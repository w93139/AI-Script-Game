# 终局 1.8 集合归一候选（2026-09-29）

## 范围

`finale-motivation/1.8` 仅在终局输出校验时修正 basis 的 `collection`：原 `(collection,id)` 不在本次授权的 `materials ∪ discussion` 中，且同一 `id` 在该集合中恰好对应一个其他 collection，才改为该 collection。已知 pair、歧义 id、无匹配 id 原样处理；改写后继续执行重复引用、空文本、90 字单句、被引讨论说话人、地点与谨慎措辞校验。模型、提示正文、输出结构与公开材料范围不变。1.0–1.7 的提示、输出 schema、上下文 schema 哈希保持。

## 四条真实回执的离线回放

只读使用上一批 1.7 的 H/Y/J/S 四条 dispatch/response；历史回执和费用未改，本轮真实调用 **0**。原文和完整引用留在仓库外私有回放报告；私有 `replay.json` 记录逐条校验结果，`replay-attribution.json` 另记录包括 Y 在内的归一后引用与说话人核对。

| AI 席 | 1.7 原判定 | 1.8 离线判定 | 集合与归属 |
| --- | --- | --- | --- |
| H | ACCEPTED | ACCEPTED | 原引用不变；点名与被引说话人一致 |
| J | ACCEPTED | ACCEPTED | 67 字仍接纳；原引用不变，归属一致 |
| S | INVALID | ACCEPTED | `evidence:statement-2` 唯一归一为 discussion；被引说话人 J 与点名一致 |
| Y | INVALID | `FINALE_MOTIVATION_LOCATION_UNSUPPORTED` | `evidence:statement-5` 唯一归一为 discussion，点名 J 与说话人一致；文本另有地点词不在归一后的两条 basis 依据中 |

因此“Y/S 均恢复”的预期**未达到**。Y 的第二道来源校验不是集合归一能解决的问题；本候选不放宽地点依据，也不将结构校验外推为语义正确。终局语义仍待独立来源复核。

## 切换准备与状态

私有 `runtime_finale18.py` 已准备，现网 8017 仍使用 1.7。状态副本临时端口 18049 的 `/health` 正常、百炼 provider/model 与现网一致；新局绑定 1.8，41 个既有局视图逐项一致，SQLite quick_check 正常。临时实例已停止，状态副本保留；私有交接文件保存启动、停止与回退命令。当前账本 **200/200 次、¥3.92154644**，剩余 0 次，本轮没有真实请求。由于 Y 回放未通过，不启用 1.8，也不宣布 MVP 验收通过。
