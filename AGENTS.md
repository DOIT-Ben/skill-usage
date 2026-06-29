# Project Rules for Codex

## Project Overview

- Project name: `skill-usage`
- Project type: public AI skill package
- Canonical skill entry: `SKILL.md`
- Canonical package name: `skill-usage`
- Main deliverables: deep audit scanner, SKILL.md, README, changelog, plugin metadata, references, evals

## Working Mode

- Use lightweight edits for wording, documentation, and examples
- Use stricter review when changing analyzer logic, path patterns, or output schema

## Maintenance Principles

- Maintain one canonical package for all platforms (Codex, Claude Code, Hermes)
- Keep `skill-usage` as the only canonical name
- Preserve cross-platform compatibility (don't hardcode paths)
- Keep analyzer logic platform-agnostic
- Maintain real usage detection accuracy
- Preserve tier definitions and thresholds

## Core Analyzer Requirements

- Must scan Codex, Claude Code, Hermes, and supported agent/editor transcript roots.
- Must handle JSON escaping (single, double, quadruple backslashes)
- Must distinguish real usage from metadata noise
- Must deduplicate by (platform, session, turn, skill)
- Must calculate both raw and real usage metrics
- Must support all common skill path patterns

## Path Patterns to Support

Required patterns:
- `~/.agents/skills/<name>`
- `~/.codex/skills/<name>`
- `~/.claude/skills/<name>`
- `~/.hermes/skills/<name>`
- `~/.codex/plugins/cache/*/skills/<name>`
- OpenAI bundled skills paths

## Real Usage Signals

Must detect:
1. Subfile access: `/skills/foo/SKILL.md`, `/skills/foo/reference.md`, etc.
2. Real operations: `Read`, `Bash`, `cat`, `Get-Content`, `grep`, `Glob`, etc.
3. Multiple accesses in same turn (indicates active use)

## Output Requirements

Must generate:
1. JSON file with full ranking
2. Markdown ranking report
3. CSV ranking report
4. Source audit report
5. Recommendations grouped by resident, external/archive, description rewrite, and alias normalization

## Tier Definitions (Do Not Change)

- ★★★ 主力: strictCalls ≥ 100
- ★★ 常用: strictCalls 20-99
- ★ 偶用: strictCalls 5-19
- · 尝试: strictCalls 1-4
- ○ 仅提及: strictCalls = 0

## Verification

Before publishing, verify:
- Analyzer runs on Windows, macOS, Linux
- Handles missing log directories gracefully
- Handles malformed JSONL gracefully
- JSON output is valid
- Markdown, CSV, and source-audit outputs are created
- Tier counts add up correctly
- Real usage detection works for all platforms

## Privacy and Security

- All analysis must be local
- No data sent to external services
- No credentials or secrets in logs
- Safe to run on any machine

## Testing

Test with:
- Empty log directories
- Malformed JSONL files
- Mixed platform logs
- Large log files (1M+ lines)
- Skills with special characters in names
- Skills with Chinese names

## Commit Guidelines

- Keep commits focused and atomic
- Use conventional commit format
- Test analyzer before committing logic changes
- Update CHANGELOG.md for user-facing changes

## Release Process

1. Update version in plugin.json
2. Update CHANGELOG.md
3. Test analyzer on all platforms
4. Commit and tag release
5. Push to GitHub
6. Create GitHub release with notes

Only commit files in this repository. Do not commit:
- Local install directories
- Generated reports (*.json, *.md, *.csv)
- Log files
- Caches
- User-specific paths

<!-- TEAM-COLLABORATION:START protocol=2.0.0 -->
## 团队协作机制

本项目已启用 `agents-team`。开始开发任务前，读取 `.codex/team-collaboration.json`。

- 所有正式任务必须先有清晰、可观察的 Goal。
- L2/L3 必须使用 GitHub Issue；Issue 必须依次包含 Goal、必须完成、验收门禁、任务边界、风险等级、依赖与阻塞条件。
- “必须完成”缺一项、验收门禁未通过或任务边界被突破时，不得宣布完成。
- L1 可由主 Codex 直接处理；L2 必须独立 QA；L3 实施前必须获得用户确认，实施后必须独立复核与 QA。
- 执行智能体只能声明代码级完成，不得声明 QA PASS、可上线或发布完成。
- 指定测试失败时必须修复实现，不得删除测试或用无解释的 skip/xfail 规避。
- GitHub Issue 管承诺，Pull Request 管事实，QA 管结论；不得维护第二套动态任务台账。
- 真实数据、权限、密钥、付费 Provider、不可逆操作和生产发布必须暂停并请求用户确认。
- 所有改动必须遵守项目级测试命令、高风险路径和保护文件配置。
<!-- TEAM-COLLABORATION:END -->
