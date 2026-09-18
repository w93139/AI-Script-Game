"""Real HTTP and stored projections with the loopback harness's invented data."""
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from scripts.local_play_validation import TOKEN, validation_app
from tests.fusion_security.test_structured_finale import submission


@pytest.mark.parametrize("role", ["a", "b", "c", "d", "e"])
def test_local_harness_five_roles_complete_via_real_http_and_restore(tmp_path, role):
    with validation_app(tmp_path / role) as app, TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + TOKEN

        def post(url, body, code=200):
            response = client.post(url, json=body)
            assert response.status_code == code, response.text
            return response.json()["data"]

        releases = client.get("/api/fusion/package-releases").json()["data"]
        assert len(releases) == 1 and len(releases[0]["characters"]) == 5
        opening = post("/api/fusion/package-sessions", {"release_id": releases[0]["id"],
                       "character_id": role, "idempotency_key": "opening"}, 201)
        view = post("/api/fusion/package-plays", {"opening_session_id": opening["session_id"],
                    "idempotency_key": "start"}, 201)
        base = "/api/fusion/package-plays/" + view["play_id"]
        assert view["selected_character_id"] == role
        assert "PRIVATE_BOOK_" + role in str(view)
        assert all("PRIVATE_BOOK_" + peer not in str(view) for peer in "abcde" if peer != role)
        assert "SYSTEM_TRUTH" not in str(view)
        forbidden = client.get(base, headers={"Authorization": "Bearer " + TOKEN + "-other-owner"})
        assert forbidden.status_code == 404
        invalid = client.post(base + "/actions", json={"idempotency_key": "invalid", "expected_revision": 0,
                              "action": "ADVANCE_PHASE", "target": None})
        assert invalid.status_code == 422
        assert client.get(base).json()["data"]["revision"] == 0

        def command(endpoint, action, payload=None):
            nonlocal view
            body = {"expected_revision": view["revision"], "idempotency_key": f"step-{view['revision']}", "action": action}
            if endpoint == "guided":
                body["schema_version"] = "package-guided-command/1.0"
            elif endpoint == "table":
                body["schema_version"] = "package-full-play-command/1.0"
            if payload is not None:
                body["payload"] = payload
            view = post(base + "/" + endpoint, body)
            assert client.get(base).json()["data"] == view

        command("actions", "ADVANCE_PHASE")
        assert view["full_game"]["phase_kind"] == "INVESTIGATION"
        command("guided", "INVESTIGATE", {"action_id": "find-key"})
        assert any(item["id"] == "evidence-find-key" for item in view["public_evidence"])
        command("guided", "INVESTIGATE", {"action_id": "open-box"})
        topic = view["single_player"]["topics"][0]
        peer = topic["responders"][0]["character_id"]
        view = post(base + "/topic", {"schema_version": "package-topic-command/1.0",
                    "expected_revision": view["revision"], "idempotency_key": "ask-topic", "action": "ASK_TOPIC",
                    "payload": {"topic_id": topic["id"], "character_id": peer, "intent_id": "initial", "channel": "PUBLIC"}})
        view = post(base + "/responses", view["single_player"]["turns"][-1]["reply_request"])
        assert view["last_ai_status"] == "OK"
        public_before = view["discussion"]
        command("table", "START_CALL", {"peer_character_id": peer})
        view = post(base + "/topic", {"schema_version": "package-topic-command/1.0",
                    "expected_revision": view["revision"], "idempotency_key": "private-topic", "action": "ASK_TOPIC",
                    "payload": {"topic_id": topic["id"], "character_id": peer, "intent_id": "clarify", "channel": "PRIVATE"}})
        view = post(base + "/private-responses", view["single_player"]["turns"][-1]["reply_request"])
        assert view["last_ai_status"] == "OK" and view["discussion"] == public_before
        assert view["full_game"]["private_discussion"]
        command("table", "STOP_CALL")
        command("guided", "FINISH_INVESTIGATION")
        command("actions", "ADVANCE_PHASE")
        command("guided", "INVESTIGATE", {"action_id": "look-note"})
        command("guided", "FINISH_INVESTIGATION")
        assert view["full_game"]["phase_kind"] == "FINALE"
        command("table", "SEAL_FINALE", submission(role))
        for peer in "abcde":
            if peer == role:
                continue
            view = post(base + "/decisions", {"schema_version": "package-table-decision-command/1.0",
                        "expected_revision": view["revision"], "idempotency_key": "seal-" + peer,
                        "character_id": peer, "action": "SEAL_FINALE"})
            assert view["last_ai_status"] == "OK"
        assert view["full_game"]["finale"]["all_sealed"]
        command("actions", "SETTLE")
        assert view["settled"] and view["status"] == "SETTLED"
        assert Decimal(view["budget"]["used_cost_cny"]) > 0  # simulated ledger only
        library = client.get("/api/fusion/package-play-library").json()["data"]
        assert view["play_id"] in str(library)
        health = client.get("/health").json()
        assert health["simulated_calls"] == 10
        assert health["real_provider_calls"] == 0 and health["real_cost_cny"] == "0"
        # Independent HTTP client and SQL session read the committed event ledger.
        with TestClient(app) as fresh:
            assert fresh.get(base, headers={"Authorization": "Bearer " + TOKEN}).json()["data"] == view


def test_local_harness_refuses_existing_database_and_requires_test_token(tmp_path):
    with validation_app(tmp_path) as app, TestClient(app) as client:
        assert client.get("/api/fusion/package-releases").status_code == 401
        assert client.post("/api/auth/anonymous-login").json()["access_token"] == TOKEN
    with pytest.raises(FileExistsError), validation_app(tmp_path):
        pass


def test_security_runner_keeps_required_paths_and_only_skips_removed_optional_suite(tmp_path):
    from scripts.test_fusion_security import suite_paths
    required = [str(tmp_path / "tests" / name) for name in
                ("fusion_security", "test_fusion_service.py", "test_fusion_rules.py")]
    assert suite_paths(tmp_path) == required  # missing required paths remain failures
    optional = tmp_path / "tests" / "media_safety"
    optional.mkdir(parents=True)
    assert suite_paths(tmp_path) == required + [str(optional)]
