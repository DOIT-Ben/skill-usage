# skill-usage

`skill-usage` is an audit-grade skill usage analyzer for AI agent logs. It ranks which skills are actually used, separates strict invocation evidence from noisy mentions, and reports which sources were scanned or excluded.

`skill-usage` 是一个用于统计 AI agent 技能命中率的审计型 skill：它不只 grep 技能名，而是区分真实调用、系统提示噪声、路径清单噪声和补充日志来源，最后给出排名与整理建议。

## Why This Exists / 为什么需要它

AI agents accumulate skills over time. After installing dozens or hundreds of skills, you need to know:

- Which skills are actually loaded or read by the agent
- Which skills only appear in system prompts, paths, inventories, or old reports
- Which session roots were scanned and which roots were intentionally kept separate
- Which skills should stay active, move external, merge aliases, or improve descriptions

## What You Get / 你会得到什么

- **Canonical ranking**: ranked by `strictCalls`, not raw text mentions
- **Noise separation**: `strictCalls`, `wideMentions`, `rawRefs`, sessions, and source breakdowns
- **Coverage audit**: primary, supplement, corpus, SQLite, and noisy request/log source boundaries
- **Recommendations**: resident, thin router, external/archive, description rewrite, alias normalization
- **Local-only privacy**: reports aggregate skill names and counts, not raw prompts or secret values

## Quick Start / 快速开始

```bash
git clone https://github.com/DOIT-Ben/skill-usage.git
```

In an agent conversation:

```text
Use skill-usage to rank all skills and explain strict usage vs noisy mentions.
```

Or run the scanner directly:

```powershell
$skill = "<path-to-skill-usage>"
$env:OUTPUT_DIR = (Get-Location).Path
Remove-Item Env:\INCLUDE_SQLITE -ErrorAction SilentlyContinue
python "$skill\scripts\deep_skill_usage_scan.py"
```

## Outputs / 输出

The deep scanner writes:

- `skill-usage-deep-report.json`
- `skill-usage-ranking-deep.md`
- `skill-usage-source-audit.md`
- `skill-usage-ranking-deep.csv`

The legacy lightweight analyzer is still available at:

```powershell
node "$skill\scripts\analyzer-legacy.js"
```

## Evidence Model / 统计口径

| Field | Meaning |
|---|---|
| `strictCalls` | Strong evidence of real skill loading or invocation, such as a Skill tool call or reading `SKILL.md` in execution context. |
| `wideMentions` | Mentions in prompts, system skill lists, paths, docs, permission rules, reports, or caches. Useful as demand/noise signal, not usage count. |
| `rawRefs` | Raw references before turn/session dedupe. Diagnostic only. |
| `strictSessions` | Unique sessions with strict usage evidence. |
| `realRatio` | `strictCalls / wideMentions`; a routing/noise smell, not an absolute quality score. |

## Coverage / 覆盖范围

Primary ranking sources include:

- Codex sessions and archived sessions
- Codex rollout summaries
- Claude project transcripts
- Hermes sessions and logs
- OpenClaw / AutoClaw sessions
- Cursor agent transcripts
- Mini-agent logs

Supplement sources are scanned separately by default when relevant:

- Cursor / VS Code workspace storage
- Codex desktop logs
- Claude local-agent-mode sessions
- Continue.dev, Trae, Windsurf, opencode, WorkBuddy, CodeBuddy logs
- SQLite state/log databases when `INCLUDE_SQLITE=1` or `ONLY_SQLITE=1`

See `references/coverage-and-noise-map.md` for the source boundary rules.

## Recommendation Rules / 建议规则

| Action | Trigger |
|---|---|
| Keep resident | High `strictCalls` or broad weekly cross-session use |
| Add thin router | High need but heavy or low-frequency body |
| Improve description | High `wideMentions`, low `strictCalls`, clear task demand |
| Merge alias | Same capability split across names or versions |
| Keep external | Useful but narrow, low strict usage |
| Archive or ignore | No strict usage and only noise mentions |

Do not treat `strictCalls = 0` as automatic deletion. It is an archive/external-review candidate, especially for recently installed or strategically important skills.

## Environment Variables / 环境变量

| Variable | Purpose |
|---|---|
| `OUTPUT_DIR` | Directory for generated reports. Defaults to current directory. |
| `REPORT_SUFFIX` | Adds a sanitized suffix to report filenames. |
| `EXTRA_PATHS_FILE` | Text file of extra paths to scan, one path per line. |
| `ONLY_EXTRA=1` | Scan only paths from `EXTRA_PATHS_FILE`. |
| `ONLY_SQLITE=1` | Scan only SQLite sources. |
| `INCLUDE_SQLITE=1` | Include built-in and extra SQLite sources. |
| `SKIP_SQLITE=1` | Skip SQLite sources. |
| `ONLY_SOURCES` | Comma-separated source labels to include. |
| `MAX_TEXT_BYTES` | Max size for a single text file. |

## Privacy / 隐私

All analysis is local. The report should contain aggregate skill names, counts, dates, and source labels only. Do not publish raw prompts, session content, account data, tokens, local personal paths, or unrelated user text.

## Canonical Name / 唯一名称

The canonical repository and skill name is:

```text
skill-usage
```

`skill-usage-auditor` has been merged into this package as the deep audit workflow.

## License

MIT License. See `LICENSE`.
