"""游戏历史回放接口的权限边界测试。

历史回放会暴露会话内的事件与角色信息，必须与列表接口同等的权限边界：
只允许房主和真正加入该局的人类玩家访问，其余一律拒绝。
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.services.game_history_service import GameHistoryService, GameResumeService


def _service_with_session(host_user_id: int, participant_user_ids: list[int] | None) -> GameHistoryService:
    session = SimpleNamespace(session_id="sess-1", host_user_id=host_user_id)
    db = MagicMock()
    if participant_user_ids:
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace()
    else:
        db.query.return_value.filter.return_value.first.return_value = None
    svc = GameHistoryService(db, MagicMock(), MagicMock())
    return svc, session


class TestRequireSessionAccess:
    def test_host_is_allowed(self):
        svc, session = _service_with_session(host_user_id=1, participant_user_ids=None)
        # 房主应直接放行，不抛异常
        svc._require_session_access(session, 1)

    def test_participant_is_allowed(self):
        svc, session = _service_with_session(host_user_id=1, participant_user_ids=[2])
        # 非房主但为参与者应放行
        svc._require_session_access(session, 2)

    def test_stranger_is_rejected(self):
        svc, session = _service_with_session(host_user_id=1, participant_user_ids=None)
        with pytest.raises(PermissionError):
            svc._require_session_access(session, 999)


class TestResumeGameAccess:
    def test_stranger_cannot_resume(self):
        session = SimpleNamespace(session_id="sess-1", host_user_id=1, script_id=7, status=SimpleNamespace(value="PAUSED"))
        db = MagicMock()
        repo = MagicMock()
        repo.get_by_session_id.return_value = session
        # 参与者查询返回 None -> 拒绝
        db.query.return_value.filter.return_value.first.return_value = None
        svc = GameResumeService(db, repo)
        import asyncio
        with pytest.raises(PermissionError):
            asyncio.run(svc.resume_game("sess-1", 999))

    def test_host_can_resume(self):
        session = SimpleNamespace(session_id="sess-1", host_user_id=1, script_id=7, status=SimpleNamespace(value="PAUSED"))
        db = MagicMock()
        repo = MagicMock()
        repo.get_by_session_id.return_value = session
        svc = GameResumeService(db, repo)
        import asyncio
        resp = asyncio.run(svc.resume_game("sess-1", 1))
        # 房主放行，且 websocket 端口不再硬编码 8000
        assert "localhost:8000" not in resp.websocket_url
        assert "8010" in resp.websocket_url


if __name__ == "__main__":
    pytest.main([__file__])
