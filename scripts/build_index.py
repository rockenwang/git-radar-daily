#!/usr/bin/env python3
"""Build a browsable index for the daily radar archive.

Reads every dated report in ``reports/`` plus the skill's own archive index
(``radar-data/archive/index.json``) and writes:

* ``docs/<date>.html``  — a permanent copy of each day's report
* ``docs/index.html``   — a date list with per-day project names and a filter box

Nothing is ever overwritten by a later day: each date keeps its own URL.

Usage: python build_index.py [--reports DIR] [--data DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
TITLE = "Git 副业雷达 · 每日归档"


def load_archive(data: pathlib.Path) -> dict[str, dict]:
    idx = data / "archive" / "index.json"
    if not idx.exists():
        return {}
    try:
        # utf-8-sig: tolerate a BOM if the file was ever rewritten by an editor
        # or a shell that prepends one (PowerShell's Set-Content does).
        raw = json.loads(idx.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return {row["date"]: row for row in raw.get("items", []) if row.get("date")}


def collect(reports: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    found = []
    for path in reports.glob("*.html"):
        m = DATE_RE.search(path.name)
        if m:
            found.append((m.group(1), path))
    found.sort(key=lambda pair: pair[0], reverse=True)
    return found


def render_index(days: list[tuple[str, int, list[str]]]) -> str:
    rows = []
    for date, count, names in days:
        chips = "".join(
            f'<span class="chip">{html.escape(n)}</span>' for n in names
        )
        rows.append(
            f"""      <li class="day" data-date="{date}" data-names="{html.escape(' '.join(names))}">
        <a class="date" href="{date}.html">{date}</a>
        <span class="meta">{count} 个项目</span>
        <div class="chips">{chips}</div>
      </li>"""
        )
    body = "\n".join(rows) if rows else '<li class="empty">还没有任何报告</li>'
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 40px 20px 80px;
    font: 15px/1.65 -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
    background: #f6f7f4; color: #1d241f;
  }}
  .wrap {{ max-width: 760px; margin: 0 auto; }}
  h1 {{ font-size: 26px; margin: 0 0 6px; letter-spacing: .01em; }}
  .sub {{ color: #6b746c; font-size: 13px; margin-bottom: 26px; }}
  .sub a {{ color: #2f6b45; }}
  input[type=search] {{
    width: 100%; padding: 11px 14px; margin-bottom: 18px;
    border: 1px solid #d9ded6; border-radius: 8px; font-size: 14px;
    background: #fff; color: inherit;
  }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  .day {{
    background: #fff; border: 1px solid #e6e9e3; border-radius: 10px;
    padding: 16px 18px; margin-bottom: 12px;
  }}
  .date {{ font-weight: 600; font-size: 16px; color: #1d241f; text-decoration: none; }}
  .date:hover {{ text-decoration: underline; }}
  .meta {{ color: #7b847c; font-size: 12px; margin-left: 10px; }}
  .chips {{ margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .chip {{
    font-size: 12px; color: #46524a; background: #f0f3ee;
    border-radius: 5px; padding: 2px 7px; font-family: ui-monospace, Consolas, monospace;
  }}
  .empty {{ color: #7b847c; padding: 20px 0; }}
  .hidden {{ display: none; }}
  footer {{ margin-top: 30px; color: #8b938c; font-size: 12px; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #14171a; color: #e6eae4; }}
    .day {{ background: #1b1f23; border-color: #2a3035; }}
    .date {{ color: #e6eae4; }}
    .chip {{ background: #252b30; color: #b9c2ba; }}
    input[type=search] {{ background: #1b1f23; border-color: #2a3035; color: inherit; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{TITLE}</h1>
  <p class="sub">每天一份，互不覆盖。数据来自 <a href="https://skillhub.cn">夜秣 git副业雷达</a>，北京时间每天 09:00 自动更新。</p>
  <input id="q" type="search" placeholder="按日期或项目名筛选，例如 2026-11 或 ppt">
  <ul id="list">
{body}
  </ul>
  <footer>共 {len(days)} 天 · 由 GitHub Actions 自动生成</footer>
</div>
<script>
  const q = document.getElementById('q');
  const items = [...document.querySelectorAll('.day')];
  q.addEventListener('input', () => {{
    const v = q.value.trim().toLowerCase();
    for (const el of items) {{
      const hay = (el.dataset.date + ' ' + el.dataset.names).toLowerCase();
      el.classList.toggle('hidden', v !== '' && !hay.includes(v));
    }}
  }});
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="reports")
    ap.add_argument("--data", default="radar-data")
    ap.add_argument("--out", default="docs")
    args = ap.parse_args()

    reports = pathlib.Path(args.reports).resolve()
    data = pathlib.Path(args.data).resolve()
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    archive = load_archive(data)
    files = collect(reports)
    if not files:
        print("no reports found")
        return 1

    days = []
    for date, path in files:
        out.joinpath(f"{date}.html").write_text(
            path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
        )
        row = archive.get(date) or {}
        names = row.get("names") or []
        count = row.get("daily") or len(names)
        days.append((date, count, names))

    out.joinpath("index.html").write_text(render_index(days), encoding="utf-8")
    out.joinpath(".nojekyll").write_text("", encoding="utf-8")
    print(f"wrote {len(days)} dated page(s) + index.html -> {out}")
    for date, count, _ in days:
        print(f"  {date}.html ({count} 项)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
