#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
必应每日壁纸抓取脚本（纯标准库，无第三方依赖）

接口：https://www.bing.com/HPImageArchive.aspx
原图：https://www.bing.com + urlbase + "_1920x1080.jpg" / "_UHD.jpg"

它会：
  1) 调用接口拿到近 N 天壁纸元数据
  2) 把图片下载到 downloads/<分辨率>/ 下（按日期命名，幂等：已存在则跳过）
  3) 扫描 downloads/ 生成 data/manifest.json（含标题/版权/各分辨率路径），
     供静态展示页读取。脚本幂等，重复运行不会丢历史。

用法：
  python bing_wallpaper.py                 # 抓当天的（两种分辨率）
  python bing_wallpaper.py --days 8        # 批量抓近 8 天（最大 8）
  python bing_wallpaper.py --res 1920x1080 # 只抓某一种分辨率
  python bing_wallpaper.py --mkt en-US     # 换地区（影响壁纸内容）
  python bing_wallpaper.py --force         # 强制重新下载已存在的
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BING_API = "https://www.bing.com/HPImageArchive.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}
SUPPORTED_RES = ["1920x1080", "UHD"]
MAX_DAYS = 8


def fetch_api(n, mkt):
    """请求接口，返回 images 列表。"""
    params = urllib.parse.urlencode({
        "format": "js", "idx": 0, "n": n, "mkt": mkt,
    })
    req = urllib.request.Request(f"{BING_API}?{params}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8")).get("images", [])


def build_url(urlbase, res):
    suffix = "_UHD.jpg" if res == "UHD" else f"_{res}.jpg"
    return "https://www.bing.com" + urlbase + suffix


def download(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
    with open(dest, "wb") as f:
        f.write(body)


def grab(urlbase, date, res, force):
    """下载单张图。返回 'downloaded' / 'skipped' / 'failed'。"""
    folder = os.path.join("downloads", res)
    os.makedirs(folder, exist_ok=True)
    fname = f"{date}_{res}.jpg"
    dest = os.path.join(folder, fname)
    if os.path.exists(dest) and not force:
        return "skipped"
    url = build_url(urlbase, res)
    try:
        download(url, dest)
        return "downloaded"
    except urllib.error.HTTPError as e:
        if res == "UHD" and e.code == 404:  # UHD 不可用回退 1920x1080
            try:
                download(build_url(urlbase, "1920x1080"), dest)
                return "downloaded"
            except Exception:
                return "failed"
        return "failed"
    except Exception:
        return "failed"


def rel_path(date, res):
    return f"downloads/{res}/{date}_{res}.jpg"


def load_manifest(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return {w["date"]: w for w in json.load(f).get("wallpapers", [])}
        except Exception:
            return {}
    return {}


def main():
    ap = argparse.ArgumentParser(description="必应每日壁纸抓取脚本")
    ap.add_argument("--days", type=int, default=1,
                    help=f"抓取近几天（1-{MAX_DAYS}，默认1=当天）")
    ap.add_argument("--mkt", default="zh-CN", help="地区代码")
    ap.add_argument("--res", nargs="*", default=SUPPORTED_RES,
                    help="分辨率列表，默认两种都要")
    ap.add_argument("--force", action="store_true", help="强制重下已存在的")
    ap.add_argument("--manifest", default="data/manifest.json",
                    help="清单输出路径")
    args = ap.parse_args()

    n = max(1, min(MAX_DAYS, args.days))
    res_list = [r for r in args.res if r in SUPPORTED_RES] or SUPPORTED_RES

    print(f"==> 请求必应接口 (days={n}, mkt={args.mkt}, res={res_list})")
    try:
        images = fetch_api(n, args.mkt)
    except Exception as e:
        print(f"请求接口失败: {e}")
        sys.exit(1)

    existing = load_manifest(args.manifest)  # 历史清单（云端回传的）
    downloaded = skipped = failed = 0

    for img in images:
        date = img.get("startdate", "unknown")
        urlbase = img.get("urlbase")
        if not urlbase:
            continue
        entry = existing.get(date, {
            "date": date,
            "title": img.get("title", ""),
            "copyright": img.get("copyright", ""),
            "link": img.get("copyrightlink", ""),
            "images": {},
        })
        # 用接口最新元数据刷新（历史项保留原值）
        entry["title"] = img.get("title", entry.get("title", ""))
        entry["copyright"] = img.get("copyright", entry.get("copyright", ""))
        entry["link"] = img.get("copyrightlink", entry.get("link", ""))
        entry.setdefault("images", {})

        for res in res_list:
            status = grab(urlbase, date, res, args.force)
            if status == "downloaded":
                downloaded += 1
                print(f"  ok    {date}_{res}.jpg")
            elif status == "skipped":
                skipped += 1
            else:
                failed += 1
                print(f"  FAIL  {date}_{res}.jpg")
            # 只要本地存在该分辨率就写进清单
            if os.path.exists(os.path.join("downloads", res, f"{date}_{res}.jpg")):
                entry["images"][res] = rel_path(date, res)
        existing[date] = entry

    wallpapers = [existing[d] for d in sorted(existing.keys(), reverse=True)]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Bing Daily Image (HPImageArchive.aspx)",
        "wallpapers": wallpapers,
    }
    os.makedirs(os.path.dirname(args.manifest), exist_ok=True)
    with open(args.manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n完成。本次下载 {downloaded} / 跳过 {skipped} / 失败 {failed}；"
          f"清单共 {len(wallpapers)} 张 -> {args.manifest}")


if __name__ == "__main__":
    main()
