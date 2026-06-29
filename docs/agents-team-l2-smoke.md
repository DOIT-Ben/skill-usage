# Agents-Team L2 smoke trial

This branch is an isolated trial of Agents-Team 0.3.0. It must not be merged
into `main` without a separate decision.

## Scope

- Generated the repository adapter, contracts, and Collaboration Gate.
- Did not modify the skill scanner, ranking rules, privacy behavior, or release.
- Used no real session data, credentials, paid providers, or production systems.

## Initialization evidence

- Command: `python3 plugins/agents-team/scripts/initialize_project.py <trial> --apply`
- Exit code: `0`
- Result: `11` adapter files created.
- Project profile: `generic`; the repository has no root Python project manifest.

## Local validation evidence

- Command: `python .codex/scripts/validate_team_collaboration.py .`
- Exit code: `0`
- Result: `team collaboration project adapter: valid`

## Preflight failure

- Symptom: the first projected adapter replaced the existing AGENTS.md and the
  comparison showed 117 deleted lines.
- Root cause: initialization was run against an empty local projection rather
  than a complete checkout, so existing project rules were absent.
- Correction: restored the complete existing AGENTS.md and appended only the
  managed collaboration block. The final comparison has zero deletions.

## GitHub gate evidence

Pending. The trial first submits intentionally incomplete PR evidence to prove
that the gate fails closed, then replaces it with current-head evidence.

## Rollback

Close the trial pull request and delete `test/agents-team-l2-smoke`.
