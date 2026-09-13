<div align="center">

# 🎭 人生海海

**单真人 AI 剧本杀** —— 你扮演一个角色，其余角色由 AI 演绎。

*AI Script Game · 一人一局，其余交给大模型*

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?logo=fastapi&logoColor=white)]()
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)]()
[![Redis](https://img.shields.io/badge/Redis-7.4-DC382D?logo=redis&logoColor=white)]()

</div>

## 这是什么

「人生海海」是一款面向浏览器的**单真人 AI 剧本杀**：你选择一名角色（可以是凶手），其余 3–7 名角色由大模型演绎。搜证、盘问、讨论、投票，在深夜的案卷里走完一整局。

**核心原则：规则引擎是唯一权威。** 阶段推进、搜证、证据可见性与投票都由确定性服务端代码决定；云模型只生成「角色发言」候选，不能直接修改游戏状态、读取私本或越权访问其他角色的材料。

## 特性

- 🎭 **单真人 + AI 配角** —— 真人选角入局，AI 各有人设、秘密与转述义务
- 🗂️ **三幕流程** —— 阅读 → 调查 → 终局，每幕有清晰目标与可做之事
- 🔍 **条件线索** —— 证据按阶段、前置条件与角色权限逐层解锁
- 🔐 **权限隔离** —— 私本、凶手秘密、证据、系统真相按角色严格过滤
- 💾 **断线续玩** —— 阶段、行动、对话、模型用量全部持久化，可续玩与回看
- ⚖️ **投票结算** —— 终局投票、封卷、真相揭晓与复盘评分

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI · PostgreSQL · Redis |
| 前端 | Next.js 16 · React 19 · Tailwind CSS 4（午夜深色主题） |
| 模型 | 火山方舟 doubao-seed-character（默认） · 阿里百炼 qwen（备用） |
| 鉴权 | JWT + 手机验证码（开发期支持免登录） |

> ⚠️ 角色对白链路只接受**经过白名单与离线契约测试**的火山方舟 / 阿里百炼，不能把「OpenAI 兼容」理解为可任意更换供应商。

## 快速开始

完整步骤见 [从零搭建本机环境](docs/development/LOCAL_SETUP_FROM_SCRATCH.md)（无需 Docker）。

```bash
# 1. 启动本机依赖（PostgreSQL / Redis）
backend/.venv/bin/python scripts/local_postgres.py start
backend/.venv/bin/python scripts/local_redis.py start

# 2. 启动后端（127.0.0.1:8010）
cd backend && ./.venv/bin/python -B main.py

# 3. 启动前端（127.0.0.1:3001）
cd frontend && npm run dev
```

浏览器打开 <http://127.0.0.1:3001>。

> 仓库不含任何可玩的剧本正文（商业剧本受版权保护，不得入库）。
> 开发者可用 `backend/scripts/seed_demo_package.py --allow-paid` 导入一份**虚构示例剧本**（需配置模型 API Key，会产生少量云模型费用）。

## 当前状态

| 能力 | 状态 |
| --- | --- |
| 本机开发运行 | ✅ 可用 |
| 单真人 + AI 文字整局 | ⚠️ 可玩，内容尚未导入发布 |
| 登录（手机验证码） | ⚠️ 代码就绪，未接真实短信供应商 |
| 开发期免登录 | ✅ `ALLOW_ANONYMOUS_ACCESS=true` |
| 语音输入 / TTS | ⏸ 未接通 |
| 正式上线 | ❌ `runtime_ready=false` |

## 项目结构

```
├── backend/     # FastAPI 后端（规则引擎、Fusion 玩法、DB、API）
│   ├── src/     # 核心源码
│   ├── scripts/ # 工具脚本（导入、联调、同步、种子数据）
│   └── tests/   # 测试
├── frontend/    # Next.js 前端（游戏房间、首页、管理后台）
├── docs/        # 契约与开发记录
├── deploy/      # 部署配置
└── scripts/     # 本机服务与预检
```

## 文档

| 想知道什么 | 看这里 |
| --- | --- |
| 环境搭建 | [从零搭建本机环境](docs/development/LOCAL_SETUP_FROM_SCRATCH.md) |
| 启动使用 | [小白本地启动说明](docs/development/LOCAL_DEVELOPMENT.md) |
| 贡献指南 | [CONTRIBUTING](CONTRIBUTING.md) |
| 迭代计划 | [迭代方案](迭代方案.md) |
| 变更记录 | [CHANGELOG](CHANGELOG.md) |
| 部署 | [ECS 部署](deploy/ECS.md) |

## 安全约定

生产环境启动自检强制以下约束，不合格会**拒绝启动**而不是带病运行：

- `SECRET_KEY` 必须显式设置且足够长
- 不接受模拟短信、匿名访问、弱数据库口令和对象存储出厂凭据
- 访问令牌 2 小时、可挂失；登录与验证码均有频次限制
- 接口说明书与遗留管理接口在生产环境默认不注册

## 许可证

[MIT](LICENSE)
