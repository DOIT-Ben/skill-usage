#!/usr/bin/env node
// skill-usage analyzer - cross-platform skill usage statistics
// Scans Codex, Claude Code, and Hermes conversation logs
// Distinguishes real usage from metadata noise

const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");

// Cross-platform home detection
function getDefaultHome(name) {
  const envVar = `${name.toUpperCase()}_HOME`;
  if (process.env[envVar]) return process.env[envVar];
  return path.join(os.homedir(), `.${name.toLowerCase()}`);
}

const SOURCES = [
  { name: "codex",  root: path.join(getDefaultHome("codex"), "sessions"),   parser: "codex" },
  { name: "claude", root: path.join(getDefaultHome("claude"), "projects"),  parser: "claude" },
  { name: "hermes", root: getDefaultHome("hermes"),                         parser: "hermes" },
];

// Regex patterns for skill paths (handles all escaping levels)
const SEP = "[\\\\/]+";
const SKILL_NAME = "([一-龥a-zA-Z0-9_.-]+)";
const HOSTS = "(?:\\.agents|\\.codex|\\.Codex|\\.claude|\\.hermes|\\.openclaw)";

const SKILL_PATTERNS = [
  new RegExp(SEP + HOSTS + SEP + "skills" + SEP + "(?:\\.system" + SEP + ")?" + SKILL_NAME + "(" + SEP + "[一-龥a-zA-Z0-9_.-]+(?:\\.md|\\.json|\\.js|\\.py|\\.sh|\\.txt|\\.yaml|\\.yml)?)?", "gi"),
  new RegExp(SEP + "\\.codex" + SEP + "plugins" + SEP + "cache" + SEP + "[^\\\\/\"'\\s]+" + SEP + "[^\\\\/\"'\\s]+" + SEP + "(?:[^\\\\/\"'\\s]+" + SEP + ")?skills" + SEP + SKILL_NAME + "(" + SEP + "[一-龥a-zA-Z0-9_.-]+(?:\\.md|\\.json|\\.js|\\.py)?)?", "gi"),
  new RegExp(SEP + "openai-(?:bundled|bundled-dev|primary-runtime|bundled-runtime)" + SEP + "[^\\\\/\"'\\s]+" + SEP + "[^\\\\/\"'\\s]+" + SEP + "skills" + SEP + SKILL_NAME + "(" + SEP + "[一-龥a-zA-Z0-9_.-]+(?:\\.md|\\.json)?)?", "gi"),
];

const SKILL_BLACKLIST = new Set([
  "skills","SKILL","skill","README","readme",".system",".agents",".codex",".claude",".hermes",
  "bundled","bundled-dev","primary-runtime","cache","plugins","name","true","false","null",
]);

const REAL_OP_SIGNALS = [
  /\bcat\b/, /\bhead\b/, /\btail\b/, /\bless\b/, /\bmore\b/,
  /Get-Content/i, /Get-ChildItem/i, /Test-Path/i,
  /\bread_file\b/, /\bRead\b/, /\bGrep\b/, /\bGlob\b/,
  /\bopen\b/, /readFile/, /readFileSync/,
];

function walkJsonl(dir, out = []) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walkJsonl(p, out);
    else if (e.isFile() && p.toLowerCase().endsWith(".jsonl")) out.push(p);
  }
  return out;
}

function extractSkillsWithMeta(text) {
  if (!text) return [];
  const result = [];
  const seen = new Set();
  for (const re of SKILL_PATTERNS) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(text))) {
      let name = m[1].replace(/\.md$/i, "");
      if (!name || SKILL_BLACKLIST.has(name)) continue;
      if (/^\d+(?:\.\d+){0,3}$/.test(name)) continue;
      const hasSubfile = !!(m[2] && m[2].length > 1);
      const key = name + "::" + (hasSubfile ? "1" : "0");
      if (seen.has(key)) continue;
      seen.add(key);
      result.push({ skill: name, hasSubfile });
    }
  }
  return result;
}

function hasRealOp(text) {
  if (!text) return false;
  for (const re of REAL_OP_SIGNALS) if (re.test(text)) return true;
  return false;
}

