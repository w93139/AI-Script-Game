<div align="center">

# 人生海海 · 孽岛疑云 Demo

**一个人，和四个 AI，围坐一桌。**

你扮演故事中的一名角色，其余角色由 AI 演绎：阅读、调查、公开讨论、单独交谈，最后做出自己的判断，揭开真相。

</div>

## 这是什么

「人生海海」是一个**本机单人 AI 剧本杀 Demo**。内置故事《孽岛疑云》：五名嫌疑人，一名死者。你选择其中一个角色，另外四个由 AI 扮演，各自掌握不同的秘密。

- **信息分层**：你能看到什么，取决于你的角色、调查进度和别人的说法。
- **说法不等于事实**：AI 会以角色语气说话，亲历、传闻和推测被区分对待。
- **规则判定真相**：阶段、线索、计分与结局由服务端规则决定，不由模型随口决定。

## 快速开始

前置：Python 3.13、Node 20+、PostgreSQL/Redis（按需），以及一个可用的模型 API Key。

1. 配置密钥（**只写在本机 `.env`，不要提交**）：

   ```sh
   cp .env.example .env     # 在 .env 中填入你的 API Key
   ```

2. 准备本机运行配置 `demo.local.json`（含私有路径，已被 `.gitignore` 忽略），格式见 `scripts/demo_launcher.py` 顶部说明。

3. 启动并打开：

   ```sh
   python scripts/demo_launcher.py start
   open http://127.0.0.1:3017/
   ```

常用命令：

```sh
python scripts/demo_launcher.py status     # 查看后端/前端与账本状态
python scripts/demo_launcher.py stop       # 停止
python scripts/demo_launcher.py restart    # 重启
python scripts/demo_launcher.py rollback   # 回退到备用运行时
```

## 玩法

1. **选角**：进入故事，了解你的身份与目标。
2. **调查**：前往不同地点查找线索（部分地点需要条件）。
3. **交流**：公开提问或单独对话，分辨亲历、传闻与推测。
4. **封卷**：提交指认、信任票与自己的推理。
5. **复盘**：揭晓真相、结果与结局。

## 主要能力

| 能力 | 说明 |
| --- | --- |
| 单人五角色 | 真人扮演一名角色，AI 承担其余角色 |
| 分阶段流程 | 阅读、调查、讨论、终局逐步推进 |
| 信息隔离 | 按角色、阶段与解锁条件呈现内容 |
| 公开 / 单独交流 | 了解立场与线索，识别不同说法 |
| 存档续玩 | 保存进度，随时继续与回看 |
| 终局复盘 | 按规则结算并揭示真相 |

## 技术栈

| 部分 | 技术 |
| --- | --- |
| 前端 | Next.js · React · TypeScript · Tailwind CSS |
| 后端 | Python · FastAPI |
| 数据 | PostgreSQL · Redis |
| AI | 模型适配、按角色过滤输入、输出校验 |

## 目录结构

- `backend/` 规则引擎、角色权限、模型适配与终局校验
- `frontend/` 游戏界面
- `scripts/` 本机启动器与工具
- `docs/` 设计与契约文档

## 范围说明

- 本项目为**本机 Demo**：单机运行、单人游玩。
- 商业剧本、私有资料与密钥不随仓库分发（见 `.gitignore`）。
- 不含公网部署、语音合成与多人联机。
- 许可证见 [LICENSE](LICENSE)。
