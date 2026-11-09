# Awesome Mac 导航页

基于 [jaywcjlove/awesome-mac](https://github.com/jaywcjlove/awesome-mac) 构建的 macOS 精选软件导航页，支持搜索、分类浏览、今日/本月新增。

**在线访问**：https://zhizhi2213.github.io/awesome-mac-nav/

## 功能

- 🔍 **全局搜索** — 中英文关键词匹配，结果高亮（搜"编辑器"或 "clipboard" 都可以）
- 📂 **两级分类** — 大类 + 子分类下拉联动，侧栏同步（开发者工具 → IDE／编辑器）
- 🔥 **今日新增 / 🆕 本月新增** — 日期由 README 提交记录自动计算，条目带"新增 MM-DD"徽章
- 🏷️ **标签筛选** — 开源 / 免费 / App Store / 原生，可叠加
- 🌐 **中英双语** — 一键切换界面语言与条目描述，偏好自动记忆
- 🔄 **每日自动更新** — GitHub Actions 每天定时重建数据并自动提交

## 数据说明

- 软件数据解析自 awesome-mac 的英文 README（25 个分类、1500+ 条目）
- 中文描述来自其官方 README-zh，按 URL 合并（部分条目无中文则回退英文）
- 「新增」日期：对比月初基线快照 + 逐条扫描 commit diff / 提交标题匹配得出

## 本地运行

无需安装任何依赖，直接用浏览器打开 `index.html` 即可（数据已内联，单文件自包含）。

## 更新数据

```bash
python3 build.py          # 拉取最新 README + 最近提交，重建 index.html
python3 build.py --scan   # 全量扫描本月提交 diff（较慢，通常不需要）
```

## 仓库结构

```
├── index.html        # 页面成品（数据内联，可直接部署）
├── template.html     # 页面模板（/*__DATA__*/ 占位符）
├── build.py          # 构建脚本：解析 README / 合并中文 / 计算新增日期 / 内联生成
├── data.js / data.json  # 构建产物数据
└── added-cache.json  # 新增日期缓存（加速重复构建）
```

## License

MIT
