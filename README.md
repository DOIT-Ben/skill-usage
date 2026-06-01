# skill-usage

English: audit-grade skill usage analyzer for AI agent logs.

`skill-usage` 是一个审计型技能使用分析器，用来统计 AI agent 里哪些 skill 真正被调用了，哪些只是被提到，哪些只是噪声。

## 这个仓库做什么

- 按 `strictCalls` 排名
- 区分 `wideMentions` 和真实调用
- 审计主来源、补充来源、噪声来源
- 输出 Markdown、CSV、JSON 报告
- 给出常驻、外置、别名合并、描述优化等建议

## 为什么需要它

AI agent 装多了 skill 之后，很容易只看到“列表里有”，看不到“真的在用”。
这个工具就是把“看起来有关”与“真正触发过”拆开，免得命中率统计被系统提示、路径清单、旧报告带偏。

## 快速开始

```bash
git clone https://github.com/DOIT-Ben/skill-usage.git
```

在对话里直接说：

```text
用 skill-usage 给我统计全部 skills 的命中率，并解释 strictCalls 和 wideMentions 的区别。
```

也可以直接跑扫描器：

```powershell
$skill = "<path-to-skill-usage>"
$env:OUTPUT_DIR = (Get-Location).Path
Remove-Item Env:\INCLUDE_SQLITE -ErrorAction SilentlyContinue
python "$skill\scripts\deep_skill_usage_scan.py"
```

## 输出

深度扫描会生成：

- `skill-usage-deep-report.json`
- `skill-usage-ranking-deep.md`
- `skill-usage-ranking-deep.csv`
- `skill-usage-source-audit.md`

旧版轻量分析器还保留在：

```powershell
node "$skill\scripts\analyzer-legacy.js"
```

## 统计口径

| 字段 | 含义 |
|---|---|
| `strictCalls` | 有明确执行上下文的真实调用证据 |
| `wideMentions` | 只是在提示词、路径、文档、列表里出现的提及 |
| `rawRefs` | 去重前的原始引用量 |
| `strictSessions` | 有真实调用证据的会话数 |
| `realRatio` | `strictCalls / wideMentions`，更像噪声/触发信号，不是绝对分数 |

## 覆盖范围

主榜会看这些来源：

- Codex sessions 和 archived sessions
- Codex rollout summaries
- Claude project transcripts
- Hermes sessions / logs
- OpenClaw / AutoClaw sessions
- Cursor agent transcripts
- mini-agent logs

补充来源单独审计，不默认并入主榜：

- Cursor / VS Code workspace storage
- Codex desktop logs
- Claude local-agent sessions
- Continue.dev、Trae、Windsurf、opencode、WorkBuddy、CodeBuddy logs
- SQLite 状态库和日志库

细则见 `references/coverage-and-noise-map.md`。

## 建议规则

| 动作 | 触发条件 |
|---|---|
| 保留常驻 | `strictCalls` 高，且跨会话稳定使用 |
| 加薄入口 | 需求高，但正文重、频率低 |
| 优化 description | `wideMentions` 高但 `strictCalls` 低 |
| 合并别名 | 同一能力被拆成多个名字 |
| 保留外置 | 有用，但场景窄 |
| 归档/忽略 | 只有噪声提及，没有真实调用 |

`strictCalls = 0` 不等于立刻删除，更适合先看是否是新装、依赖项或策略性技能。

## 隐私

分析只在本地进行。报告只应包含技能名、计数、日期和来源，不要带原始提示词、账号信息、token、本机私人路径或无关文本。

## 唯一名称

唯一 canonical 仓库和 skill 名称是：

```text
skill-usage
```

`skill-usage-auditor` 已并入这个仓库，作为深度审计工作流。

## License

MIT License. See `LICENSE`.
