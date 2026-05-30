# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-30

### Added
- Initial release of skill-usage analyzer
- Cross-platform conversation log scanning (Codex, Claude Code, Hermes)
- Real usage detection (distinguishes actual usage from metadata noise)
- Turn-based deduplication to avoid counting system prompt listings
- Support for all common skill path patterns:
  - `~/.agents/skills/`
  - `~/.codex/skills/`
  - `~/.claude/skills/`
  - `~/.hermes/skills/`
  - `~/.codex/plugins/cache/*/skills/`
- JSON escape handling (single, double, quadruple backslashes)
- Tier-based ranking system (主力/常用/偶用/尝试/零使用)
- Cleanup recommendations for unused skills
- JSON report output with full metrics
- Console report with top 60 skills and tier breakdown

### Features
- **Real usage signals**: Detects subfile access and real operations
- **Usage intensity**: Calculates calls/sessions ratio
- **Time range**: Tracks first and last usage dates
- **Platform breakdown**: Shows usage distribution across Codex/Claude/Hermes
- **Session coverage**: Counts unique sessions per skill

### Metrics
- `calls`: Total turn-deduplicated hits
- `realCalls`: Hits with real usage signals
- `ratio`: Usage intensity (calls per session)
- `realRatio`: Percentage of real usage
- `sessions`: Unique sessions
- `realSessions`: Sessions with real usage
- `sources`: Platform breakdown
- `firstSeen`, `lastSeen`: Date range

[1.0.0]: https://github.com/DOIT-Ben/skill-usage/releases/tag/v1.0.0
