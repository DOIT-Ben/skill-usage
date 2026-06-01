---
name: skill-usage
description: Use when the user asks to rank skills, analyze skill hit rate, audit missed skill calls, scan Codex/Claude/OpenClaw/Hermes/Cursor/agent session logs, compare strict skill invocations with noisy mentions, or investigate whether skill usage statistics missed session directories.
---

# Skill Usage

## Core Idea

This skill audits skill usage by separating evidence into layers. A reliable ranking is not "grep every skill name and sort counts"; it is a pipeline that discovers all plausible session sources, separates strict invocation evidence from noisy mentions, and reports what was included, excluded, and still uncertain.

Use Chinese for user-facing reports when the user is Chinese. Keep private prompts, raw log content, tokens, account data, and unrelated session text out of the report.

## Operating Rule

Never promise universal coverage just because a scan ran. Promise a verifiable coverage audit:

1. What roots were scanned.
2. What roots were discovered but excluded as noise.
3. What was counted as strict usage.
4. What was counted only as wide mention.
5. What remains unknown or mixed.

## Evidence Levels

| Field | Meaning | Use |
| --- | --- | --- |
| `strictCalls` | Strong evidence of real skill loading or invocation, such as explicit Skill tool calls or reading/opening `SKILL.md` with execution context. | Main ranking and resident/active decisions. |
| `wideMentions` | Skill names or paths in prompts, system listings, permission rules, path tables, docs, or caches. | Demand/noise signal; not a hit-rate denominator by itself. |
| `rawRefs` | Raw references before de-duplication by session/turn/skill. | Diagnostic use only. |
| `strictSessions` | Sessions that contain strict evidence for a skill. | Breadth of actual use. |
| `realRatio` | `strictCalls / wideMentions`. | Trigger quality/noise smell, not absolute quality. |
| `strictSources` | Deduped source counts that match `strictCalls` semantics. | Source distribution in the main table. |
| `rawSources` / `strictRawSources` | Raw source counts before dedupe. | Diagnostic use only. |

## Required Workflow

### 1. Inventory Local Skill Names

Before scanning logs, collect skill names from active, external, disabled, and plugin-cache layers:

- `%USERPROFILE%\.agents\skills`
- `%USERPROFILE%\.agents\skills-external\incoming`
- `%USERPROFILE%\.agents\skills-disabled`
- `%USERPROFILE%\.codex\plugins\cache`

Normalize aliases only when they clearly point to the same skill. Preserve versioned names such as `code-1.0.4` unless the user asks for alias folding.

### 2. Discover Transcript Sources

Read `references/coverage-and-noise-map.md` before a full audit. The minimum canonical roots are Codex sessions, archived sessions, rollout summaries, Claude projects, Hermes sessions/logs, OpenClaw sessions, Cursor project transcripts, and mini-agent logs.

For "don't miss anything" requests, also scan the supplement roots listed in that reference, then keep them separate unless they contain clean session-like evidence.

### 3. Run The Scanner

Bundled script:

```powershell
$skill = '<path-to-skill-usage>'
$out = (Get-Location).Path
$env:OUTPUT_DIR = $out
Remove-Item Env:\INCLUDE_SQLITE -ErrorAction SilentlyContinue
python "$skill\scripts\deep_skill_usage_scan.py"
```

Useful environment variables:

| Variable | Purpose |
| --- | --- |
| `OUTPUT_DIR` | Directory for generated `skill-usage-*` reports. Defaults to current directory. |
| `REPORT_SUFFIX` | Adds a sanitized suffix to output filenames, e.g. `-codex-logs`. Non filename-safe characters are replaced. |
| `EXTRA_PATHS_FILE` | Text file containing additional paths, one per line. |
| `ONLY_EXTRA=1` | Scan only paths from `EXTRA_PATHS_FILE`. |
| `ONLY_SQLITE=1` | Scan only SQLite sources. |
| `INCLUDE_SQLITE=1` | Include built-in and extra SQLite sources. Use for supplement scans, not canonical ranking. |
| `SKIP_SQLITE=1` | Skip SQLite sources. |
| `ONLY_SOURCES` | Comma-separated source labels to include. |
| `MAX_TEXT_BYTES` | Max single text-file size to scan. Invalid values fall back to the default. |

### 4. Produce Four Outputs

Use `references/report-template.md` and always include:

1. Canonical ranking: primary transcript/session roots only.
2. Expanded session ranking: canonical plus newly discovered session-like supplement.
3. Discovery audit: scanned roots, candidate counts, noise counts, unknown/mixed buckets.
4. Recommendations: resident, external, alias, or description actions.

For the recommendation pass, apply `references/recommendation-rules.md` instead of inventing ad hoc labels.

### 5. Interpret Results

Use these rules:

- High `strictCalls` and broad `strictSessions`: candidate for resident or thin active router entry.
- High `wideMentions` but low `strictCalls`: likely system-prompt/path noise, weak trigger wording, or skill listed often but rarely loaded.
- High demand terms in user tasks but low strict usage: improve description and add routing examples.
- Low strict and low wide: keep archived/external unless strategically important.
- Huge editor/opencode/request logs with millions of mentions: use as coverage evidence, not canonical ranking.
- Built-in SQLite sources such as Codex logs/state are supplement scans by default; include them only when explaining coverage or duplication risk.

## Missed-Source Guardrail

If a previous result looked too small, run a discovery pass before reranking:

1. Search for session-like files by path/name.
2. Search for content hits containing `SKILL.md`, `.agents\skills`, `.codex\skills`, `.claude\skills`, `Available skills`, or `skill_name`.
3. Classify candidates into primary, supplement, corpus, unknown, and noise.
4. Explain why each supplement is or is not merged into the main ranking.

This guardrail is the part that was missing in the old workflow.

## When The User Asks For Parallel Subagents

If the user explicitly asks you to run multiple subagents, split the audit into disjoint read-only questions:

1. One subagent for coverage discovery and source boundaries.
2. One subagent for ranking interpretation and noise detection.
3. One subagent for output/template sanity and recommendation wording.

Do not duplicate the same search in multiple subagents.

## Common Mistakes

- Treating `wideMentions` as usage.
- Counting `git add .agents/skills/...`, permission allowlists, or "Available skills" inventories as strict calls.
- Mixing request/system prompt logs into the main ranking without de-duplication.
- Ignoring editor-side session stores such as Cursor/VS Code workspaceStorage, Trae/Windsurf history, opencode logs, or Codex desktop logs.
- Reporting a top-N ranking without source coverage, skipped files, and noise boundaries.
- Hiding uncertainty. If a bucket is mixed or noisy, say so.

## Final Response Shape

For user-facing summaries, lead with:

```text
结论：原流程漏的是“发现层”和“分层口径”，不是所有真实调用都漏了。
```

Then give:

- Main ranking top 20 or top 50.
- Coverage numbers.
- Missed/added roots.
- Recommendations by action.
- Paths to generated Markdown/CSV/JSON artifacts.

Keep raw session content out of the answer.