function parseCodex(records, sessionId, stats) {
  let turn = "init", model = "unknown";
  for (const rec of records) {
    if (rec?.type === "event_msg" && rec.payload?.type === "task_started" && rec.payload?.turn_id) {
      turn = rec.payload.turn_id;
    }
    if (rec?.type === "turn_context" && rec.payload?.model) model = rec.payload.model;
    if (rec?.type === "response_item" && rec.payload?.type === "function_call") {
      stats.fnCalls++;
      const args = rec.payload.arguments || "";
      const real = hasRealOp(args);
      for (const { skill, hasSubfile } of extractSkillsWithMeta(args)) {
        record(stats, sessionId, turn, skill, rec.timestamp, model, "codex", hasSubfile || real);
      }
    }
    if (rec?.type === "response_item" && rec.payload?.type === "function_call_output") {
      const o = rec.payload.output;
      const text = typeof o === "string" ? o : JSON.stringify(o || "");
      for (const { skill, hasSubfile } of extractSkillsWithMeta(text)) {
        record(stats, sessionId, turn, skill, rec.timestamp, model, "codex", hasSubfile);
      }
    }
  }
}

function parseClaude(records, sessionId, stats) {
  let turn = "init", model = "unknown";
  for (const rec of records) {
    if (rec?.promptId) turn = rec.promptId;
    if (rec?.message?.model) model = rec.message.model;
    if (rec?.type === "assistant" && Array.isArray(rec?.message?.content)) {
      for (const block of rec.message.content) {
        if (block?.type === "tool_use") {
          stats.fnCalls++;
          const text = JSON.stringify(block.input || "");
          const real = hasRealOp(text) || ["Read","Bash","Grep","Glob"].includes(block.name);
          for (const { skill, hasSubfile } of extractSkillsWithMeta(text)) {
            record(stats, sessionId, turn, skill, rec.timestamp, model, "claude", hasSubfile || real);
          }
          if (block.name === "Skill" && block.input?.skill) {
            record(stats, sessionId, turn, block.input.skill, rec.timestamp, model, "claude-skilltool", true);
          }
        }
      }
    }
    if (rec?.type === "user" && Array.isArray(rec?.message?.content)) {
      for (const block of rec.message.content) {
        if (block?.type === "tool_result") {
          const x = block.content;
          const text = typeof x === "string" ? x : JSON.stringify(x || "");
          for (const { skill, hasSubfile } of extractSkillsWithMeta(text)) {
            record(stats, sessionId, turn, skill, rec.timestamp, model, "claude", hasSubfile);
          }
        }
      }
    }
  }
}

function parseHermes(records, sessionId, stats) {
  let turn = "init", model = "unknown";
  for (const rec of records) {
    if (rec?.role === "session_meta" && rec?.model) model = rec.model;
    if (rec?.role === "user") turn = `turn-${stats._turnCounter++}`;
    if (rec?.role === "assistant" && Array.isArray(rec.tool_calls)) {
      for (const tc of rec.tool_calls) {
        stats.fnCalls++;
        const args = tc?.function?.arguments || "";
        const real = hasRealOp(args);
        for (const { skill, hasSubfile } of extractSkillsWithMeta(args)) {
          record(stats, sessionId, turn, skill, rec.timestamp, model, "hermes", hasSubfile || real);
        }
      }
    }
    if (rec?.role === "tool" && rec?.content) {
      const text = typeof rec.content === "string" ? rec.content : JSON.stringify(rec.content);
      for (const { skill, hasSubfile } of extractSkillsWithMeta(text)) {
        record(stats, sessionId, turn, skill, rec.timestamp, model, "hermes", hasSubfile);
      }
    }
  }
}

function record(stats, sessionId, turn, skill, ts, model, source, isReal) {
  const turnKey = `${source}::${sessionId}::${turn}::${skill}`;
  const cur = stats.callsBySkill.get(skill) || {
    rawRefs: 0, turnHits: new Set(), realHits: new Set(),
    sessions: new Set(), realSessions: new Set(),
    models: new Map(), sources: new Map(),
    firstSeen: ts || "9999", lastSeen: ts || "",
  };
  cur.rawRefs++;
  cur.turnHits.add(turnKey);
  cur.sessions.add(`${source}::${sessionId}`);
  if (isReal) {
    cur.realHits.add(turnKey);
    cur.realSessions.add(`${source}::${sessionId}`);
  }
  cur.models.set(model, (cur.models.get(model) || 0) + 1);
  cur.sources.set(source, (cur.sources.get(source) || 0) + 1);
  if (ts && ts < cur.firstSeen) cur.firstSeen = ts;
  if (ts && ts > cur.lastSeen) cur.lastSeen = ts;
  stats.callsBySkill.set(skill, cur);
  stats.globalTurnHits.add(turnKey);
  if (isReal) stats.globalRealHits.add(turnKey);
}

// Main
const stats = {
  callsBySkill: new Map(),
  globalTurnHits: new Set(),
  globalRealHits: new Set(),
  fnCalls: 0, totalLines: 0, parseErrors: 0,
  filesByName: {}, _turnCounter: 0,
};

