# 必应每日壁纸（自动抓取 + 静态展示）

每天 **17:00（北京时间）** 由 GitHub Actions 自动抓取必应当日壁纸（1920×1080 与 4K UHD 两种分辨率），
提交到本仓库的 `gh-pages` 分支，并通过 **GitHub Pages** 生成在线画廊。
**图片只存在于 GitHub 仓库，不占用你本地磁盘。**

## 在线地址
- 壁纸展示页（GitHub Pages）：`https://<你的用户名>.github.io/bing-wallpaper/`
- 仓库地址：`https://github.com/<你的用户名>/bing-wallpaper`

> 首次启用 Pages 后约 1 分钟可访问；若 404，确认仓库 Settings → Pages 的 Source 已设为 `gh-pages` 分支、`/ (root)`。

## 工作原理
1. `bing_wallpaper.py` 调用必应官方免鉴权接口 `HPImageArchive.aspx` 获取近几天壁纸元数据。
2. 拼出高清原图地址下载到 `downloads/<分辨率>/`，按日期命名，**幂等**（已存在则跳过）。
3. 扫描 `downloads/` 生成 `data/manifest.json`（标题 / 版权 / 各分辨率路径）。
4. Actions 工作流：先还原 `gh-pages` 上的历史图片 → 跑脚本补抓当天 → 把 `index.html`+`downloads/`+`data/` 发布到 `gh-pages`（orphan 分支，历史不膨胀）。
5. GitHub Pages 从 `gh-pages` 提供静态画廊。

## 本地使用（可选）
纯标准库，无需安装依赖，用 Python 3.12+ 运行：
```bash
python bing_wallpaper.py            # 抓当天
python bing_wallpaper.py --days 8  # 批量抓近 8 天
python bing_wallpaper.py --res 1920x1080   # 只抓某种分辨率
python bing_wallpaper.py --mkt en-US        # 换地区
```
本地运行会把图片存到 `downloads/`（仅本地调试用；日常抓取由云端完成，无需本地保留）。

## 手动触发
仓库 → Actions → Daily Bing Wallpaper → Run workflow，可立即跑一次。

## 注意
- 必应接口最多回溯 7 天（`--days` 上限 8，含当天），长期积累靠每日自动运行。
- GitHub 计划任务在仓库 60 天无活动后会被自动暂停，届时手动触发一次即可恢复。
- 仓库会随时间增长（每天约 4–8 MB），属正常现象。
