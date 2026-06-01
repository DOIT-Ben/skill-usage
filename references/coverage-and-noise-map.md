# Coverage And Noise Map

Use this map to prevent undercounting and overcounting in skill-usage audits.

## Canonical Primary Sources

These are clean enough for the main ranking when parsed with strict evidence rules.

| Root | Class | Notes |
| --- | --- | --- |
| `%USERPROFILE%\.codex\sessions` | primary | Codex CLI/app session transcripts. |
| `%USERPROFILE%\.codex\archived_sessions` | primary | Archived Codex sessions. |
| `%USERPROFILE%\.codex\memories\rollout_summaries` | primary | Summaries can contain evidence of skill use; keep de-duplicated. |
| `%USERPROFILE%\.claude\projects` | primary | Claude project transcripts. |
| `%USERPROFILE%\.hermes\sessions` | primary | Hermes session JSON/JSONL. |
| `%USERPROFILE%\.hermes\logs` | primary | Hermes logs with session-like records. |
| `%USERPROFILE%\.openclaw\agents` | primary | OpenClaw agent session logs. |
| `%USERPROFILE%\.openclaw-autoclaw\agents` | primary | AutoClaw/OpenClaw session logs. |
| `%USERPROFILE%\.openclaw-autoclaw\autoclaw\chat-history` | primary | AutoClaw chat history when present. |
| `%USERPROFILE%\.cursor\projects` | primary | Cursor agent transcripts. |
| `%USERPROFILE%\.mini-agent\log` | primary | Mini-agent logs. |

## Supplement Sources

Scan these for coverage, but do not merge them into the canonical ranking unless the report explains why.

| Root | Class | Default Decision |
| --- | --- | --- |
| `%APPDATA%\Cursor\User\workspaceStorage` | agent supplement | Often mixed state/log data. |
| `%APPDATA%\Code\User\workspaceStorage` | agent supplement | Often mixed state/log data. |
| `%LOCALAPPDATA%\Codex\Logs` | agent supplement | Useful but often duplicates request/system logs. |
| `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\local-agent-mode-sessions` | agent supplement | Claude UWP/local-agent mode sessions. |
| `%USERPROFILE%\.continue\dev_data` | agent supplement | Continue.dev data. |
| `%USERPROFILE%\.cursor-local-assistant-v2\history` | agent supplement | Local assistant history. |
| `%APPDATA%\Trae CN\User\History` | agent supplement | Editor history, high noise risk. |
| `%APPDATA%\Windsurf\User\History` | agent supplement | Editor history, high noise risk. |
| `%USERPROFILE%\.local\state\opencode` | agent supplement | High repeated prompt/listing noise. |
| `%USERPROFILE%\.local\share\opencode` | agent supplement | Includes DB/log data; keep separate by default. |
| `%APPDATA%\WorkBuddy\logs` | agent supplement | Tool logs. |
| `%APPDATA%\CodeBuddy\logs` | agent supplement | Tool logs. |

## SQLite Sources

Built-in SQLite sources are useful for coverage audits, but they are not part of the canonical ranking by default because they often duplicate request payloads, system prompts, or state indexes.

| Source | Default Decision |
| --- | --- |
| `%USERPROFILE%\.codex\state_*.sqlite` | Supplement only. |
| `%USERPROFILE%\.codex\logs_*.sqlite` | Supplement only; high duplicate/request-log risk. |
| `%USERPROFILE%\.hermes\state.db` | Supplement only. |
| `%USERPROFILE%\.cursor\ai-tracking\ai-code-tracking.db` | Supplement only. |

## Corpus Sources

These can prove prior discussion or user intent, not actual invocation frequency.

| Root | Class | Default Decision |
| --- | --- | --- |
| `<conversation-export-root>` | corpus | Historical conversation corpus. |
| `<notes-or-memory-root>` | corpus | Personal notes and distilled memory. |
| `<work-documents-root>` | corpus | Work documents. |

## Noise Buckets

Mark these as discovered but excluded unless the user explicitly asks for source/reference frequency.

- Skill source directories: `.agents\skills`, `.codex\skills`, `.claude\skills`, plugin skill bundles.
- Dependency/cache directories: `node_modules`, `.venv`, `site-packages`, `.cache`, build caches.
- Generated artifacts: previous `skill-usage-*` outputs, graph/cache exports, HTML reports.
- Permission/system prompt repeats: allowlists, "Available skills" blocks, generated context dumps.
- Bulk path operations: `git add .agents/skills/...`, backup manifests, installer file lists.
- Project docs that mention skills as examples but are not session transcripts.

## Strict Evidence Examples

Count as strict only when paired with execution context:

- Explicit `skill_name`, `skillName`, or Skill tool invocation records.
- Reading/opening a specific `SKILL.md` because a task triggered it.
- Tool-call or command traces showing the agent inspected a skill body for the active task.

Do not count as strict:

- Plain path listings.
- System-prompt skill inventories.
- Skill source file contents.
- Markdown notes saying a skill exists.
- User asking "is there a skill for X" unless the agent actually loads/uses one.
