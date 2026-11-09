#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 Awesome Mac 双语导航页数据
1. 解析英文 README.md -> 分类/子分类/条目
2. 解析中文 README-zh.md, 按 URL 合并中文名与中文描述
3. 通过 GitHub commit diff 计算每个条目的首次新增日期(今日/本月新增)
4. 生成 data.js / data.json, 并把数据内联进 index.html(单文件自包含)
"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

REPO = "jaywcjlove/awesome-mac"
CST = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))

# 分类中文名映射
CAT_ZH = {
    "Reading and Writing Tools": "阅读与写作",
    "Developer Tools": "开发者工具",
    "Design and Product": "设计与产品",
    "AI Tools": "AI 工具",
    "Communication": "通信协作",
    "Data Recovery Tools": "数据恢复",
    "Audio and Video Tools": "音视频工具",
    "Download Management Tools": "下载工具",
    "Cloud Storage": "网盘与云存储",
    "Input Methods": "输入法",
    "Voice-to-Text": "语音转文字",
    "Browsers": "浏览器",
    "Translation Tools": "翻译工具",
    "Education": "教育",
    "Finance": "金融",
    "Encryption": "加密工具",
    "Security Tools": "安全工具",
    "Proxy and VPN Tools": "代理与 VPN",
    "Utilities": "实用工具",
    "Gaming Software": "游戏",
    "Remote Login Software": "远程控制",
    "QuickLook Plugins": "QuickLook 插件",
    "Third Party App Markets": "第三方应用市场",
    "Mac App Download Sites": "Mac 软件下载站",
    "Terminal Apps": "终端工具",
}
SUB_ZH = {
    "Text Editors": "文本编辑器",
    "Office": "办公套件",
    "Markdown Tools": "Markdown 工具",
    "Note-taking": "笔记工具",
    "Journaling": "日记",
    "Writing": "写作",
    "Ebooks": "电子书",
    "RSS": "RSS 阅读",
    "Others": "其他",
    "IDEs": "IDE／编辑器",
    "Developer Utilities": "开发者实用工具",
    "Regular Expression Editors": "正则表达式编辑器",
    "API Development and Analysis": "API 开发与分析",
    "Network Analysis": "网络分析",
    "Frameworks For Hybrid Applications": "混合应用框架",
    "Version Control": "版本控制",
    "Virtualization": "虚拟机",
    "Databases": "数据库",
    "Terminal Apps": "终端工具",
    "Design Tools": "设计工具",
    "Prototyping and Mind-Mapping Tools": "原型与思维导图",
    "Screenshot Tools": "截图工具",
    "Screen Recording": "屏幕录制",
    "Other Tools": "其他工具",
    "Collaboration and Team Tools": "协作与团队工具",
    "Email Clients": "邮件客户端",
    "File Sharing": "文件共享",
    "Audio Record and Process": "音频录制与处理",
    "Clipboard Tools": "剪贴板工具",
    "Menu Bar Tools": "菜单栏工具",
    "Cleanup and Uninstall": "清理与卸载",
    "File Organization Tools": "文件整理",
    "General Tools": "通用工具",
    "To-Do Lists": "待办事项",
    "Productivity": "效率提升",
    "Window Management": "窗口管理",
    "Password Management": "密码管理",
    "Finder Tools": "Finder 增强",
    "Quality of Life Improvements": "体验优化",
    "System Related Tools": "系统工具",
    "Package Managers": "包管理器",
    "Genuine Sites": "正版下载站",
    "Pirated software download site blocklist": "盗版下载站黑名单",
}


def fetch(url, retries=4):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "awesome-mac-page-builder"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # 网络抖动/限流重试
            last = e
            time.sleep(1.2 * (i + 1))
    raise last


def norm_url(u):
    u = u.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


ITEM_RE = re.compile(r"^\s*[*-]\s*\[(.+?)\]\((\S+?)(?:\s+\".*?\")?\)\s*[-–]?\s*(.*)$")


