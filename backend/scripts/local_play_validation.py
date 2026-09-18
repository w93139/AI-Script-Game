"""Loopback-only UI integration harness using fictional data and a fake SDK.

Run: backend/.venv/bin/python backend/scripts/local_play_validation.py
This is NOT the application entry point or a publication/real-model check.
Only the existing test publisher seam and authentication are replaced. Actual
runtime/play routes, request validation, services, projections and SQLite event
persistence are exercised. No production database or commercial content is read.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.dont_write_bytecode = True
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

TOKEN = "synthetic-local-player"
MODEL = "doubao-seed-character-260628"


def deny_network(*_args, **_kwargs):
    raise AssertionError("Validation server must not make outbound network connections")


@contextmanager
def offline_guard():
    """Accept incoming HTTP while preventing every outgoing socket connection."""
    with (
        patch("dotenv.load_dotenv", return_value=False),
        patch("socket.socket.connect", deny_network),
        patch("socket.socket.connect_ex", deny_network),
        patch("socket.create_connection", deny_network),
    ):
        yield


class SyntheticSDK:
    """Deterministic responses, based solely on the actual authorized context."""
    def __init__(self):
        self.calls = 0

    async def chat_completion(self, messages, **_kwargs):
        from src.fusion.package_validation import canonical_json
        from src.services.llm_service import LLMResponse

        self.calls += 1
        context = json.loads(messages[1].content)["context"]
        schema = context.get("schema_version", "")
        if schema.startswith("package-table-context/"):
            if context["action"] == "SEAL_FINALE":
                result = {
                    "schema_version": "structured-finale-submission/1.0",
                    "answers": [{"question_id": q["id"], "option_ids":
                                 [o["id"] for o in q["options"][:q["max_choices"]]]}
                                for q in context["questions"]],
                    "vote": {"accusation_id": None, "trust_character_id": None},
                    "reflection": "合成联调：固定模拟提交，不代表模型推理质量。",
                }
            elif context["action"] == "CAST_BALLOT":
                result = {"kind": "CHOOSE", "choice_id": context["options"][0]["id"]}
            else:
                result = {"choice_id": context["options"][0]["id"]}
        elif schema.startswith("finale-motivation-context/"):
            result = {"text": "", "basis": []}
        elif schema.startswith("package-dialogue-context/"):
            result = {"segments": [{"text": "", "mode": "UNCERTAIN", "basis": []}]}
        else:
            raise AssertionError("Unsupported synthetic SDK context: " + schema)
        return LLMResponse(content=canonical_json(result),
                           usage={"prompt_tokens": 100, "completion_tokens": 10},
                           model=MODEL, finish_reason="stop")


@contextmanager
def validation_app(root: Path):
    """Construct a fresh, isolated store; refuse to overwrite any existing file."""
    from fastapi import Depends, FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
    from sqlalchemy.orm import sessionmaker

    from src.api.routes import package_play_routes, package_runtime_routes
    from src.core.auth_middleware import UnifiedAuthMiddleware
    from src.db.models import ScriptImportJob, ScriptPackageVersion, User
    from src.db.models.package_play import ScriptPackagePlay, ScriptPackagePlayEvent
    from src.db.models.package_runtime import ScriptPackagePlaySession
    from src.db.session import get_db_session
    from src.fusion.agents import PlayerModelSettings
    from src.fusion.budget import BudgetPolicy
    from src.fusion.package_guided_flow import GuidedFlowContent
    from src.fusion.package_play import PackagePlayService
    from src.fusion.package_role_model import PackageRoleModel
    from src.fusion.package_runtime import PackageRuntimeService
    from src.fusion.package_single_player import SinglePlayerContent
    from src.fusion.package_validation import content_hash
    from tests.fusion_security.test_package_full_play import full_package, REFS, SEATS
    from tests.fusion_security.test_package_guided_flow import content
    from tests.fusion_security.test_package_runtime import FixturePublisher, publish
    from tests.fusion_security.test_single_player_topics import document

    root = Path(root).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    database = root / "synthetic-play.sqlite3"
    # Exclusive creation also rejects an existing symlink.
    with database.open("xb"):
        pass
    os.chmod(database, 0o600)
    engine = create_engine("sqlite:///" + str(database), connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def explicit_transactions(connection, _record):
        connection.isolation_level = None
        connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "begin")
    def begin(connection):
        connection.exec_driver_sql("BEGIN")

    metadata = MetaData()
    for model_type in (User, ScriptPackageVersion, ScriptImportJob, ScriptPackagePlaySession,
                       ScriptPackagePlay, ScriptPackagePlayEvent):
        model_type.__table__.to_metadata(metadata)
    Table("script_package_releases", metadata, Column("id", Integer, primary_key=True))
    metadata.create_all(engine)
    factory = sessionmaker(engine, autoflush=False)
    publisher = FixturePublisher()
    package = full_package()
    package["title"] = "合成联调专用：虚构五席完整规则验证"
    for material in package["knowledge"]:
        material["retelling"] = "MAY_RETELL"
    package_hash = content_hash(package)
    guided_catalogues, single_catalogues = {}, {}
    from copy import deepcopy
    for role in SEATS:
        guide = content(package)
        guide["selected_character_id"] = role
        guided_catalogues[role] = GuidedFlowContent(package, guide)
        doc = document(package)
        doc["selected_character_id"] = role
        doc["replaces_materials"] = []
        responder_template = doc["topics"][0]["responders"][0]
        responders = []
        for peer in SEATS:
            if peer == role:
                continue
            entry = deepcopy(responder_template)
            entry["character_id"] = peer
            material = next(m for m in package["knowledge"] if m["id"] == f"initial-{peer}")
            from src.fusion.package_guided_flow import digest
            entry["basis"] = [{"collection": "knowledge", "id": material["id"],
                               "text_sha256": digest(material["text"]), "source_refs": REFS}]
            responders.append(entry)
        doc["topics"][0]["responders"] = responders
        second = deepcopy(doc["topics"][0])
        second.update(id="scene-two", phase_id="investigate-two")
        doc["topics"].append(second)
        single_catalogues[role] = SinglePlayerContent(package, doc)
    registries = {"guided_content": {package_hash: guided_catalogues},
                  "single_player_content": {package_hash: single_catalogues}}
    with factory() as db:
        for owner in (1, 2):
            db.add(User(id=owner, username=f"synthetic-{owner}", email=f"synthetic-{owner}@example.invalid",
                        hashed_password="SYNTHETIC_NOT_A_PASSWORD", is_active=True))
        db.commit()
        publish(SimpleNamespace(db=db, publisher=publisher), package)

    sdk = SyntheticSDK()
    settings = PlayerModelSettings(provider="volcengine_ark", model=MODEL, timeout_seconds=2,
                                   retries=0, max_output_tokens=256, max_input_bytes=24000,
                                   thinking_mode="disabled", temperature=0, paid_calls_enabled=True)
    role_model = PackageRoleModel(sdk, settings)
    # The production adapters require this flag. The injected SDK cannot call
    # providers and the process has an outbound socket guard. Positive rates are
    # required by the real ledger: its costs are simulated, real charges are 0.
    policy = BudgetPolicy(token_limit=1_000_000, cost_limit_cny=Decimal("10"),
                          input_rate_cny=Decimal("1"), cached_input_rate_cny=Decimal("0.1"),
                          output_rate_cny=Decimal("2"), paid_calls_enabled=True,
                          pricing_version="synthetic-ledger-no-real-charges/1")

    def session():
        with factory() as db:
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def runtime(db=Depends(session)):
        return PackageRuntimeService(db, publisher, single_player_content=registries["single_player_content"])

    def play(db=Depends(session)):
        return PackagePlayService(db, publisher, role_model, policy,
                                  speech_policy="role-speech/1.10", table_policy="package-table-model/1.1",
                                  include_interactions=True, request_scope_policy="package-request-scope/1.0",
                                  finale_policy="finale-motivation/1.1", **registries)

    class SyntheticAuth(UnifiedAuthMiddleware):
        async def get_user_from_token(self, token):
            owner = {TOKEN: 1, TOKEN + "-other-owner": 2}.get(token)
            return SimpleNamespace(id=owner, is_active=True, is_admin=False) if owner else None

    app = FastAPI(title="Synthetic local validation only")
    app.add_middleware(SyntheticAuth)
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(?:127\.0\.0\.1|localhost):[0-9]+",
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
    app.include_router(package_runtime_routes.router)
    app.include_router(package_play_routes.router)
    app.dependency_overrides[get_db_session] = session
    app.dependency_overrides[package_runtime_routes.runtime_service] = runtime
    app.dependency_overrides[package_play_routes.play_service] = play

    @app.post("/api/auth/anonymous-login")
    def anonymous_login():
        return {"access_token": TOKEN, "token_type": "bearer"}

    @app.get("/health")
    def health():
        return {"status": "ok", "data_class": "synthetic_noncommercial", "model": "fake_sdk",
                "simulated_calls": sdk.calls, "real_provider_calls": 0, "real_cost_cny": "0"}

    app.state.validation = SimpleNamespace(factory=factory, publisher=publisher, sdk=sdk, database=database)
    try:
        yield app
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8016)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    with TemporaryDirectory(prefix="ai-script-synthetic-play-") as directory, offline_guard():
        with validation_app(Path(directory)) as app:
            import uvicorn
            print(json.dumps({"url": f"http://127.0.0.1:{args.port}", "token": TOKEN,
                              "database": str(app.state.validation.database), "synthetic": True,
                              "external_network": "blocked", "real_provider_calls": 0,
                              "notice": "测试发布夹具；不证明正式发布、真实登录或模型内容质量。"}, ensure_ascii=False), flush=True)
            uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
