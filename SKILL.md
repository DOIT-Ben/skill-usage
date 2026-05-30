---
name: skill-usage
description: "Analyze AI agent conversation history to show which skills you actually use vs. which are just taking up space. Scans Codex, Claude Code, and Hermes logs, distinguishes real usage from metadata noise, and provides ranked reports with cleanup recommendations."
triggers: [skill-usage, analyze-skills, skill-stats]
---

# Skill Usage Analyzer

Use this skill when the user wants to:
- Analyze which skills they actually use
- Find out which skills are safe to remove
- Get statistics on skill usage patterns
- Understand their skill usage history
- Clean up unused skills

## Core Principle

Scan conversation logs from Codex, Claude Code, and Hermes to distinguish **real skill usage** (agent actually read SKILL.md or executed skill code) from **metadata noise** (skill name appeared in system prompt).

## When To Use

- User asks "which skills do I use most?"
- User asks "which skills can I safely delete?"
- User wants to analyze skill usage patterns
- User mentions "skill statistics" or "skill analytics"
- User wants to clean up their skills directory

## When Not To Use

- User wants to install or update skills (use `skill-installer` instead)
- User wants to create new skills (use `skill-creator` instead)
- User wants to search for available skills (use `find-skills` instead)

## How It Works

### 1. Locate Conversation Logs

Scan these locations (cross-platform):
- `$CODEX_HOME/sessions/**/*.jsonl` (Codex CLI)
- `$CLAUDE_HOME/projects/**/*.jsonl` (Claude Code)
- `$HERMES_HOME/*.jsonl` (Hermes)

Default homes:
- Codex: `~/.codex`
- Claude: `~/.claude`
- Hermes: `~/.hermes`

### 2. Parse Platform-Specific Formats

**Codex**: Look for `response_item` records with:
- `type: "function_call"` → check `arguments` field
- `type: "function_call_output"` → check `output` field

**Claude Code**: Look for:
- `type: "assistant"` with `tool_use` blocks → check `input` field
- `name: "Skill"` with explicit skill invocation → record as high-confidence
- `type: "user"` with `tool_result` → check `content` field

**Hermes**: Look for:
- `role: "assistant"` with `tool_calls` → check `function.arguments`
- `role: "tool"` → check `content` field

### 3. Extract Skill Names with Real Usage Detection

Use regex patterns to match skill paths:
```
/.agents/skills/<name>
/.codex/skills/<name>
/.claude/skills/<name>
/.hermes/skills/<name>
/.codex/plugins/cache/*/skills/<name>
```

Handle JSON escaping (single, double, quadruple backslashes).

**Real usage signals**:
- Path includes subfile: `/skills/foo/SKILL.md` or `/skills/foo/reference.md`
- Appears in real operation: `Read`, `Bash`, `cat`, `Get-Content`, `grep`, etc.
- Multiple accesses in same turn (indicates active use, not just listing)

### 4. Deduplicate by Turn

Group by `(platform, sessionId, turnId, skillName)` to avoid counting:
- Multiple file reads in same turn as separate uses
- System prompt listings as usage

### 5. Calculate Metrics

For each skill:
- `calls`: Total turn-deduplicated hits
- `realCalls`: Hits with real usage signals
- `sessions`: Unique sessions
- `realSessions`: Sessions with real usage
- `ratio`: calls / sessions (usage intensity)
- `realRatio`: realCalls / calls * 100 (real usage percentage)
- `firstSeen`, `lastSeen`: Date range

### 6. Rank and Tier

Sort by `realCalls` descending.

Tiers:
- ★★★ 主力 (real ≥ 100): Core dependencies
- ★★ 常用 (real 20-99): Frequently used
- ★ 偶用 (real 5-19): Occasionally useful
- · 尝试 (real 1-4): Tried but not adopted
- ○ 零使用 (real = 0): Never actually used (safe to remove)

### 7. Generate Report

Output:
1. **Console summary**: Top 60 skills, tier breakdown
2. **JSON file**: `skill-usage-report.json` with full ranking
3. **Cleanup recommendations**: List skills with `realCalls: 0`

## Implementation

The analyzer is implemented in `analyzer.js` (Node.js script).

When invoked:
1. Run `node analyzer.js` from the skill directory
2. Read the generated `skill-usage-report.json`
3. Present the top 60 skills in a formatted table
4. Show tier breakdown
5. Highlight cleanup candidates (realCalls = 0)

## Output Format

### Console Report

```
=== Top 60 真实主力榜（按 realCalls 排序）===
rank  real  calls  realSess  比值   真率   skill
----  ----  -----  --------  -----  -----  ----------------------------------
   1  1284   1287       380   3.39   100%  superpowers
   2   410    427       232   1.79    96%  web-access
   3   324    337        99   3.30    96%  jobs-design
...

=== 全部 skill 计数分布（按真实命中分梯队）===
★★★ 主力 (real≥100): 18 个
★★  常用 (real 20-99): 79 个
★   偶用 (real 5-19): 114 个
·   尝试 (real 1-4): 182 个
○   仅列出/未真用 (real=0): 328 个
```

### JSON Schema

See README.md for full schema.

## Error Handling

- If log directories don't exist, skip gracefully
- If JSONL is malformed, skip that line and continue
- If no skills found, report "No skill usage detected"
- If analyzer.js fails, show error and suggest manual run

## Privacy Note

All analysis is local. No data is sent to external services.

## Verification

After running, verify:
- JSON report exists and is valid
- Top skills match user's intuition
- Tier counts add up to total unique skills
- Cleanup candidates (real=0) are actually unused

## Next Steps After Analysis

Suggest:
- Review cleanup candidates before removing
- Check if low-usage skills are recent installs
- Consider archiving "尝试" tier skills for later
- Keep "主力" and "常用" tier skills

## Example Invocation

User: "Which skills do I actually use?"

Agent:
1. Invoke this skill
2. Run analyzer
3. Present top 20 skills
4. Show tier breakdown
5. Highlight any skills with 0 real usage
6. Ask if user wants full report or cleanup recommendations
