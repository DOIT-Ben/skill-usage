# Changelog

## [1.1.0] - 2026-06-01

### Changed

- Made `skill-usage` the public package name for the deep skill usage audit workflow.
- Replaced the main skill instructions with strict-call, wide-mention, and coverage-audit semantics.
- Updated plugin metadata for the public `skill-usage` repository.

### Added

- Added `scripts/deep_skill_usage_scan.py`.
- Added source coverage and noise boundaries in `references/coverage-and-noise-map.md`.
- Added recommendation rules and report template references.
- Added eval prompts for source coverage, noisy mentions, and recommendation output.
- Added CSV ranking output alongside JSON and Markdown reports.

### Preserved

- Kept the original lightweight Node analyzer as `scripts/analyzer-legacy.js`.

## [1.0.0] - 2026-05-30

### Added

- Initial release of `skill-usage` analyzer.
- Cross-platform conversation log scanning for Codex, Claude Code, and Hermes.
- Real usage detection for actual use versus metadata noise.
- Turn-based de-duplication to avoid counting system prompt listings.
- Support for common skill path patterns.
- JSON escape handling.
- Tier-based ranking system.
- JSON report output with full metrics.
- Console report with top skills and tier breakdown.

[1.1.0]: https://github.com/DOIT-Ben/skill-usage
[1.0.0]: https://github.com/DOIT-Ben/skill-usage/releases/tag/v1.0.0
