/**
 * commit-and-tag-version 配置 —— 中文 changelog + 语义化版本号
 *
 * 兼容 standard-version 配置格式（standard-version 已 archived，改用其活跃 fork）
 * 文档：https://github.com/absolute-version/commit-and-tag-version#configuration
 *
 * 版本号规则（自动）：
 *   feat       → minor
 *   fix        → patch
 *   feat! / BREAKING CHANGE → major
 */
module.exports = {
  // changelog 中文分节：type → 章节（hidden 表示不出现在 changelog）
  types: [
    { type: 'feat', section: '✨ 新功能' },
    { type: 'fix', section: '🐛 Bug 修复' },
    { type: 'perf', section: '⚡ 性能' },
    { type: 'refactor', section: '♻️ 重构' },
    { type: 'revert', section: '⏪ 回退', hidden: true },
    { type: 'docs', section: '📝 文档' },
    { type: 'test', section: '✅ 测试' },
    { type: 'style', section: '💄 格式', hidden: true },
    { type: 'chore', section: '🔧 构建/依赖', hidden: true },
  ],
  // 版本标签前缀
  tagPrefix: 'v',
  // 版本面：本仓无 package.json，五份 agent 插件清单 + cursor 市场元数据
  // 均以 .version 字段对外宣告版本——不列 bumpFiles 则发版只动 tag，
  // 市场侧更新信号停在旧版本（v0.2.0 曾手工同步 6 处）。
  bumpFiles: [
    '.claude-plugin/plugin.json',
    '.codex-plugin/plugin.json',
    '.cursor-plugin/plugin.json',
    '.cursor-plugin/marketplace.json',
    '.grok-plugin/plugin.json',
    '.kimi-plugin/plugin.json',
  ],
  // commit / compare URL 从 git remote 自动推断 host（GitHub / 阿里云 codeup / GitLab 均适配）
  // 如需固定 host，在此覆写 commitUrlFormat / compareUrlFormat
};
