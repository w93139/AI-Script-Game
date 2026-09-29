# AGENTS.md — 开发与运行说明

本文件供在本仓库工作的编码助手使用。**早期开发记录与验证历史已移出本仓库，可从 git 历史找回**，此后只保留必要的现状说明。

## 项目

「人生海海」是一个**本机单人 AI 剧本杀 Demo**：一名真人扮演故事中的一个角色，其余角色由 AI 扮演。规则、线索、计分与结局由服务端规则决定；模型只负责角色表达。前端 Next.js，后端 FastAPI。

## 目录

- `backend/` 规则引擎、角色权限、模型适配、终局校验
- `frontend/` 游戏界面
- `scripts/demo_launcher.py` 本机启动器（`start/stop/restart/status/rollback`）
- `docs/contracts/` 接口与数据契约

## 本机运行

```sh
python scripts/demo_launcher.py start      # 需要 demo.local.json（本机私有，已 gitignore）
python scripts/demo_launcher.py status
python scripts/demo_launcher.py stop
```

`demo.local.json` 指向本机私有的运行时、状态目录、前端构建与端口，**不要提交**。

## 硬约束

1. **密钥**：只保存在 `.env`（已 gitignore）；不打印、不提交、不写入任何被跟踪文件；不要把 Key 贴进 Issue 或提交信息。
2. **私有资料**：剧本正文、私有资料、真实存档与模型原始输出均在仓库外；不复制进仓库。
3. **冻结与旧局**：已冻结/已发布版本、历史事件与历史账本不改写；新策略必须使用新版本。
4. **费用**：真实模型调用受次数与费用上限约束，写入共享账本；失败、取消、重复均不自动重发；每次调用前先读账本。
5. **结构 ≠ 语义**：结构校验通过不代表内容正确；实现方不得自行宣布语义验收通过。

## 测试（离线优先）

```sh
backend/.venv/bin/python scripts/dev_preflight.py                                  # 0/2 允许，1 阻塞
backend/.venv/bin/python -m unittest discover -s scripts -p 'test_dev_preflight.py'
backend/.venv/bin/python backend/scripts/test_fusion_security.py
cd frontend && npm run check && npm test
git diff --check
```

不要裸跑旧全量 pytest（可能初始化真实应用）。
