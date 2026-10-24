---
name: account-diagnose-runner
description: Link-in, report-out account diagnostic for Xiaohongshu (RED) and Douyin. Paste a profile URL, capture the public profile (plus creator-center analytics when available), score 24 items across 6 modules, and emit a zero-dependency HTML scorecard that names one primary bottleneck with falsifiable judgement criteria. Use when the user asks to 诊断账号 / 账号打分 / 为什么没流量 / 主页怎么改 / 对标账号分析, or says "audit this Xiaohongshu or Douyin account", "score this profile", "why is my account stuck".
---

# account-diagnose-runner

**Give it a profile link. It gives you an HTML scorecard.**

No manual number-copying, no hand-scoring. Capture → structure → score → report, in four steps.

Self-contained: the scoring rubric (`references/`), the scorer (`scripts/`), and two worked samples (`examples/`) ship in this repo. Nothing else to install.

---

## What problem it solves

Most "why is my account stuck" answers are vibes. This one forces three things:

1. **A fixed rubric** — 24 items, 6 modules, 100 points per platform. Same table for every account, so two audits are comparable **within** a platform.
2. **A single bottleneck** — the report names exactly one main contradiction, not a checklist of twenty suggestions. Everything else is recorded but not actioned.
3. **Falsifiable criteria** — every fix carries a metric, a date, and the condition under which the fix should be judged a failure.

If the data isn't there, the report says "not measured" and refuses to grade. It never estimates.

---

## Input contract (three tiers)

