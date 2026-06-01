# Report Template

Use this template for final Markdown reports.

## Title

`# Skill Usage Audit`

## Executive Summary

Start with 3-5 bullets:

- Whether the old workflow missed sources or overcounted noise.
- Canonical totals: skills, strict calls, wide mentions, files scanned.
- Discovery totals: primary, supplement, corpus, noise, unknown.
- The top skill groups by strict usage.
- The most important action recommendation.

## Coverage

Include this table:

| Layer | Files | Unique Skills | Strict Calls | Wide Mentions | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| primary transcript/session |  |  |  |  | canonical ranking |
| expanded session supplement |  |  |  |  | compare only |
| agent/editor supplement |  |  |  |  | not merged unless justified |
| legacy/corpus supplement |  |  |  |  | historical intent only |
| noisy request/log sources |  |  |  |  | excluded from canonical |

## Main Ranking

Use this table:

| Rank | Skill | Tier | Strict Calls | Wide Mentions | Strict Sessions | Sessions | Real Ratio | Recommendation |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |

Recommended tier labels:

- `★★★ 主力`: `strictCalls >= 100`
- `★★ 常用`: `strictCalls >= 20`
- `★ 偶用`: `strictCalls >= 5`
- `· 尝试`: `strictCalls >= 1`
- `○ 仅提及`: `strictCalls == 0`

## Supplemental Ranking

Explain why it is separate:

```text
补充榜用于发现漏扫源和噪声，不直接改变主榜。只有当补充源能证明是干净会话记录时，才合并到 expanded session ranking。
```

## Missed Source Analysis

Use concise bullets:

- Missed primary roots:
- Added supplement roots:
- Excluded noise roots:
- Unknown/mixed roots needing manual review:

## Recommendations

Group by action:

| Action | Skills | Reason |
| --- | --- | --- |
| Keep resident / add thin router |  | High strict usage and broad sessions. |
| Improve description |  | High demand or wide mentions but low strict usage. |
| Alias merge / normalize |  | Same capability split across names or versions. |
| Keep external/archive |  | Low strict usage or niche workflow. |
| Do nothing |  | Noise-only mention or obsolete item. |

## Verification

End with:

- Commands/scripts run.
- Output artifact paths.
- Parse or health checks.
- Known limitations.

If the report includes per-source columns, make sure the main ranking uses deduped source counts that match the row-level strict/wide semantics. Keep raw source repetition in separate diagnostic fields only.

Never include raw session prompts or sensitive account/token values.
