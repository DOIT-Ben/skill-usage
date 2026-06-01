#!/usr/bin/env python3
"""Deep local skill-usage scan.

This script is intentionally local-only and privacy-preserving: it reports skill
names and aggregate counts, not raw prompt/log content.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


WORKDIR = Path(os.environ.get("OUTPUT_DIR", Path.cwd())).resolve()
WORKDIR.mkdir(parents=True, exist_ok=True)
HOME = Path(os.environ.get("USERPROFILE", str(Path.home())))

def safe_suffix(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    value = value.strip(".-_")
    if not value:
        return ""
    if not value.startswith("-"):
        value = "-" + value
    return value[:80]


def int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


REPORT_SUFFIX = safe_suffix(os.environ.get("REPORT_SUFFIX", ""))
OUT_JSON = WORKDIR / f"skill-usage-deep-report{REPORT_SUFFIX}.json"
OUT_MD = WORKDIR / f"skill-usage-ranking-deep{REPORT_SUFFIX}.md"
OUT_CSV = WORKDIR / f"skill-usage-ranking-deep{REPORT_SUFFIX}.csv"
OUT_AUDIT = WORKDIR / f"skill-usage-source-audit{REPORT_SUFFIX}.md"
RG_HIT_FILE = WORKDIR / "skill-usage-content-hit-files.txt"
MAX_TEXT_BYTES = int_env("MAX_TEXT_BYTES", 250 * 1024 * 1024)

TEXT_EXTS = {
    ".jsonl",
    ".json",
    ".log",
    ".txt",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    "",
}

SKILL_BLACKLIST = {
    "",
    ".agents",
    ".codex",
    ".claude",
    ".hermes",
    ".openclaw",
    ".system",
    "README",
    "readme",
    "SKILL",
    "skill",
    "skills",
    "skill-name",
    "<skill-name>",
    "name",
    "true",
    "false",
    "null",
    "cache",
    "plugins",
    "bundled",
    "primary-runtime",
}

REAL_OP_RE = re.compile(
    r"\b(cat|head|tail|less|more|Read|Grep|Glob|Bash|open|read_file|readFile|readFileSync)\b"
    r"|Get-Content|Select-String|rg\s+|grep\s+|skills/read|Skill tool|tool_use",
    re.I,
)
METADATA_RE = re.compile(
    r"Available skills|### Available skills|Skill bodies live on disk|How to use skills|"
    r"MEMORY_SUMMARY|memory folder|memories/skills/<skill-name>|技能总览|外置技能索引",
    re.I,
)
EXPLICIT_SKILL_RE = re.compile(
    r"""
    ["'](?:skill|skillName|skill_name)["']\s*:\s*["']([A-Za-z0-9_.:-]+)["']
    """,
    re.X,
)


@dataclass
class SourceStats:
    files: int = 0
    bytes: int = 0
    rows: int = 0
    hits: int = 0
    strict_hits: int = 0
    errors: int = 0
    skipped: int = 0


@dataclass
class SkillStats:
    raw_refs: int = 0
    wide_keys: set[str] = field(default_factory=set)
    strict_keys: set[str] = field(default_factory=set)
    sessions: set[str] = field(default_factory=set)
    strict_sessions: set[str] = field(default_factory=set)
    sources: Counter = field(default_factory=Counter)
    strict_sources: Counter = field(default_factory=Counter)
    source_keys: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    strict_source_keys: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    first_seen: str = ""
    last_seen: str = ""


class Scanner:
    def __init__(self) -> None:
        self.skills: dict[str, SkillStats] = {}
        self.sources: dict[str, SourceStats] = defaultdict(SourceStats)
        self.files_seen: set[str] = set()
        self.skipped_files: list[dict[str, Any]] = []
        self.parse_errors = 0

    def record(
        self,
        skill: str,
        *,
        source: str,
        session: str,
        turn: str,
        ts: str = "",
        strict: bool = False,
    ) -> None:
        skill = clean_skill_name(skill)
        if not is_valid_skill_name(skill):
            return

        key = f"{session}::{turn}::{skill}"
        s = self.skills.setdefault(skill, SkillStats())
        s.raw_refs += 1
        s.wide_keys.add(key)
        s.sessions.add(session)
        s.sources[source] += 1
        s.source_keys[source].add(key)
        if strict:
            s.strict_keys.add(key)
            s.strict_sessions.add(session)
            s.strict_sources[source] += 1
            s.strict_source_keys[source].add(key)
        if ts:
            day = normalize_day(ts)
            if day:
                if not s.first_seen or day < s.first_seen:
                    s.first_seen = day
                if not s.last_seen or day > s.last_seen:
                    s.last_seen = day

        self.sources[source].hits += 1
        if strict:
            self.sources[source].strict_hits += 1

    def scan_text_file(self, path: Path, source: str) -> None:
        p = str(path)
        if p in self.files_seen:
            return
        self.files_seen.add(p)
        stat = self.sources[source]
        stat.files += 1
        try:
            size = path.stat().st_size
            stat.bytes += size
            if size > MAX_TEXT_BYTES:
                stat.skipped += 1
                self.skipped_files.append({"path": p, "reason": "too_large", "bytes": size})
                return
        except OSError as exc:
            stat.errors += 1
            self.skipped_files.append({"path": p, "reason": f"stat_error:{exc.__class__.__name__}"})
            return

        session = derive_session_id(path)
        current_turn = "init"
        line_no = 0
        try:
            if path.suffix.lower() == ".json" and size <= 80 * 1024 * 1024:
                raw = path.read_text(encoding="utf-8", errors="ignore")
                if not maybe_contains_skill(raw):
                    return
                rec = try_json(raw)
                stat.rows += 1
                if rec is not None:
                    sid = find_first_key(rec, ("session_id", "sessionId", "thread_id", "id")) or session
                    ts = str(find_first_key(rec, ("timestamp", "ts", "created_at", "updated_at", "started_at")) or "")
                    self.scan_object(
                        rec,
                        source=source,
                        session=f"{source}:{sid}",
                        turn="json-file",
                        ts=ts or date_from_path(path),
                    )
                else:
                    for line_no, line in enumerate(raw.splitlines(), 1):
                        if maybe_contains_skill(line):
                            self.scan_text(
                                line,
                                source=source,
                                session=f"{source}:{session}",
                                turn=str(line_no),
                                ts=date_from_path(path),
                                context="raw-json-line",
                            )
                return

            with path.open("r", encoding="utf-8", errors="ignore") as f:
                for line_no, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    if not maybe_contains_skill(line):
                        continue
                    stat.rows += 1
                    rec = None
                    if path.suffix.lower() in {".jsonl", ".json"}:
                        rec = try_json(line)
                    if rec is not None:
                        current_turn = update_turn(current_turn, rec, line_no)
                        sid = find_first_key(rec, ("session_id", "sessionId", "thread_id", "id")) or session
                        ts = str(find_first_key(rec, ("timestamp", "ts", "created_at", "updated_at")) or "")
                        self.scan_object(
                            rec,
                            source=source,
                            session=f"{source}:{sid}",
                            turn=current_turn or str(line_no),
                            ts=ts,
                        )
                    else:
                        self.scan_text(
                            line,
                            source=source,
                            session=f"{source}:{session}",
                            turn=str(line_no),
                            ts=date_from_path(path),
                            context="raw-line",
                        )
        except OSError as exc:
            stat.errors += 1
            self.skipped_files.append({"path": p, "reason": f"read_error:{exc.__class__.__name__}"})
            return
        except Exception:
            stat.errors += 1
            self.parse_errors += 1

    def scan_object(
        self,
        obj: Any,
        *,
        source: str,
        session: str,
        turn: str,
        ts: str = "",
        path_hint: str = "",
    ) -> None:
        # Explicit Claude/Codex/Hermes-style Skill tool invocation.
        if isinstance(obj, dict):
            tool_name = str(obj.get("name") or obj.get("tool_name") or obj.get("type") or "")
            if tool_name == "Skill":
                payload = obj.get("input") or obj.get("arguments") or obj.get("args") or obj
                skill = find_first_key(payload, ("skill", "skillName", "skill_name"))
                if isinstance(skill, str):
                    self.record(skill, source=source, session=session, turn=turn, ts=ts, strict=True)

            if obj.get("type") == "tool_use" and obj.get("name") == "Skill":
                payload = obj.get("input") or {}
                skill = find_first_key(payload, ("skill", "skillName", "skill_name"))
                if isinstance(skill, str):
                    self.record(skill, source=source, session=session, turn=turn, ts=ts, strict=True)

        for field_path, value in flatten_text(obj):
            context = f"{path_hint}.{field_path}" if path_hint else field_path
            self.scan_text(value, source=source, session=session, turn=turn, ts=ts, context=context)

    def scan_text(
        self,
        text: str,
        *,
        source: str,
        session: str,
        turn: str,
        ts: str = "",
        context: str = "",
    ) -> None:
        if not text:
            return
        if len(text) > 200_000:
            inherited_metadata = bool(METADATA_RE.search(text) or "system_prompt" in context or "skill_metadata" in context)
            child_context = f"{context}.skill_metadata" if inherited_metadata else context
            for chunk in skill_windows(text):
                self.scan_text(chunk, source=source, session=session, turn=turn, ts=ts, context=child_context)
            return
        is_metadata = bool(METADATA_RE.search(text) or "system_prompt" in context or "skill_metadata" in context)
        real_op = bool(REAL_OP_RE.search(text))

        for variant in text_variants(text):
            for skill, has_subfile, local_meta in extract_skill_paths(variant):
                strict = has_subfile and real_op and not is_metadata and not local_meta
                self.record(skill, source=source, session=session, turn=turn, ts=ts, strict=strict)

            # Explicit skill names only count when the surrounding text is clearly
            # about a Skill tool / skills/read invocation. This avoids counting
            # ordinary words like browser, pdf, or documents.
            if re.search(r"\b(Skill|skills/read|skills\.read|skill_name|skillName)\b", variant, re.I):
                for m in EXPLICIT_SKILL_RE.finditer(variant):
                    skill = m.group(1)
                    if not skill:
                        continue
                    strict = bool(real_op or "Skill" in variant or "skills/read" in variant)
                    self.record(skill, source=source, session=session, turn=turn, ts=ts, strict=strict and not is_metadata)

    def scan_sqlite(self, db_path: Path, source: str, queries: list[tuple[str, str, list[str]]]) -> None:
        p = str(db_path)
        if p in self.files_seen:
            return
        self.files_seen.add(p)
        stat = self.sources[source]
        stat.files += 1
        try:
            stat.bytes += db_path.stat().st_size
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        except Exception as exc:
            stat.errors += 1
            self.skipped_files.append({"path": p, "reason": f"sqlite_open:{exc.__class__.__name__}"})
            return
        try:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            for table, where, cols in queries:
                col_expr = ", ".join([quote_ident(c) for c in cols])
                sql = f"select rowid as __rowid, {col_expr} from {quote_ident(table)}"
                if where:
                    sql += f" where {where}"
                try:
                    for row in cur.execute(sql):
                        stat.rows += 1
                        session = f"{source}:{table}:{row['__rowid']}"
                        texts = []
                        for c in cols:
                            val = row[c]
                            if val is not None:
                                texts.append(str(val))
                        joined = "\n".join(texts)
                        self.scan_text(joined, source=source, session=session, turn="sqlite-row", context=f"sqlite:{table}")
                except sqlite3.Error:
                    stat.errors += 1
        finally:
            con.close()

    def scan_sqlite_generic(self, db_path: Path, source: str) -> None:
        p = str(db_path)
        if p in self.files_seen:
            return
        self.files_seen.add(p)
        stat = self.sources[source]
        stat.files += 1
        try:
            stat.bytes += db_path.stat().st_size
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        except Exception as exc:
            stat.errors += 1
            self.skipped_files.append({"path": p, "reason": f"sqlite_open:{exc.__class__.__name__}"})
            return
        try:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            tables = []
            for row in cur.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'"):
                tables.append(str(row["name"]))
            for table in tables[:200]:
                try:
                    info = list(cur.execute(f"pragma table_info({quote_ident(table)})"))
                except sqlite3.Error:
                    stat.errors += 1
                    continue
                cols = [
                    str(r["name"])
                    for r in info
                    if re.search(r"(char|clob|text|json|varchar|nvarchar)", str(r["type"]), re.I)
                    or re.search(r"(content|message|prompt|response|body|text|json|tool|skill|history|session|title|path|name)", str(r["name"]), re.I)
                ]
                if not cols:
                    continue
                where = " or ".join(
                    [
                        f"lower(coalesce({quote_ident(c)},'')) like '%skill%'"
                        f" or coalesce({quote_ident(c)},'') like '%SKILL.md%'"
                        f" or coalesce({quote_ident(c)},'') like '%技能%'"
                        for c in cols
                    ]
                )
                col_expr = ", ".join(quote_ident(c) for c in cols)
                sql = f"select rowid as __rowid, {col_expr} from {quote_ident(table)} where {where} limit 50000"
                try:
                    for row in cur.execute(sql):
                        stat.rows += 1
                        texts = []
                        for c in cols:
                            val = row[c]
                            if val is not None:
                                texts.append(str(val))
                        joined = "\n".join(texts)
                        self.scan_text(
                            joined,
                            source=source,
                            session=f"{source}:{table}:{row['__rowid']}",
                            turn="sqlite-row",
                            context=f"sqlite-generic:{table}",
                        )
                except sqlite3.Error:
                    stat.errors += 1
        finally:
            con.close()

    def make_report(self) -> dict[str, Any]:
        rows = []
        for skill, s in self.skills.items():
            wide = len(s.wide_keys)
            strict = len(s.strict_keys)
            source_mentions = Counter({k: len(v) for k, v in s.source_keys.items()})
            strict_source_calls = Counter({k: len(v) for k, v in s.strict_source_keys.items()})
            rows.append(
                {
                    "skill": skill,
                    "strictCalls": strict,
                    "wideMentions": wide,
                    "rawRefs": s.raw_refs,
                    "strictSessions": len(s.strict_sessions),
                    "sessions": len(s.sessions),
                    "realRatio": round(strict / wide * 100, 1) if wide else 0,
                    "sources": dict(source_mentions.most_common()),
                    "strictSources": dict(strict_source_calls.most_common()),
                    "rawSources": dict(s.sources.most_common()),
                    "strictRawSources": dict(s.strict_sources.most_common()),
                    "firstSeen": s.first_seen,
                    "lastSeen": s.last_seen,
                }
            )
        rows.sort(key=lambda r: (-r["strictCalls"], -r["wideMentions"], r["skill"].lower()))

        return {
            "generatedAt": now_iso(),
            "summary": {
                "uniqueSkills": len(rows),
                "strictCalls": sum(r["strictCalls"] for r in rows),
                "wideMentions": sum(r["wideMentions"] for r in rows),
                "rawRefs": sum(r["rawRefs"] for r in rows),
                "filesScanned": len(self.files_seen),
                "parseErrors": self.parse_errors,
                "skippedFiles": len(self.skipped_files),
            },
            "sources": {
                k: {
                    "files": v.files,
                    "bytes": v.bytes,
                    "rows": v.rows,
                    "hits": v.hits,
                    "strictHits": v.strict_hits,
                    "errors": v.errors,
                    "skipped": v.skipped,
                }
                for k, v in sorted(self.sources.items())
            },
            "ranking": rows,
            "skippedFiles": self.skipped_files[:500],
        }


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def clean_skill_name(name: str) -> str:
    name = name.strip().strip("\"'`.,;:()[]{}<>")
    name = name.replace("%20", " ")
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name


def is_valid_skill_name(name: str) -> bool:
    if not name or name in SKILL_BLACKLIST:
        return False
    if len(name) > 80:
        return False
    if name.startswith(".") and name != ".system":
        return False
    if re.fullmatch(r"\d+(?:\.\d+){0,4}", name):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_.:\-\u4e00-\u9fff]+", name):
        return False
    if re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?", name):
        return False
    if re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+){1,}", name.lower()) and not re.search(r"-\d+\.\d+", name):
        return False
    if re.search(r"\.(txt|json|yaml|yml|js|py|ts|tsx|jsx|html|css)$", name, re.I):
        return False
    if name.upper() == name and re.search(r"[A-Z]", name) and len(name) > 3:
        return False
    # Filter common truncated path fragments produced by prose examples.
    if name in {"path", "file", "json", "yaml", "txt", "md", "py", "js"}:
        return False
    return True


def normalize_day(ts: str) -> str:
    if not ts:
        return ""
    ts = str(ts)
    m = re.search(r"(20\d{2})[-_/]?(0[1-9]|1[0-2])[-_/]?([0-3]\d)", ts)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if ts.isdigit() and len(ts) >= 10:
        try:
            import datetime as dt

            v = int(ts[:10])
            return dt.datetime.fromtimestamp(v).strftime("%Y-%m-%d")
        except Exception:
            return ""
    return ""


def date_from_path(path: Path) -> str:
    return normalize_day(str(path))


def now_iso() -> str:
    import datetime as dt

    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def derive_session_id(path: Path) -> str:
    stem = path.name
    stem = re.sub(r"\.(jsonl|json|log|txt|md)$", "", stem, flags=re.I)
    return stem


def try_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def find_first_key(obj: Any, keys: Iterable[str]) -> Any | None:
    keyset = set(keys)
    if isinstance(obj, dict):
        for k in keyset:
            if k in obj:
                return obj[k]
        for v in obj.values():
            got = find_first_key(v, keyset)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for item in obj:
            got = find_first_key(item, keyset)
            if got is not None:
                return got
    return None


def update_turn(current: str, rec: Any, line_no: int) -> str:
    if not isinstance(rec, dict):
        return current
    payload = rec.get("payload")
    if isinstance(payload, dict) and payload.get("turn_id"):
        return str(payload["turn_id"])
    if rec.get("promptId"):
        return str(rec["promptId"])
    if rec.get("role") == "user" or rec.get("type") == "user":
        return f"user-{line_no}"
    return current


def flatten_text(obj: Any, prefix: str = "", depth: int = 0) -> Iterable[tuple[str, str]]:
    if depth > 8:
        return
    if isinstance(obj, str):
        yield prefix or "text", obj
        stripped = obj.strip()
        if len(stripped) > 1 and stripped[0] in "[{" and stripped[-1] in "]}":
            nested = try_json(stripped)
            if nested is not None and nested is not obj:
                yield from flatten_text(nested, prefix + ".json", depth + 1)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{prefix}.{k}" if prefix else str(k)
            yield from flatten_text(v, child, depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:200]):
            yield from flatten_text(v, f"{prefix}[{i}]", depth + 1)
    elif obj is not None and isinstance(obj, (int, float)):
        return


def text_variants(text: str) -> list[str]:
    variants = []
    seen = set()

    def add(s: str) -> None:
        if s and s not in seen:
            seen.add(s)
            variants.append(s)

    add(text)
    cur = text
    for _ in range(4):
        nxt = cur.replace("\\/", "/")
        nxt = re.sub(r"\\\\+", lambda m: "\\" * max(1, len(m.group(0)) // 2), nxt)
        nxt = decode_unicode_escapes(nxt)
        add(nxt)
        if nxt == cur:
            break
        cur = nxt
    return variants


def decode_unicode_escapes(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        try:
            return chr(int(m.group(1), 16))
        except Exception:
            return m.group(0)

    return re.sub(r"\\u([0-9a-fA-F]{4})", repl, text)


def maybe_contains_skill(text: str) -> bool:
    low = text.lower()
    return "skill" in low or "skills" in low or "技能" in text


def skill_windows(text: str, radius: int = 1200, limit: int = 120) -> Iterable[str]:
    low = text.lower()
    spans = []
    for needle in ("skill", "skills", "技能"):
        start = 0
        while len(spans) < limit:
            idx = low.find(needle.lower(), start)
            if idx < 0:
                break
            spans.append((max(0, idx - radius), min(len(text), idx + radius)))
            start = idx + len(needle)
    if not spans:
        return
    spans.sort()
    merged = []
    for a, b in spans:
        if not merged or a > merged[-1][1]:
            merged.append([a, b])
        else:
            merged[-1][1] = max(merged[-1][1], b)
    for a, b in merged[:limit]:
        yield text[a:b]


def extract_skill_paths(text: str) -> Iterable[tuple[str, bool, bool]]:
    norm = text.replace("\\", "/")
    norm = norm.replace("\\\\", "/")
    low = norm.lower()
    starts = [m.start() for m in re.finditer(r"(?:^|/)skills/", low)]
    for start in starts:
        prefix = low[max(0, start - 260) : start]
        local_meta = "/memories/" in prefix or "memory folder" in low[max(0, start - 120) : start + 120]
        trusted_prefix = any(
            marker in prefix
            for marker in (
                "/.agents",
                "/.codex",
                "/.claude",
                "/.hermes",
                "/.openclaw",
                "/.opencode",
                "/.clawdbot",
                "openai-bundled",
                "openai-primary-runtime",
                "plugins/cache",
            )
        )
        if not trusted_prefix and not re.search(r"\b(read|skill|skills/read|SKILL\.md)\b", norm[max(0, start - 80) : start + 120], re.I):
            continue

        after = norm[start:]
        if after.startswith("/"):
            after = after[1:]
        if not after.lower().startswith("skills/"):
            continue
        rest = after[len("skills/") :]
        rest = re.split(r"[\s\"'`<>{}\[\](),;|]+", rest, 1)[0]
        parts = [p for p in rest.split("/") if p]
        if not parts:
            continue
        skill = parts[0]
        if skill == ".system" and len(parts) > 1:
            skill = parts[1]
            parts = parts[1:]
        has_subfile = len(parts) > 1 and (
            parts[1].lower() in {"skill.md", "reference.md", "readme.md"}
            or bool(re.search(r"\.(md|json|js|py|txt|yaml|yml|sh|ps1)$", parts[-1], re.I))
        )
        yield skill, has_subfile, local_meta


def discover_text_sources() -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []

    def add_glob(root: Path, pattern: str, source: str) -> None:
        if not root.exists():
            return
        try:
            for p in root.glob(pattern):
                if p.is_file() and p.suffix.lower() in TEXT_EXTS and not is_duplicate_snapshot_path(p):
                    sources.append((p, source))
        except OSError:
            return

    add_glob(HOME / ".codex" / "sessions", "**/*.jsonl", "codex-sessions")
    add_glob(HOME / ".codex" / "archived_sessions", "**/*.jsonl", "codex-archived")
    for p in [HOME / ".codex" / "history.jsonl", HOME / ".codex" / "session_index.jsonl"]:
        if p.exists():
            sources.append((p, "codex-index"))
    add_glob(HOME / ".codex" / "memories" / "rollout_summaries", "*.md", "codex-rollout-summaries")

    add_glob(HOME / ".claude" / "projects", "**/*.jsonl", "claude-projects")
    if (HOME / ".claude" / "history.jsonl").exists():
        sources.append((HOME / ".claude" / "history.jsonl", "claude-history"))

    add_glob(HOME / ".hermes" / "sessions", "**/*.jsonl", "hermes-session-jsonl")
    add_glob(HOME / ".hermes" / "sessions", "**/*.json", "hermes-session-json")
    add_glob(HOME / ".hermes" / "logs", "**/*.log", "hermes-logs")
    add_glob(HOME / ".hermes" / "logs", "**/*.json", "hermes-logs")
    if (HOME / ".hermes" / ".hermes_history").exists():
        sources.append((HOME / ".hermes" / ".hermes_history", "hermes-history"))

    for root_name, source in [
        (".openclaw", "openclaw-sessions"),
        (".openclaw-autoclaw", "openclaw-autoclaw-sessions"),
    ]:
        root = HOME / root_name
        add_glob(root / "agents", "**/sessions/*.jsonl", source)
        add_glob(root / "agents", "**/sessions/*.json", source)
        add_glob(root / "autoclaw" / "chat-history", "*.json", source)

    add_glob(HOME / ".cursor" / "projects", "**/agent-transcripts/**/*.jsonl", "cursor-agent-transcripts")

    add_glob(HOME / ".mini-agent" / "log", "*.log", "mini-agent-logs")
    if (HOME / ".mini-agent" / ".history").exists():
        sources.append((HOME / ".mini-agent" / ".history", "mini-agent-history"))

    extra_paths_file = os.environ.get("EXTRA_PATHS_FILE", "").strip()
    if extra_paths_file:
        sources.extend(load_extra_text_sources(Path(extra_paths_file)))

    # Preserve order while deduplicating.
    out = []
    seen = set()
    for p, source in sources:
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((p, source))
    return out


def load_extra_text_sources(path_file: Path) -> list[tuple[Path, str]]:
    """Load full-disk discovered paths without passing them back through a shell."""
    if not path_file.exists():
        return []
    sources: list[tuple[Path, str]] = []
    try:
        lines = path_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    for raw in lines:
        raw = raw.strip().lstrip("\ufeff")
        if not raw:
            continue
        p = Path(raw)
        if p.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if not p.is_file():
                continue
        except OSError:
            continue
        if is_duplicate_snapshot_path(p):
            continue
        sources.append((p, classify_extra_source(p)))
    return sources


def load_extra_sqlite_sources(path_file: Path) -> list[tuple[Path, str]]:
    if not path_file.exists():
        return []
    sources: list[tuple[Path, str]] = []
    try:
        lines = path_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    for raw in lines:
        raw = raw.strip().lstrip("\ufeff")
        if not raw:
            continue
        p = Path(raw)
        if p.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            continue
        try:
            if not p.is_file():
                continue
        except OSError:
            continue
        if is_duplicate_snapshot_path(p):
            continue
        sources.append((p, classify_extra_source(p) + "-db"))
    return sources


def classify_extra_source(path: Path) -> str:
    lp = str(path).lower()
    if "\\.codex\\sessions\\" in lp:
        return "codex-sessions"
    if "\\.codex\\archived_sessions\\" in lp:
        return "codex-archived"
    if "\\.codex\\" in lp:
        return "full-disk-codex"
    if "\\.claude\\projects\\" in lp:
        return "claude-projects"
    if "\\.claude\\" in lp:
        return "full-disk-claude"
    if "\\.hermes\\sessions\\" in lp:
        if path.suffix.lower() == ".jsonl":
            return "hermes-session-jsonl"
        return "hermes-session-json"
    if "\\.hermes\\" in lp:
        return "full-disk-hermes"
    if "\\.openclaw" in lp:
        return "full-disk-openclaw"
    if "\\.cursor\\" in lp:
        return "full-disk-cursor"
    if "\\.continue\\" in lp:
        return "full-disk-continue"
    if "\\opencode\\" in lp:
        return "full-disk-opencode"
    if any(marker in lp for marker in ("\\session", "\\sessions", "\\chat", "\\conversation", "\\transcript", "\\history", "\\messages")):
        return "full-disk-sessionish"
    if any(marker in lp for marker in ("\\agents\\", "\\agent\\", "\\logs\\", "\\log\\")):
        return "full-disk-agent-log"
    return "full-disk-corpus"


def is_duplicate_snapshot_path(path: Path) -> bool:
    """Skip known backup/snapshot copies so old duplicated sessions do not inflate usage."""
    lp = str(path).lower()
    duplicate_markers = (
        "\\backups_state\\",
        "\\session-repair-backup-",
        "\\promote-workspace-backup-",
        "\\skill-sync-backups\\",
        "\\backups\\",
        ".bak",
        ".deleted.",
        ".reset.",
        ".checkpoint.",
        ".trajectory.",
        "session-meta-backup.json",
    )
    return any(marker in lp for marker in duplicate_markers)


def sqlite_sources() -> list[tuple[Path, str, list[tuple[str, str, list[str]]]]]:
    like_skill = (
        "lower(coalesce({col},'')) like '%skill%' "
        "or coalesce({col},'') like '%SKILL.md%' "
        "or lower(coalesce({col},'')) like '%skills%'"
    )

    return [
        (
            HOME / ".codex" / "state_5.sqlite",
            "codex-state-db",
            [
                (
                    "threads",
                    " or ".join(like_skill.format(col=quote_ident(c)) for c in ["rollout_path", "cwd", "title", "first_user_message", "preview", "agent_path"]),
                    ["id", "rollout_path", "cwd", "title", "first_user_message", "preview", "agent_path"],
                ),
                (
                    "thread_dynamic_tools",
                    " or ".join(like_skill.format(col=quote_ident(c)) for c in ["name", "description", "input_schema", "namespace"]),
                    ["name", "description", "input_schema", "namespace"],
                ),
            ],
        ),
        (
            HOME / ".codex" / "logs_2.sqlite",
            "codex-logs-db",
            [
                (
                    "logs",
                    " or ".join(
                        [
                            "coalesce(target,'') like '%skills%'",
                            "coalesce(module_path,'') like '%skills%'",
                            "coalesce(file,'') like '%skills%'",
                            "coalesce(feedback_log_body,'') like '%SKILL.md%'",
                            "coalesce(feedback_log_body,'') like '%skills/%'",
                            "coalesce(feedback_log_body,'') like '%.agents%skills%'",
                            "coalesce(feedback_log_body,'') like '%.codex%skills%'",
                            "coalesce(feedback_log_body,'') like '%.claude%skills%'",
                            "coalesce(feedback_log_body,'') like '%.hermes%skills%'",
                            "coalesce(feedback_log_body,'') like '%skill-usage%'",
                        ]
                    ),
                    ["ts", "target", "feedback_log_body", "module_path", "file"],
                )
            ],
        ),
        (
            HOME / ".hermes" / "state.db",
            "hermes-state-db",
            [
                (
                    "messages",
                    " or ".join(like_skill.format(col=quote_ident(c)) for c in ["content", "tool_calls", "reasoning", "reasoning_details", "reasoning_content", "codex_message_items"]),
                    ["session_id", "role", "content", "tool_calls", "tool_name", "reasoning", "reasoning_details", "reasoning_content", "codex_message_items", "timestamp"],
                ),
                (
                    "sessions",
                    like_skill.format(col=quote_ident("system_prompt")),
                    ["id", "source", "model", "system_prompt", "started_at", "ended_at"],
                ),
            ],
        ),
        (
            HOME / ".cursor" / "ai-tracking" / "ai-code-tracking.db",
            "cursor-ai-tracking-db",
            [
                (
                    "ai_code_hashes",
                    " or ".join(like_skill.format(col=quote_ident(c)) for c in ["source", "fileName", "requestId", "conversationId", "model"]),
                    ["source", "fileName", "requestId", "conversationId", "model", "timestamp"],
                ),
                (
                    "scored_commits",
                    like_skill.format(col=quote_ident("commitMessage")),
                    ["commitHash", "branchName", "commitMessage", "commitDate"],
                ),
            ],
        ),
    ]


def tier(strict: int) -> str:
    if strict >= 100:
        return "★★★ 主力"
    if strict >= 20:
        return "★★ 常用"
    if strict >= 5:
        return "★ 偶用"
    if strict >= 1:
        return "· 尝试"
    return "○ 仅提及"


def write_outputs(report: dict[str, Any]) -> None:
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = report["ranking"]
    tier_counts = Counter(tier(r["strictCalls"]) for r in rows)

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "rank",
                "tier",
                "skill",
                "strictCalls",
                "wideMentions",
                "rawRefs",
                "strictSessions",
                "sessions",
                "realRatio",
                "firstSeen",
                "lastSeen",
                "strictSources",
                "sources",
            ],
        )
        writer.writeheader()
        for i, r in enumerate(rows, 1):
            writer.writerow(
                {
                    "rank": i,
                    "tier": tier(r["strictCalls"]),
                    "skill": r["skill"],
                    "strictCalls": r["strictCalls"],
                    "wideMentions": r["wideMentions"],
                    "rawRefs": r["rawRefs"],
                    "strictSessions": r["strictSessions"],
                    "sessions": r["sessions"],
                    "realRatio": r["realRatio"],
                    "firstSeen": r["firstSeen"],
                    "lastSeen": r["lastSeen"],
                    "strictSources": json.dumps(r["strictSources"], ensure_ascii=False, sort_keys=True),
                    "sources": json.dumps(r["sources"], ensure_ascii=False, sort_keys=True),
                }
            )

    md = []
    md.append("# Deep Skill Usage Ranking")
    md.append("")
    md.append(f"Generated: `{report['generatedAt']}`")
    s = report["summary"]
    md.append(
        f"Scope: {s['uniqueSkills']} skills; strictCalls={s['strictCalls']}; "
        f"wideMentions={s['wideMentions']}; rawRefs={s['rawRefs']}; filesScanned={s['filesScanned']}; skippedFiles={s['skippedFiles']}"
    )
    md.append("")
    md.append("`strictCalls` = strong evidence of a real skill read/invocation. `wideMentions` = path/name traces, including noisy system-prompt/listing mentions.")
    md.append("")
    md.append("## Tier Summary")
    md.append("")
    for label in ["★★★ 主力", "★★ 常用", "★ 偶用", "· 尝试", "○ 仅提及"]:
        md.append(f"- {label}: {tier_counts[label]}")
    md.append("")
    md.append("## Full Ranking")
    md.append("")
    md.append("| Rank | Tier | Skill | Strict Calls | Wide Mentions | Strict Sessions | Sessions | Real Ratio | First Seen | Last Seen | Strict Sources | Wide Sources |")
    md.append("| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |")
    for i, r in enumerate(rows, 1):
        strict_sources = ",".join(f"{k}:{v}" for k, v in list(r["strictSources"].items())[:6])
        sources = ",".join(f"{k}:{v}" for k, v in list(r["sources"].items())[:6])
        md.append(
            f"| {i} | {tier(r['strictCalls'])} | {escape_md(r['skill'])} | {r['strictCalls']} | {r['wideMentions']} | "
            f"{r['strictSessions']} | {r['sessions']} | {r['realRatio']}% | {r['firstSeen']} | {r['lastSeen']} | "
            f"{escape_md(strict_sources)} | {escape_md(sources)} |"
        )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    audit = []
    audit.append("# Skill Usage Source Audit")
    audit.append("")
    audit.append(f"Generated: `{report['generatedAt']}`")
    audit.append("")
    audit.append("## Sources")
    audit.append("")
    audit.append("| Source | Files | Rows | Hits | Strict Hits | Bytes | Errors | Skipped |")
    audit.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for source, st in report["sources"].items():
        audit.append(
            f"| {source} | {st['files']} | {st['rows']} | {st['hits']} | {st['strictHits']} | {st['bytes']} | {st['errors']} | {st['skipped']} |"
        )
    audit.append("")
    audit.append("## Skipped Files")
    audit.append("")
    if report["skippedFiles"]:
        audit.append("| Path | Reason | Bytes |")
        audit.append("| --- | --- | ---: |")
        for item in report["skippedFiles"][:200]:
            audit.append(f"| {escape_md(item.get('path', ''))} | {escape_md(item.get('reason', ''))} | {item.get('bytes', '')} |")
    else:
        audit.append("No files were skipped by the deep scanner.")
    OUT_AUDIT.write_text("\n".join(audit) + "\n", encoding="utf-8")


def escape_md(text: str) -> str:
    return str(text).replace("|", "\\|")


def main() -> None:
    scanner = Scanner()

    text_sources = discover_text_sources()
    extra_paths_file = os.environ.get("EXTRA_PATHS_FILE", "").strip()
    only_sources = {s.strip() for s in os.environ.get("ONLY_SOURCES", "").split(",") if s.strip()}
    only_sqlite = os.environ.get("ONLY_SQLITE", "") == "1"
    only_extra = os.environ.get("ONLY_EXTRA", "") == "1"
    if only_sources:
        text_sources = [(p, s) for p, s in text_sources if s in only_sources]
    if only_extra:
        text_sources = load_extra_text_sources(Path(extra_paths_file)) if extra_paths_file else []
    if only_sqlite:
        text_sources = []
    print(f"text sources: {len(text_sources)}")
    for idx, (path, source) in enumerate(text_sources, 1):
        if idx % 500 == 0:
            print(f"  scanned text files: {idx}/{len(text_sources)}")
        scanner.scan_text_file(path, source)

    include_sqlite = os.environ.get("INCLUDE_SQLITE", "") == "1" or only_sqlite
    skip_sqlite = os.environ.get("SKIP_SQLITE", "") == "1" or not include_sqlite
    sqlite_items = sqlite_sources()
    if only_extra:
        sqlite_items = []
    for db_path, source, queries in sqlite_items:
        if skip_sqlite:
            continue
        if only_sources and source not in only_sources:
            continue
        if db_path.exists():
            print(f"sqlite source: {source} {db_path}")
            scanner.scan_sqlite(db_path, source, queries)

    if not skip_sqlite and extra_paths_file:
        sqlite_extra = load_extra_sqlite_sources(Path(extra_paths_file))
        if only_sources:
            sqlite_extra = [(p, s) for p, s in sqlite_extra if s in only_sources]
        print(f"extra sqlite sources: {len(sqlite_extra)}")
        for idx, (db_path, source) in enumerate(sqlite_extra, 1):
            if idx % 50 == 0:
                print(f"  scanned sqlite files: {idx}/{len(sqlite_extra)}")
            scanner.scan_sqlite_generic(db_path, source)

    report = scanner.make_report()
    write_outputs(report)
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_AUDIT}")
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
