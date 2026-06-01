# skill-usage

English: An independent skill for auditing AI agent skill usage and hit-rate evidence.

`skill-usage` 是一个独立公开的技能调用量统计 skill。它用于分析 AI agent 的会话日志，统计哪些 skill 被真正调用、哪些只是被系统提示或路径清单提到，并输出可复查的排名、覆盖范围和整理建议。

## 适合什么场景

- 想知道一个 agent 实际最常用哪些 skills
- 想统计某个技能库的调用量、命中率和跨会话覆盖
- 想区分“真实调用”和“只是出现在 system prompt 里”
- 想发现统计流程有没有漏掉 Codex、Claude、Hermes、Cursor 等会话来源
- 想决定哪些 skills 应该常驻、外置、合并别名或优化 description

## 核心能力

- **真实调用排名**：主榜按 `strictCalls` 排序，而不是按文本出现次数排序。
- **噪声分层**：把 `wideMentions`、路径清单、系统提示、历史报告和真实调用分开。
- **来源审计**：报告扫描了哪些来源、跳过了哪些来源、哪些来源只能作为补充证据。
- **整理建议**：给出常驻、薄入口、外置、归档、别名合并、description 优化建议。
- **本地隐私优先**：只输出聚合统计，不输出原始提示词、账号信息或 token。

## 安装

```bash
git clone https://github.com/DOIT-Ben/skill-usage.git
```

如果你的 agent 支持从本地目录安装 skill，可以把这个仓库作为 skill 目录安装。

## 在对话中使用

可以直接这样说：

```text
用 skill-usage 统计全部 skills 的调用量，给我主榜、补充榜、噪声说明和整理建议。
```

也可以问更具体的问题：

```text
为什么这个 skill 的 wideMentions 很高，但 strictCalls 很低？这算命中率差吗？
```

## 直接运行扫描器

```powershell
$skill = "<path-to-skill-usage>"
$env:OUTPUT_DIR = (Get-Location).Path
Remove-Item Env:\INCLUDE_SQLITE -ErrorAction SilentlyContinue
python "$skill\scripts\deep_skill_usage_scan.py"
```

## 输出文件

默认生成：

- `skill-usage-deep-report.json`
- `skill-usage-ranking-deep.md`
- `skill-usage-ranking-deep.csv`
- `skill-usage-source-audit.md`

旧版轻量扫描器保留为兼容入口：

```powershell
node "$skill\scripts\analyzer-legacy.js"
```

## 统计口径

| 字段 | 含义 | 用途 |
|---|---|---|
| `strictCalls` | 有明确执行上下文的真实调用证据 | 主排名依据 |
| `wideMentions` | 在提示词、路径、文档、列表、缓存中出现的提及 | 需求和噪声信号 |
| `rawRefs` | 去重前的原始引用次数 | 诊断用 |
| `strictSessions` | 出现真实调用证据的会话数 | 判断是否跨会话稳定 |
| `realRatio` | `strictCalls / wideMentions` | 判断噪声或触发质量 |

不要把 `wideMentions` 当作真实调用量。它可能只是系统提示、权限列表、README、历史报告或路径清单造成的重复出现。

## 覆盖范围

主榜优先使用干净的会话/转录来源，例如：

- Codex sessions 和 archived sessions
- Codex rollout summaries
- Claude project transcripts
- Hermes sessions / logs
- OpenClaw / AutoClaw sessions
- Cursor agent transcripts
- mini-agent logs

补充来源会单独审计，不默认并入主榜，例如：

- Cursor / VS Code workspace storage
- Codex desktop logs
- Claude local-agent sessions
- Continue.dev、Trae、Windsurf、opencode、WorkBuddy、CodeBuddy logs
- SQLite 状态库和日志库

详细边界见 `references/coverage-and-noise-map.md`。

## 建议规则

| 动作 | 典型条件 |
|---|---|
| 保留常驻 | `strictCalls` 高，跨会话稳定 |
| 加薄入口 | 需求高，但 skill 正文较重或场景低频 |
| 优化 description | `wideMentions` 高但 `strictCalls` 低 |
| 合并别名 | 同一能力被多个名称拆分 |
| 保留外置 | 有价值但场景窄 |
| 归档或忽略 | 只有噪声提及，没有真实调用 |

`strictCalls = 0` 不等于可以直接删除。它只是进入“归档/外置复查”候选，还需要结合是否新安装、是否是依赖技能、是否有战略价值来判断。

## 环境变量

| 变量 | 作用 |
|---|---|
| `OUTPUT_DIR` | 输出目录，默认当前目录 |
| `REPORT_SUFFIX` | 给输出文件名追加后缀 |
| `EXTRA_PATHS_FILE` | 额外扫描路径列表，一行一个路径 |
| `ONLY_EXTRA=1` | 只扫描 `EXTRA_PATHS_FILE` 中的路径 |
| `ONLY_SQLITE=1` | 只扫描 SQLite 来源 |
| `INCLUDE_SQLITE=1` | 在常规扫描中加入 SQLite 来源 |
| `SKIP_SQLITE=1` | 跳过 SQLite 来源 |
| `ONLY_SOURCES` | 只扫描指定 source label，逗号分隔 |
| `MAX_TEXT_BYTES` | 单个文本文件最大扫描字节数 |

## 隐私边界

这个 skill 的目标是统计调用量，不是公开会话内容。报告应只包含技能名、聚合计数、日期、来源标签和建议，不应包含：

- 原始提示词或完整会话内容
- token、API key、cookie、账号信息
- 个人目录、私有项目路径或无关私人上下文
- 与技能统计无关的文本

## 仓库

- GitHub: https://github.com/DOIT-Ben/skill-usage
- Skill name: `skill-usage`

## License

MIT License. See `LICENSE`.
