# adv_full：建议链路完整时间线运行（2026-11-10）

> 探索性运行：未在运行前写预期行为，不作为场景卡判定依据。单次运行，单一模型。

## 运行条件

- 被测版本：map-system `0640239`。
- 配置：`mvn spring-boot:run` 按 `pom.xml` 启用 `local` 配置档。`application-local.properties` 不入库，由同目录的 `.example` 复制并填入智谱密钥，其中 `llm.advisory.enabled=true`；基础配置中 advisory 默认关闭，不启用该档则不会产生建议。其余取 `application.properties`：`llm.enabled=true`、`llm.advisory.max-iterations=10`、日志级别 DEBUG。
- 模型：zhipu `glm-4.5-air`。
- 依赖：`map-mqtt`、`my_postgis` 均运行；本地库无海图表，水文查询立即报错返回（与 [B1](../B1-场景04-依赖不可达.md) 的对照条件相同）。
- 输入：武汉演示模拟器完整时间线，无注入、无参数。
- 时间：2026-11-10 20:49–21:05（UTC+8）。

```bash
cd backend/map-service && mvn -q spring-boot:run > backend.log 2>&1
python3 -I sse_capture.py sse.log          # B2 附录 B
simulator/venv/bin/python -u simulator/wuhan_yangtze_ais_simulator.py > sim.log 2>&1
```

## 文件

| 文件 | 内容 |
|---|---|
| `adv_full_sse.log` | SSE 全量（接收时间、事件类型、JSON）。RISK_UPDATE 2752 帧，ADVISORY 4，ERROR 4 |
| `adv_full_sim.log` | 模拟器输出，AIS 报文 2751 条 |
| `adv_full_backend.log` | 后端日志节选，169 行（原始 46915 行）。保留启动段、建议触发与发布、Agent 工具调用（DEBUG，仅工具名）、解释生成；删去其余 DEBUG、每帧的 `Dispatcher Time` 与水文查询失败 WARN（2800 条）。本地路径已替换 |
| `advisory_stats.py` | 统计脚本，仅依赖标准库 |

复算：`python3 -I advisory_stats.py adv_full_sse.log adv_full_backend.log v`

## 结果

时间以首帧接收时间为 +0 s。含目标的帧 2750，时长 920 s，最大帧滞后 1.0 s。本船 COG 在 +578 s 前恒为 29.6°。

目标等级：

- `900001222`（对遇）：SAFE → +229 s CAUTION → +281 s WARNING → +317 s ALARM → +323 s WARNING → +332 s SAFE。
- `900002222`：SAFE → +88 s CAUTION → +151 s WARNING → +373 s ALARM → +489 s WARNING → +634 s SAFE。三处阈值各在 1–2 s 内往返 2 次后才稳定。

建议生成（8 次触发）：

| 触发 | 结果 | 耗时 | 工具调用 | 等级 | 动作 | 显示至 |
|---|---|---|---|---|---|---|
| +55 s | 发布 | 7.9 s | 6 | SAFE | MONITOR / LOW | +124 s（被顶替） |
| +117 s | 发布 | 6.3 s | 5 | CAUTION | COURSE_CHANGE / MEDIUM | +160 s（被顶替） |
| +151 s | 发布 | 9.4 s | 8 | WARNING | COURSE_CHANGE / HIGH，右转 30° | +280 s（到期） |
| +229 s | 超出迭代上限 | 6.8 s | 10 | — | — | — |
| +266 s | 超出迭代上限 | 6.8 s | 10 | — | — | — |
| +281 s | 超出迭代上限 | 6.7 s | 10 | — | — | — |
| +317 s | 超出迭代上限 | 6.4 s | 10 | — | — | — |
| +373 s | 发布 | 9.8 s | 8 | ALARM | COURSE_CHANGE / IMMEDIATE，右转 30° | +502 s（到期） |

## 观察

1. **两个目标同时非 SAFE 时生成全部失败。** +229 s 至 +317 s 的 4 次触发各调用 10 个工具后达到迭代上限（`llm.advisory.max-iterations=10`，每次迭代执行一个工具调用），没有产生最终回答。`900001222` 从 CAUTION 到 ALARM 再回到 SAFE 的全过程（+229 s 至 +332 s）没有任何一条建议覆盖。前端收到的错误事件为 `ADVISORY_SCHEMA_FAILED`，文本为“schema validation error”，与实际原因不符。
2. **有目标处于 WARNING 及以上而没有未过期建议的时段共两段**：+280 s 至 +382 s（102.4 s，含 `900001222` 的 ALARM）；+502 s 至 +634 s（131.4 s，`900002222` 为 ALARM 或 WARNING）。合计 233.8 s，占 WARNING 及以上时长 481.1 s 的 48.6%；按全部非 SAFE 计为 545.4 s 中的 42.9%。第二段的成因是建议固定有效 120 s，而同一会遇在已覆盖等级之内不再触发。
   - 该统计是探索性的，不是覆盖指标：只看是否存在未过期、未被顶替的建议，不检查建议是否针对当前风险最高的目标。+229 s 至 +280 s 期间显示的建议只针对 `900002222`，此时 `900001222` 已为 CAUTION。
3. **建议文本中的本船航向有误。** +55 s 的建议依据写“航向 296°”，+373 s 的建议动作写“将航向从 296 度改为 326 度”；同期 SSE 帧中本船 COG 为 29.6°。+117 s、+151 s 的两条写作 29.6°。工具入参与返回值未记入日志，错误出自工具输出还是模型转述未能确认；机动评估实际使用的转角、目标与返回的 CPA 是否对应发布的动作，同样未核对。
4. **发布后场景变化的情况**：+55 s 的建议称 `900002222`“已通过最近点”，25 s 后该目标升为 CAUTION，该建议继续显示 36 s；其余三条在显示期间受影响目标的等级未下降。未出现目标驶过后建议仍在显示的情况。

## 限制

- 单次运行；工具调用次数与失败与否随模型输出变化，未做重复运行。
- 模拟器按脚本运行，本船不执行建议，无法观察建议被采纳后的情况。
- 工具入参与返回值不在日志中，观察 1 的“10 次调用”只有工具名序列。
