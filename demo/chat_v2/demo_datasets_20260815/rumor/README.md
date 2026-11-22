# RumorAnalyze 模拟数据

**本目录全部为模拟数据**，由 `demo/chat_v2/rumor/data_prep/generate_synthetic.py --out demo_datasets_20260815/rumor --seed 2026` 生成，帖子内容和用户均为虚构，不对应任何真实事件。脚本固定了随机种子，每次运行结果相同。

| 事件 | 场景 | 源帖数 | 转发数 |
|---|---|---:|---:|
| `salt_shortage` | 食盐断货谣言 | 7 | 4,993 |
| `exam_leak` | 高考泄题谣言 | 6 | 3,057 |
| `earthquake_forecast` | 地震预测谣言 | 6 | 3,826 |

## 字段

- `posts.csv`：post_id, user_id, created_at, text, followers, label（rumor / debunk / normal）
- `reposts.csv`：post_id, parent_post_id, user_id, created_at。parent_post_id 可以是源帖，也可以是另一条转发，因此转发关系会形成多层的树。

user_id 已做哈希脱敏，时间为当地时间，格式为 `YYYY-MM-DD HH:MM:SS`。

## 模拟规则（便于核对分析结论）

- 辟谣帖由粉丝数大的官方账号发布，发布时间比谣言晚 4～18 小时（每个事件不同）。
- 转发时更倾向于转发粉丝数多的节点，约 1% 的转发者是大 V（粉丝数 5 万～40 万）。
- 谣言帖的转发量大于辟谣帖，普通帖的转发量很少。