def parse_readme(text):
    categories, cur_cat, cur_sub = [], None, None
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("###"):
            name = line[3:].strip()
            if name in ("Contents", "目录", "Contributors", "License", "Contributing"):
                cur_cat = None
                continue
            cur_cat = {"name": name, "subs": [], "items": []}
            categories.append(cur_cat)
            cur_sub = None
        elif line.startswith("### ") and cur_cat is not None:
            name = re.sub(r"\[!.*", "", line[4:]).strip()
            cur_sub = {"name": name, "items": []}
            cur_cat["subs"].append(cur_sub)
        elif cur_cat is not None and (line.startswith("* ") or line.startswith("- ")):
            m = ITEM_RE.match(line)
            if not m:
                continue
            name, url, rest = m.group(1).strip(), m.group(2).strip(), m.group(3)
            desc = re.sub(r"\[!\[[^\]]*\]\[[^\]]*\]\]\(\S+\)\s*", "", rest)
            desc = re.sub(r"!\[[^\]]*\]\[[^\]]*\]", "", desc).strip().rstrip(" .;。")
            tags = []
            if "Open-Source Software" in rest: tags.append("oss")
            if "Freeware" in rest: tags.append("free")
            if "App Store" in rest: tags.append("appstore")
            if "Native App" in rest: tags.append("native")
            item = {"name": name, "url": url, "desc": desc, "tags": tags}
            (cur_sub["items"] if cur_sub else cur_cat["items"]).append(item)
    return categories


added_dates = {}
CACHE_FILE = os.path.join(HERE, "added-cache.json")


