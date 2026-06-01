# Recommendation Rules

Use these rules after generating the ranking tables.

## Ranking Dimensions

Sort the main table by:

1. `strictCalls` descending.
2. `strictSessions` descending.
3. `realRatio` descending.
4. `lastSeen` descending.

Do not sort by `wideMentions` unless the user asks for noisy demand signals.

## Action Classes

| Action | Trigger | Recommendation Text |
| --- | --- | --- |
| Keep resident | `strictCalls >= 100` or weekly use across many sessions | `保留常驻：真实调用高，跨会话稳定。` |
| Add thin router | High need but heavy/low-frequency body | `加薄入口：常驻只放路由，正文留外置。` |
| Improve description | High `wideMentions`, low `strictCalls`, clear task demand | `优化 description：用户/系统经常提到，但没有稳定触发。` |
| Merge alias | Same capability split across names or versions | `合并别名：减少统计分裂和路由歧义。` |
| Keep external | Useful but narrow, low strict usage | `保留外置：需要时由 router-skills 调用。` |
| Archive or ignore | No strict usage and only noise mentions | `无需处理：目前只是路径或系统提示噪声。` |

## Real Ratio Interpretation

`realRatio` is a smell detector, not a value score.

- High strict + high ratio: strong routing.
- High strict + low ratio: real use exists, but inventories/logs inflate mentions.
- Low strict + high wide: investigate trigger wording or noise source.
- Low strict + low wide: likely low priority.

## Description Rewrite Guidance

When improving a skill description:

- Start with `Use when`.
- Describe triggering situations, not the workflow.
- Include user phrasing variants in English and Chinese when relevant.
- Avoid saying the whole process in frontmatter; put process in the body.
- Keep active-root skills lean; route heavy workflows through external skills.

## Alias Folding Guidance

Only fold aliases after checking evidence. Do not blindly combine names that look similar.

Good candidates:

- Same repo/version variants that clearly replaced each other.
- Old and new names with identical trigger domain.
- Plugin-prefixed and unprefixed names that point to the same skill body.

Bad candidates:

- Parent workflow and child workflow with different responsibilities.
- A broad router skill and a narrow execution skill.
- Different vendors that share a generic word like `browser`.
