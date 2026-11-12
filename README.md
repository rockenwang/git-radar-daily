# Git 副业雷达 · 每日自动报告

夜秣「git副业雷达」技能的云端托管：每天北京时间 **09:00** 在 GitHub Actions 上跑一遍，
报告自动发布到 GitHub Pages。

## 看报告

- 网页版（手机也能看）：**https://rockenwang.github.io/git-radar-daily/**
- 原始 HTML：本仓库 `reports/Git副业雷达_YYYY-MM-DD.html`
- 每次运行的构建产物：Actions → 对应 run → Artifacts → `radar-report`

## 它每天做什么

1. 从 SkillHub 拉最新的「夜秣git副业雷达」技能（不 vendoring，作者更新自动跟上）
2. 用 `GITHUB_TOKEN` 走 GitHub API 抓 trending + 近 30 天新建高星项目
3. 按「能不能变成钱」六维打分，出 8 个项目
4. **免费机翻**补全中文（Google 公共端点 → MyMemory 兜底，不需任何 API key）
5. 把报告提交回本仓库，并发布到 GitHub Pages

## 关于翻译

技能原版推荐由 Agent 做「精译」。这里没有接任何大模型 API，用的是免费公共翻译端点，
所以报告里会诚实地挂 **机器直译** 标签 —— 够看，但不是人写的。

想升级成精译，两种办法：

- 在 `scripts/auto_translate.py` 里塞一个模型 API 调用（改 `_google` / `_mymemory` 那层）
- 或者本地开着 DSH 让 Agent 跑

## 历史账本

`radar-data/` 保存了跨天查重账本（`seen.json`）、每日档案（`archive/`）、
星数快照（`history/`）。**别删** —— 删了第二天会重新推荐同一批项目，档案库也归零。

## 手动触发

Actions → 每日 Git 副业雷达 → Run workflow。

## 改时间

编辑 `.github/workflows/daily.yml` 里的 cron。注意 **GitHub 用的是 UTC**：
北京时间 09:00 = `0 1 * * *`。

## 已知限制

- GitHub Actions 的定时任务在整点高峰可能延迟 5-30 分钟启动，这是平台行为
- 公开仓库的 Actions 免费；私有仓库每月 2000 分钟额度（本任务每次约 3 分钟）
- 60 天没有任何 commit 的活动仓库，GitHub 会自动暂停定时任务（本任务每天 commit，不受影响）
