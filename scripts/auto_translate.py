#!/usr/bin/env python3
"""Free machine-translation pass for 夜秣 git 副业雷达 — no API key.

Strategy
--------
* Pure-English description -> translate the whole sentence (better fluency).
* Mixed Chinese/English description -> split into sentences, translate only the
  English ones, keep the existing Chinese untouched.

Providers are free public endpoints (Google's gtx endpoint, then MyMemory).

Honesty: the result is stored as *machine* translation (``_src = "mt"``,
``_auto = True``). `zh_state` therefore reports "rule", so the report keeps its
机器直译 chip and never claims a model refined it.

Usage: python auto_translate.py <skill-dir> [--out DIR] [--theme T] [--no-render]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
CJK = re.compile(r"[\u4e00-\u9fff]")
# Split after every CJK terminator, and after an ASCII terminator only when a
# space follows (so "3.5" and "e.g." stay intact).
SENT = re.compile(r"(?<=[。！？])|(?<=[.!?])\s+|\n+")


def _get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", "replace")


def _google(text: str) -> str:
    q = urllib.parse.quote(text)
    raw = _get(
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=en&tl=zh-CN&dt=t&q={q}"
    )
    data = json.loads(raw)
    return "".join(seg[0] for seg in (data[0] or []) if seg and seg[0]).strip()


def _mymemory(text: str) -> str:
    q = urllib.parse.quote(text[:480])
    raw = _get(f"https://api.mymemory.translated.net/get?q={q}&langpair=en|zh-CN")
    return ((json.loads(raw).get("responseData") or {}).get("translatedText") or "").strip()


PROVIDERS = (("google", _google), ("mymemory", _mymemory))


def _score(text: str) -> tuple[int, int]:
    """Fewer leftover English words is better; more Chinese is better."""
    words = re.findall(r"[A-Za-z]{3,}", text or "")
    return (len(words), -len(CJK.findall(text or "")))


def translate_text(text: str) -> str:
    """Translate one English chunk; keep the candidate with least leftover English."""
    best, best_key = "", None
    for name, fn in PROVIDERS:
        try:
            out = fn(text)
        except Exception as exc:  # noqa: BLE001 - provider hiccups are routine
            print(f"    [{name}] {type(exc).__name__}")
            continue
        if not out or not CJK.search(out):
            continue
        key = _score(out)
        if best_key is None or key < best_key:
            best, best_key = out, key
        if key[0] == 0:
            break
    return best


def translate_desc(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if not CJK.search(text):
        return translate_text(text)
    out = []
    for chunk in [c.strip() for c in SENT.split(text) if c and c.strip()]:
        if CJK.search(chunk):
            out.append(chunk)
            continue
        if len(re.findall(r"[A-Za-z]{3,}", chunk)) < 2:
            out.append(chunk)
            continue
        zh = translate_text(chunk)
        out.append(zh or chunk)
        time.sleep(0.4)
    return " ".join(out).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir")
    ap.add_argument("--out", default="")
    ap.add_argument("--theme", default="")
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    skill = pathlib.Path(args.skill_dir).resolve()
    sys.path.insert(0, str(skill / "scripts"))
    import analy  # noqa: PLC0415
    import radar  # noqa: PLC0415

    last = skill / "data" / "last_picks.json"
    if not last.exists():
        print(f"missing {last}")
        return 1
    payload = json.loads(last.read_text(encoding="utf-8"))

    rows = list(payload.get("picks") or [])
    for bucket in ((payload.get("focus_tab") or {}).get("buckets") or {}).values():
        rows += bucket

    done = 0
    for row in rows:
        if not analy.needs_translate(row):
            continue
        analyze = dict(row.get("analy") or {})
        source = analyze.get("en") or row.get("desc") or ""
        zh = translate_desc(source)
        if not zh:
            continue
        analyze["zh"] = zh
        analyze["plain"] = analy.to_plain(zh, row.get("form", ""))
        analyze["_auto"] = True   # still the machine lane, not a model refinement
        analyze["_src"] = "mt"
        row["analy"] = analyze
        done += 1
        print(f"  {row.get('full_name')}: {zh[:52]}")
        time.sleep(0.4)

    last.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"translated {done} item(s)")

    if args.no_render:
        return 0

    # `_ensure_analy` normally recomputes every field for machine rows. Keep the
    # machine translation we just wrote instead of throwing it away.
    original_ensure = radar._ensure_analy

    def ensure_analy(row):
        if (row.get("analy") or {}).get("_src") == "mt":
            return
        original_ensure(row)

    radar._ensure_analy = ensure_analy
    radar.cmd_render(argparse.Namespace(out=args.out, theme=args.theme))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