def load_cache():
    """缓存: {"items": {url: date}, "commits": [sha...]} 避免每次重建重复扫描"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"items": {}, "commits": []}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)


def list_commits_api(since):
    url = f"https://api.github.com/repos/{REPO}/commits?path=README.md&per_page=100&since={since}"
    out = []
    for c in json.loads(fetch(url)):
        dt = datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00")).astimezone(CST)
        out.append({"sha": c["sha"], "date": dt, "msg": c["commit"]["message"]})
    return out


def list_commits_atom():
    """Atom feed 无 API 频率限制, 取最近 20 条提交"""
    import xml.etree.ElementTree as ET
    xml = fetch(f"https://github.com/{REPO}/commits/master.atom")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(xml).findall("a:entry", ns):
        title = (e.findtext("a:title", "", ns) or "").strip()
        upd = e.findtext("a:updated", "", ns)
        sha = (e.findtext("a:id", "", ns) or "").rsplit("/", 1)[-1]
        dt = datetime.fromisoformat(upd.replace("Z", "+00:00")).astimezone(CST)
        out.append({"sha": sha, "date": dt, "msg": title})
    return out


def list_commits(since):
    try:
        return list_commits_api(since)
    except Exception as e:
        print(f"warn: GitHub API 不可用({e}), 改用 Atom feed", file=sys.stderr)
        return list_commits_atom()


def scan_diff(sha, dt):
    time.sleep(0.4)
    diff = fetch(f"https://github.com/{REPO}/commit/{sha}.diff")
    cur = None
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            parts = line.split()
            cur = parts[-1].lstrip("b/") if len(parts) >= 4 else None
        elif cur == "README.md" and line.startswith("+") and not line.startswith("+++"):
            m = re.match(r"^\+\s*[*-]\s*\[.+?\]\((\S+?)(?:\s+\".*?\")?\)", line)
            if m:
                added_dates.setdefault(norm_url(m.group(1)), dt.strftime("%Y-%m-%d"))


def iter_items(categories):
    for cat in categories:
        for it in cat["items"]:
            yield cat, None, it
        for sub in cat["subs"]:
            for it in sub["items"]:
                yield cat, sub, it


def main():
    today = datetime.now(CST).strftime("%Y-%m-%d")
    month_start = today[:7] + "-01"
    month_start_dt = datetime.strptime(month_start, "%Y-%m-%d").replace(tzinfo=CST)

    categories = parse_readme(fetch(f"https://raw.githubusercontent.com/{REPO}/master/README.md"))

    # 中文 README: URL -> 中文名/描述
    zh_map = {}
    try:
        for cat, sub, it in iter_items(parse_readme(fetch(f"https://raw.githubusercontent.com/{REPO}/master/README-zh.md"))):
            zh_map[norm_url(it["url"])] = {"name": it["name"], "desc": it["desc"]}
    except Exception as e:
        print("warn: 中文 README 拉取失败 ->", e, file=sys.stderr)

    # 分类中英名 + 条目中文名
    zh_hit = 0
    for cat, sub, it in iter_items(categories):
        k = norm_url(it["url"])
        z = zh_map.get(k)
        if z:
            it["nameZh"] = z["name"]
            it["descZh"] = z["desc"]
            zh_hit += 1
        it["cat"] = cat["name"]
        it["sub"] = sub["name"] if sub else ""
    for cat in categories:
        cat["zh"] = CAT_ZH.get(cat["name"], cat["name"])
        for sub in cat["subs"]:
            sub["zh"] = SUB_ZH.get(sub["name"], sub["name"])

    n_items = sum(1 for _ in iter_items(categories))
    print(f"条目 {n_items}, 中文匹配 {zh_hit} ({zh_hit * 100 // max(n_items, 1)}%)")
    missing_cat = [c["name"] for c in categories if c["name"] not in CAT_ZH]
    missing_sub = [s["name"] for c in categories for s in c["subs"] if s["name"] not in SUB_ZH]
    if missing_cat or missing_sub:
        print("缺少中文映射:", missing_cat, missing_sub, file=sys.stderr)

    # 新增日期: 本地缓存 + 最近提交标题(不依赖 GitHub API 基线快照)
    try:
        commits = sorted(list_commits("2026-10-20T00:00:00Z"), key=lambda c: c["date"])
    except Exception as e:
        print(f"warn: 提交列表不可用({e}), 仅使用本地缓存 added-cache.json", file=sys.stderr)
        commits = []
    cache = load_cache()
    added_dates.update(cache.get("items", {}))
    recent = [c for c in commits if c["date"] >= month_start_dt]

    # 提交标题形如 "Add Polka to Menu Bar Tools (#4390)" / "Add Quill (#4343)"
    msg_dates = {}
    for c in recent:
        first = c["msg"].splitlines()[0]
        m = re.match(r"(?i)^add\s+(.+?)(?:\s+(?:to|under|in)\s+.*)?\s*(?:\(#\d+\))?\s*$", first)
        if m:
            key = m.group(1).strip().lower()
            msg_dates.setdefault(key, c["date"].strftime("%Y-%m-%d"))

    # 可选: 逐条扫 diff(慢且易被 GitHub 限流), 传 --scan 才开启
    if "--scan" in sys.argv:
        done = set(cache.get("commits", []))
        todo = [c for c in recent if c["sha"] not in done]
        print(f"扫描 diff: {len(todo)} 个提交...")
        for c in todo:
            try:
                scan_diff(c["sha"], c["date"])
                done.add(c["sha"])
            except Exception as e:
                print("  warn:", c["sha"][:8], e, file=sys.stderr)
        cache["commits"] = sorted(done)

    cache["items"] = dict(added_dates)

    def date_from_msg(name):
        """用 commit 标题兜底匹配条目新增日期"""
        k = name.strip().lower()
        if k in msg_dates:
            return msg_dates[k]
        pat = re.compile(r"\b" + re.escape(k) + r"\b")
        hits = [c for c in recent if pat.search(c["msg"].lower())]
        return hits[-1]["date"].strftime("%Y-%m-%d") if hits else None

    n_new = n_today = 0
    for _, _, it in iter_items(categories):
        k = norm_url(it["url"])
        d = added_dates.get(k) or date_from_msg(it["name"])
        if d and d >= month_start:
            it["added"] = d
            added_dates.setdefault(k, d)
            n_new += 1
            if d == today:
                n_today += 1

    cache["items"] = dict(added_dates)
    save_cache(cache)

    data = {"builtAt": today, "today": today, "monthStart": month_start,
            "categories": categories, "stats": {"total": n_items, "month": n_new, "today": n_today}}
    print(f"本月新增 {n_new}, 今日新增 {n_today}")

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(HERE, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.AWESOME_MAC_DATA = " + payload + ";\n")

    # 内联进模板 -> index.html (单文件, 不依赖外部资源)
    tpl_path = os.path.join(HERE, "template.html")
    if os.path.exists(tpl_path):
        with open(tpl_path, encoding="utf-8") as f:
            tpl = f.read()
        html = tpl.replace("/*__DATA__*/", payload)
        with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"index.html 已生成 ({len(html)//1024} KB, 数据已内联)")


if __name__ == "__main__":
    main()
