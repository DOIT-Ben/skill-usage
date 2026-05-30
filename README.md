# skill-usage

`skill-usage` analyzes your AI agent conversation history to show which skills you actually use, how often, and which ones are just taking up space.

`skill-usage` 是一个 AI agent 技能使用分析工具。它扫描你的对话历史，告诉你哪些 skill 真的在用、哪些只是装了没用、哪些可以安全清理。

## Why This Exists / 为什么需要它

AI agents accumulate skills over time. After installing dozens or hundreds of skills, you lose track of:

- Which skills you actually depend on vs. which are just listed in system prompts
- Which skills are used once and forgotten
- Which skills are worth keeping when cleaning up disk space
- How your skill usage patterns change over time

`skill-usage` scans your Codex, Claude Code, and Hermes conversation logs, distinguishes real usage from metadata noise, and gives you a ranked report with evidence.

AI agent 用久了会积累大量 skill。装了几十上百个之后，你会不知道：

- 哪些 skill 真的在用，哪些只是出现在 system prompt 里
- 哪些 skill 用过一次就忘了
- 清理磁盘时哪些可以安全删除
- 你的 skill 使用习惯随时间怎么变化

`skill-usage` 扫描你的 Codex、Claude Code、Hermes 对话日志，区分真实使用和元数据噪音，给你一份有证据的排行榜。

## Who It Is For / 适合谁

- 想知道自己最常用哪些 skill 的人
- 需要清理磁盘、删除无用 skill 的人
- 想验证新装的 skill 是否真的被用上的人
- 需要统计团队 skill 使用情况的人

## What You Get / 你会得到什么

- **真实命中排行**：按真实使用次数排序，不是"被列出"次数
- **跨平台统计**：Codex + Claude Code + Hermes 全覆盖
- **真假区分**：区分"真的读了 SKILL.md"和"只是出现在路径里"
- **会话覆盖率**：每个 skill 跨多少个会话使用
- **时间范围**：首次使用和最近使用日期
- **清理建议**：哪些 skill 零使用可以安全删除

## Quick Start / 快速开始

### Installation

```bash
# Clone or download this skill
git clone https://github.com/DOIT-Ben/skill-usage.git

# Or install via npx skills (if published)
npx skills add DOIT-Ben/skill-usage -g
```

### Usage

In your AI agent conversation:

```
Use skill-usage to analyze my skill usage history
```

Or directly:

```
/skill-usage
```

The skill will:
1. Scan your conversation logs (Codex, Claude Code, Hermes)
2. Distinguish real usage from metadata noise
3. Generate a ranked report with:
   - Top skills by real usage
   - Skills by tier (主力/常用/偶用/尝试/零使用)
   - Cleanup recommendations

### Output

You'll get:

- **Console report**: Top 60 skills ranked by real usage
- **JSON file**: `skill-usage-report.json` with full data for all skills
- **Tier breakdown**: How many skills in each usage tier

## How It Works / 工作原理

### Real Usage Detection

The analyzer distinguishes **real usage** from **metadata noise** by checking:

1. **Subfile access**: Did the agent read `SKILL.md`, `reference.md`, or other skill files?
2. **Real operations**: Did the skill path appear in `Read`, `Bash`, `cat`, `Get-Content`, or similar commands?
3. **Turn deduplication**: Multiple accesses in the same turn count as one usage

### Path Coverage

Supports all common skill locations:

- `~/.agents/skills/`
- `~/.codex/skills/`
- `~/.claude/skills/`
- `~/.hermes/skills/`
- `~/.codex/plugins/cache/*/skills/`
- OpenAI bundled skills

### Platform Support

- **Codex**: Parses `response_item` with `function_call` and `function_call_output`
- **Claude Code**: Parses `tool_use` blocks and explicit `Skill` tool calls
- **Hermes**: Parses `tool_calls` and `tool` role messages

### JSON Escape Handling

Handles nested JSON escaping (e.g., `\\\\skills\\\\` in double-encoded strings).

## Output Schema / 输出格式

### JSON Report

```json
{
  "generatedAt": "2026-05-30T...",
  "scanned": {
    "codex": 762,
    "claude": 125,
    "hermes": 16
  },
  "summary": {
    "totalLines": 866955,
    "fnCalls": 150495,
    "hits": 11933,
    "realHits": 9660,
    "uniqueSkills": 721
  },
  "ranking": [
    {
      "skill": "superpowers",
      "calls": 1287,
      "realCalls": 1284,
      "ratio": 3.39,
      "realRatio": 100,
      "sessions": 380,
      "realSessions": 380,
      "sources": "codex:1286,claude:1",
      "firstSeen": "2026-05-12",
      "lastSeen": "2026-05-30"
    }
  ]
}
```

### Field Definitions

| Field | Description |
|---|---|
| `skill` | Skill name |
| `calls` | Total turn-deduplicated hits |
| `realCalls` | Hits with subfile access or real operations |
| `ratio` | calls / sessions (higher = more intensive use) |
| `realRatio` | realCalls / calls * 100 (percentage of real usage) |
| `sessions` | Number of unique sessions |
| `realSessions` | Sessions with real usage |
| `sources` | Platform breakdown (codex:N, claude:N, hermes:N) |
| `firstSeen` | First usage date (YYYY-MM-DD) |
| `lastSeen` | Most recent usage date (YYYY-MM-DD) |

## Tiers / 使用梯队

| Tier | Real Calls | Meaning |
|---|---|---|
| ★★★ 主力 | ≥ 100 | Core skills you depend on |
| ★★ 常用 | 20-99 | Frequently used |
| ★ 偶用 | 5-19 | Occasionally useful |
| · 尝试 | 1-4 | Tried but not adopted |
| ○ 零使用 | 0 | Never actually used (safe to remove) |

## Cleanup Recommendations / 清理建议

Skills with `realCalls: 0` are safe to remove. They appear in system prompts but were never actually invoked.

Before removing, check:
- Is it a recently installed skill you plan to use?
- Is it a dependency of another skill?
- Does it have sentimental value?

## Limitations / 局限性

- **History only**: Only analyzes past usage, not future intent
- **Local logs**: Only scans logs on the current machine
- **No live monitoring**: Runs on-demand, not real-time
- **Path-based detection**: Skills invoked without file access may be undercounted

## License

MIT License

Copyright (c) 2026 Skill Usage Maintainers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

Issues and pull requests welcome at https://github.com/DOIT-Ben/skill-usage

## Changelog

See [CHANGELOG.md](CHANGELOG.md)
