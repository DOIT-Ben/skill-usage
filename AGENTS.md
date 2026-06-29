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