console.log("Scanning conversation logs...\n");

for (const src of SOURCES) {
  const files = walkJsonl(src.root);
  stats.filesByName[src.name] = files.length;
  if (files.length === 0) {
    console.log(`[${src.name}] No logs found at ${src.root}`);
    continue;
  }
  console.log(`[${src.name}] ${files.length} files`);
  for (const f of files) {
    let raw;
    try { raw = fs.readFileSync(f, "utf8"); } catch { continue; }
    const lines = raw.split(/\r?\n/).filter(Boolean);
    stats.totalLines += lines.length;
    const records = [];
    for (const line of lines) {
      try { records.push(JSON.parse(line)); } catch { stats.parseErrors++; }
    }
    const sid = path.basename(f, ".jsonl");
    if (src.parser === "codex") parseCodex(records, sid, stats);
    else if (src.parser === "claude") parseClaude(records, sid, stats);
    else if (src.parser === "hermes") parseHermes(records, sid, stats);
  }
}

const ranked = [...stats.callsBySkill.entries()]
  .map(([skill, v]) => {
    const calls = v.turnHits.size;
    const realCalls = v.realHits.size;
    const sessions = v.sessions.size;
    const realSessions = v.realSessions.size;
    return {
      skill, calls, realCalls,
      ratio: sessions > 0 ? +(calls / sessions).toFixed(2) : 0,
      realRatio: calls > 0 ? +(realCalls / calls * 100).toFixed(0) : 0,
      sessions, realSessions, rawRefs: v.rawRefs,
      sources: [...v.sources.entries()].map(([s,c]) => `${s}:${c}`).join(","),
      firstSeen: (v.firstSeen || "").slice(0,10),
      lastSeen: (v.lastSeen || "").slice(0,10),
    };
  })
  .sort((a,b) => b.realCalls - a.realCalls || b.calls - a.calls);

console.log("\n========== Skill Usage Report ==========");
console.log(`Files scanned: ${Object.entries(stats.filesByName).map(([k,v])=>`${k}=${v}`).join(", ")}`);
console.log(`Total lines: ${stats.totalLines.toLocaleString()}`);
console.log(`Function calls: ${stats.fnCalls.toLocaleString()}`);
console.log(`Total hits (turn-deduped): ${stats.globalTurnHits.size.toLocaleString()}`);
console.log(`Real hits (with subfile/real-op): ${stats.globalRealHits.size.toLocaleString()}`);
console.log(`Unique skills: ${ranked.length}`);

const reportPath = path.join(__dirname, "skill-usage-report.json");
fs.writeFileSync(reportPath, JSON.stringify({
  generatedAt: new Date().toISOString(),
  scanned: stats.filesByName,
  summary: {
    totalLines: stats.totalLines, fnCalls: stats.fnCalls,
    hits: stats.globalTurnHits.size, realHits: stats.globalRealHits.size,
    uniqueSkills: ranked.length,
  },
  ranking: ranked,
}, null, 2), "utf8");

console.log(`\nReport saved: ${reportPath}`);

console.log("\n=== Top 60 Skills (by real usage) ===");
console.log("rank  real  calls  realSess  ratio  真率   skill");
console.log("----  ----  -----  --------  -----  -----  ----------------------------------");
ranked.slice(0, 60).forEach((r, i) => {
  console.log(
    String(i+1).padStart(4) + "  " +
    String(r.realCalls).padStart(4) + "  " +
    String(r.calls).padStart(5) + "  " +
    String(r.realSessions).padStart(8) + "  " +
    String(r.ratio).padStart(5) + "  " +
    (String(r.realRatio)+"%").padStart(5) + "  " +
    r.skill
  );
});

console.log("\n=== Usage Tiers ===");
const tiers = [
  ["★★★ Core (real≥100)", r => r.realCalls >= 100],
  ["★★  Frequent (real 20-99)", r => r.realCalls >= 20 && r.realCalls < 100],
  ["★   Occasional (real 5-19)", r => r.realCalls >= 5 && r.realCalls < 20],
  ["·   Tried (real 1-4)", r => r.realCalls >= 1 && r.realCalls < 5],
  ["○   Unused (real=0)", r => r.realCalls === 0],
];
for (const [label, fn] of tiers) {
  const list = ranked.filter(fn);
  console.log(`${label}: ${list.length} skills`);
}

const unused = ranked.filter(r => r.realCalls === 0);
if (unused.length > 0) {
  console.log(`\n${unused.length} skills have zero real usage and are archive/external-review candidates.`);
  console.log(`   Check the JSON report for the full list.`);
}

console.log("\nAnalysis complete.");