| You provide | Reachable score | Report must state |
|---|---|---|
| URL only | Xiaohongshu ≈46 / 100; Douyin ≈46 / 100 (public grid has no play counts) | "N points unmeasured, no grade" |
| URL + analytics | Xiaohongshu ≈68 / 100; **Douyin ≈56 / 100** (5 of Douyin's content items require watching the video) | "N points unmeasured, no grade" |
| URL + analytics + post copy / watch notes | 100 / 100 | Grade allowed |

**Never ask for the user's password.** Never use a logged-in session to read anything not visible on the public profile — except the account owner's own creator center, when the user hands you that link themselves.

---

## Four steps

### 1. Parse the link, fix the platform

```
Xiaohongshu: xiaohongshu.com/user/profile/<user_id>   → platform=xhs
Douyin:      douyin.com/user/<sec_uid>                → platform=douyin
Douyin creator center:
             creator.douyin.com/creator-micro/...     → platform=douyin, backend available
```

Expand short links (`xhslink.com`, `v.douyin.com`) first. If no `user_id` survives parsing, ask for the full profile URL.

### 2. Capture, then write `profile.json`

Open the profile with a browser tool and capture only what is actually rendered:

- nickname, platform ID, IP region
- bio **verbatim, line by line** — never paraphrase
- tags, following, followers, likes
- first 10–12 posts: title text, like count, pinned flag, cover text if any
- when the creator center is available: 7-day and 30-day plays, completion rate, interaction rate, follower delta

Write it against [`scripts/profile.schema.json`](scripts/profile.schema.json). Fill unknown fields with `null` — **never with 0, never with a guess.**

Capture rules:

- Login wall → report **BLOCKED**, do not enter credentials, do not retry more than twice
- CAPTCHA / risk control → same
- A post hides its like count → `null`, not `0`
- Always record `captured_at`; the report must display it

### 3. Score with the script, never by hand

```bash
python scripts/score_account.py examples/sample-profile.json --out examples/sample-score.json
```

The script computes: nickname search terms, bio four elements, follower/following ratio, like spread and median, title prefix patterns, topic distribution, backend vs baseline deltas. It outputs per-item score + deduction reason + measured/missing flag + module rates + the primary bottleneck + the grade.

Two protections are built in. **Do not override them by hand:**

1. **Coverage gate** — a module measured below 70% of its full marks cannot compete for "lowest"; you can't tell a true weakness from an unmeasured one.
2. **No-bottleneck rule** — if every qualifying module scores ≥70%, output `main = null` plus "no significant primary bottleneck", and state how many points are unmeasured. Calling a 91% module "the main problem" is nonsense.

Items requiring human judgement (avatar credibility, grid consistency, cover readability, hook quality, comment handling) go into the `manual` field of the JSON. **Look at the image before scoring it.** If you can't, write `null`.

### 4. Emit the HTML report

Nine fixed sections: header → one-line verdict → score table + six module cards → radar → funnel → issue list → what not to do → where this report may be wrong → credibility statement.

- Zero dependencies: inline SVG + CSS, no CDN, opens offline
- A4 landscape, printable, red-gold palette (#C41230 / #CAAA74)
- Every number must be traceable to `score.json`. Any hand-adjusted score must be labelled "manual adjustment" in the report
- Layout reference: [`examples/sample-report-xhs.html`](examples/sample-report-xhs.html), [`examples/sample-report-douyin.html`](examples/sample-report-douyin.html)
- Full spec: [`references/report-spec.md`](references/report-spec.md)

---

## Scoring system

Six modules, 24 items, 100 points per platform.

| Module | Xiaohongshu | Douyin | What it measures |
|---|---|---|---|
| M1 Account layer | 16 | 14 | Nickname search terms, avatar credibility, bio four elements, grid consistency |
| M2 Content layer | 30 | 32 | Title prefix, cover readability, opening hook, value type, keywords, closing CTA, shareable artifact, completion structure |
| M3 Structure layer | 14 | 14 | Topic mix, posting cadence, time-slot distribution, series consistency |
| M4 Data layer | 22 | 28 | Impressions, click/completion rate, interaction rate, follower growth |
| M5 Conversion layer | 12 | 8 | Profile hand-off, comment handling, enquiry path |
| M6 Differentiation | 6 | 4 | One-sentence difference, overlap with peers |

Full rubrics: [`references/xhs-scoring.md`](references/xhs-scoring.md), [`references/douyin-scoring.md`](references/douyin-scoring.md).

**Scores are not cross-platform comparable.** Two different tables with different weights. An Xiaohongshu 38 and a Douyin 45 say nothing about each other.

Grade bands: 90 S / 80 A / 70 B / 60 C / <60 D. **If ≥30 points are unmeasured, no grade is issued.**

---

## Hard boundaries

1. **Capture failure is a valid result.** BLOCKED is a legitimate output. Never substitute "an account I saw before that looked similar".
2. **Read-only.** No likes, follows, comments, or edits. No login walls bypassed.
3. **Only script-computed scores count.** Every figure in the report must exist in `score.json`.
4. **No certainty, no promises.** No "this will go viral", no "guaranteed follower growth". Give evidence, direction, and a probability framing.
5. **One bottleneck per report.** Other modules are recorded, not actioned. Changing five things at once makes attribution impossible.
6. **Don't infer shadow-banning.** An empty analytics panel is a data gap, not a platform punishment.

---

## Known limits

- Public profiles expose a ceiling of roughly **46 / 100** on both platforms (measured on one account each, 2026-10-24 — an empirical value, not a platform rule).
- **Douyin public profiles give likes only, no play counts**, and post titles require opening each post. Creator-center analytics are the only source of plays/completion/retention.
- The Douyin creator center renders **about 5 posts** at a time and warns that sorting covers only the last 90 days — expect small samples.
- Five Douyin content items (first 3 seconds, first frame, closing CTA, shareable artifact, completion structure) **require actually watching the video**. Backend data cannot substitute, which is why Douyin's ceiling is lower than Xiaohongshu's.
- Xiaohongshu often hides like counts on some posts; collections pages are usually private.
- Accounts with tightened privacy may expose only nickname and bio.
- **Validated on 2 real accounts** (same owner, both platforms, 2026-10-24). The rest are constructed fixtures. Review the first report of any batch by hand before trusting it at scale.

---

## File map

```
account-diagnose-runner/
├── SKILL.md                    this file
├── README.md                   bilingual overview (EN / 中文)
├── LICENSE                     MIT
├── references/
│   ├── xhs-scoring.md          24-item rubric, Xiaohongshu
│   ├── douyin-scoring.md       24-item rubric, Douyin
│   └── report-spec.md          9-section report spec + failure-mode library
├── scripts/
│   ├── score_account.py        scorer (stdlib only, Python 3.8+)
│   └── profile.schema.json     capture contract
└── examples/
    ├── sample-profile.json     fictional account, all fields populated
    ├── sample-score.json       its scorer output
    ├── sample-report-xhs.html  rendered sample, Xiaohongshu
    └── sample-report-douyin.html rendered sample, Douyin
```
