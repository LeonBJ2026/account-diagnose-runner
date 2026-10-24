# account-diagnose-runner · 账号诊断器

**Link in, HTML scorecard out — for Xiaohongshu (RED) and Douyin accounts.**

A self-contained skill (rubric + scorer + samples) that turns a profile URL into a printable, evidence-backed account diagnostic instead of a list of vague tips.

**喂它一条主页链接，还你一份可打印的 HTML 诊断评分卡。** 中文说明见下方 [中文文档](#中文).

---

## Why this exists

Most "why is my account stuck?" answers are vibes. This skill forces three things:

| | What it does |
|---|---|
| **Fixed rubric** | 24 items across 6 modules, 100 points per platform. Same table every time, so audits are comparable *within* a platform. |
| **One bottleneck** | The report names exactly one primary bottleneck. Everything else is recorded but deliberately not actioned — changing five things at once makes attribution impossible. |
| **Falsifiable criteria** | Every fix ships with a metric, a review date, and the condition under which the fix should be judged a **failure**. No "post more and see". |

When data is missing, the report says *not measured* and **refuses to grade**. It never fills gaps with estimates.

---

## Install

```bash
git clone https://github.com/LeonBJ2026/account-diagnose-runner.git
```

Drop the folder into your agent's skill directory:

- Trae / Claude Code (project scope): `.trae/skills/account-diagnose-runner/`
- Global scope: `~/.trae-cn/skills/account-diagnose-runner/`

Requirements: Python 3.8+ (standard library only — no `pip install`), and a browser tool for capture.

---

## Quick start

```bash
cd account-diagnose-runner
python scripts/score_account.py examples/sample-profile.json --out examples/sample-score.json
```

Expected output:

```
总分 84.0 / 99（缺测 1 分）→ 折合 84.8，等级：A
主要矛盾：M6（得分率 33%）
```

Then ask your agent: `诊断这个账号 <profile-url>`.

The agent will: parse the link → capture the public profile → write `profile.json` → run the scorer → assemble the 9-section HTML report.

---

## Input tiers

| You provide | Reachable score | Grade allowed |
|---|---|---|
| URL only | ≈46 / 100 on both platforms (public grids hide play counts) | No |
| URL + creator analytics | Xiaohongshu ≈68; **Douyin ≈56** (5 Douyin content items require watching the video) | No if ≥30 pts missing |
| URL + analytics + post copy / watch notes | 100 / 100 | Yes |

---

## The report

Nine fixed sections, single self-contained HTML file (inline SVG, no CDN, opens offline, A4 landscape, printable):

1. Header — platform, account, capture date, data cut-off, credibility level
2. One-line verdict — a single bottleneck, plus one piece of counter-evidence
3. Score table + six module explainer cards (what it measures / why it weighs that much / most common mistake)
4. Radar — six axes; modules measured below 70% coverage are drawn dashed and excluded from comparisons
5. Funnel — where attention actually dies
6. Issue list — each item: evidence → root cause → fix → **falsification criterion**
7. What not to do — with a reason for each
8. Where this report may be wrong — pre-written re-judgement conditions
9. Credibility statement — what is sourced, what is inferred, what is unmeasured

Open [`examples/sample-report-xhs.html`](examples/sample-report-xhs.html) or [`examples/sample-report-douyin.html`](examples/sample-report-douyin.html) in a browser.

---

## Scoring

Six modules, 24 items, 100 points.

| Module | Xiaohongshu | Douyin |
|---|---|---|
| M1 Account | 16 | 14 |
| M2 Content | 30 | 32 |
| M3 Structure | 14 | 14 |
| M4 Data | 22 | 28 |
| M5 Conversion | 12 | 8 |
| M6 Differentiation | 6 | 4 |

Grades: 90 S / 80 A / 70 B / 60 C / <60 D. **≥30 points unmeasured → no grade.**

Two protections are built into the scorer and are not meant to be overridden:

- **Coverage gate (70%)** — a module measured below 70% of its full marks cannot compete for "lowest"; you cannot tell a true weakness from an unmeasured one.
- **No-bottleneck rule** — if every qualifying module scores ≥70%, the output is `no significant primary bottleneck` plus the unmeasured point count. Calling a 91% module "the main problem" is nonsense.

**Scores are not cross-platform comparable.** Different tables, different weights.

---

## Hard boundaries

- Capture failure is a valid result — `BLOCKED` is a legitimate output, never substituted with a "similar account I saw before"
- Read-only: no likes, follows, comments, or edits; no login walls bypassed
- Only script-computed scores count; any hand-adjusted value must be labelled in the report
- No certainty and no growth promises — evidence, direction, and probability framing only
- Never infer shadow-banning from an empty analytics panel; that is a data gap, not a punishment

---

## Known limits

- Ceiling on public profiles: roughly **46 / 100** on both platforms (measured on one account each, 2026-10-24 — empirical, not a platform rule)
- Douyin public profiles expose likes only, no play counts; titles require opening each post. Creator-center analytics are the only source of plays / completion / retention.
- The Douyin creator center renders about 5 posts at a time and warns that sorting covers only the last 90 days — expect small samples.
- Validated on **2 real accounts** (same owner, both platforms, 2026-10-24). Everything else is constructed fixtures. Review the first report of any batch by hand.

---

## Layout

```
SKILL.md                    agent entry point (workflow + boundaries)
references/xhs-scoring.md   24-item rubric, Xiaohongshu
references/douyin-scoring.md 24-item rubric, Douyin
references/report-spec.md   9-section report spec + failure-mode library
scripts/score_account.py    scorer (stdlib only)
scripts/profile.schema.json capture contract
examples/                   fictional sample profile + score + two rendered reports
```

---

## License

MIT. See [LICENSE](LICENSE).

---

<a id="中文"></a>
# 中文文档

**给它一条主页链接，它还你一份 HTML 诊断评分卡。**

一个自包含账号诊断技能（口径 + 算分器 + 样例），支持小红书与抖音。不靠感觉，靠固定评分表和可证伪的改法。

## 它解决什么问题

大多数"账号为什么起不来"的答案都是感觉。这个技能强制三件事：

| | 做了什么 |
|---|---|
| **固定评分表** | 6 模块 24 项 100 分，每次都用同一张表，同一平台内的两次诊断可以横比。 |
| **只给一个主要矛盾** | 报告只点名一个瓶颈。其余模块记录在案但**故意不给改法**——一次改五处，14 天后无法归因。 |
| **可证伪的判据** | 每条改法都带指标、复看日期，以及"什么情况算失败"。不是"多发几条看看"。 |

**数据缺了就写"缺测"并拒绝判级，绝不估算。**

## 安装

```bash
git clone https://github.com/LeonBJ2026/account-diagnose-runner.git
```

把目录放进你的智能体技能目录：

- Trae / Claude Code（项目级）：`.trae/skills/account-diagnose-runner/`
- 全局：`~/.trae-cn/skills/account-diagnose-runner/`

依赖：Python 3.8+（只用标准库，不用装任何包），抓取需要一个浏览器工具。

## 快速开始

```bash
cd account-diagnose-runner
python scripts/score_account.py examples/sample-profile.json --out examples/sample-score.json
```

预期输出：

```
总分 84.0 / 99（缺测 1 分）→ 折合 84.8，等级：A
主要矛盾：M6（得分率 33%）
```

然后对智能体说：`诊断这个账号 <主页链接>`。

它会：解析链接 → 抓公开主页 → 落成 `profile.json` → 跑算分器 → 组装 9 区块 HTML 报告。

## 三档输入

| 你给的东西 | 能跑到 | 能否判级 |
|---|---|---|
| 只给链接 | 两个平台都约 46 / 100（公开主页不显示播放量） | 否 |
| 链接 + 后台数据 | 小红书约 68；**抖音约 56**（抖音有 5 项内容判断必须看片） | 缺测 ≥30 分则不判 |
| 链接 + 后台 + 正文/看片记录 | 100 / 100 | 可以判 |

## 报告长什么样

九个固定区块，单文件 HTML（内联 SVG、零 CDN、离线可开、A4 横版可打印）：

1. 报告头 —— 平台、账号、抓取日、数据截止日、可信度等级
2. 一句话结论 —— 只给一个主要矛盾，附一条反例证据
3. 评分总表 + 六模块释义卡（测什么 / 为什么占这个分值 / 最容易犯的错）
4. 六维雷达 —— 覆盖不足 70% 的模块画虚线，且不参与"最低"比较
5. 漏斗现状 —— 注意力到底死在哪一环
6. 问题清单 —— 每条四段：证据 → 病因 → 改法 → **失败判据**
7. 不建议做什么 —— 每条都带理由
8. 本报告可能错在哪 —— 事先写死的改判条件
9. 可信度声明 —— 哪些有来源、哪些是推断、哪些没测

浏览器打开 [`examples/sample-report-xhs.html`](examples/sample-report-xhs.html) 或 [`examples/sample-report-douyin.html`](examples/sample-report-douyin.html) 看效果。

## 评分表

| 模块 | 小红书 | 抖音 |
|---|---|---|
| M1 账号层 | 16 | 14 |
| M2 内容层 | 30 | 32 |
| M3 结构层 | 14 | 14 |
| M4 数据层 | 22 | 28 |
| M5 转化层 | 12 | 8 |
| M6 差异化 | 6 | 4 |

等级：90 S / 80 A / 70 B / 60 C / <60 D。**缺测 ≥30 分不判级。**

算分器内置两道保护，不建议手工推翻：

- **覆盖率门槛（70%）**：实测覆盖不足满分的 70% 的模块，不参与"最低"比较——分不清是真低还是缺测。
- **无短板不点名**：所有合格模块都 ≥70% 时，输出"未见显著主要矛盾"，并提示还缺多少分。把 91% 的模块叫"主要矛盾"是荒谬的。

**两个平台的分数不可互比**：不同的表、不同的权重。小红书 38 分和抖音 45 分说明不了任何关系。

## 硬边界

- 抓取失败就报失败，`BLOCKED` 是合法结果，不许拿"以前见过的类似账号"顶替
- 只读：不点赞、不关注、不评论、不编辑，不绕登录墙
- 报告里的每个数字必须能在 `score.json` 找到出处，手改过的必须标注
- 不给确定性结论、不承诺涨粉；只给依据、方向和概率表述
- 不根据空白的后台数据推断"被限流"——那是数据缺口，不是平台处罚

## 已知限制

- 公开主页可测上限约 **46 / 100**（2026-10-24 各实测 1 例，属经验值，不是平台规则）
- 抖音公开主页只给点赞、不给播放量，标题要点进每条才看得到；播放/完播/留存只有创作者中心后台有
- 抖音创作者中心内容管理页一次只渲染约 5 条，并提示排序仅支持近 90 天，样本会偏小
- 已用 **2 个真实账号**验证（同一主体的两个平台，2026-10-24），其余为构造用例；批量使用时第一份报告请人工复核

## 许可

MIT，见 [LICENSE](LICENSE)。
