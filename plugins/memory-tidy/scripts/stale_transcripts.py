#!/usr/bin/env python3
import argparse
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

HOME = Path.home()


def live_session_ids():
    ids = set()
    for f in (HOME / ".claude/sessions").glob("*.json"):
        try:
            data = json.loads(f.read_text())
            os.kill(int(data["pid"]), 0)
            ids.add(data["sessionId"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return ids


def open_files():
    paths = set()
    proc = Path("/proc")
    if not proc.is_dir():
        return paths
    for pid in os.listdir(proc):
        if not pid.isdigit():
            continue
        try:
            for fd in os.listdir(proc / pid / "fd"):
                try:
                    paths.add(os.readlink(proc / pid / "fd" / fd))
                except OSError:
                    pass
        except OSError:
            pass
    return paths


def transcripts():
    for f in (HOME / ".claude/projects").glob("*/*.jsonl"):
        yield "claude", f
    for f in (HOME / ".codex/sessions").rglob("*.jsonl"):
        yield "codex", f


def size_of(path):
    if path.is_dir():
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    return path.stat().st_size


def main():
    ap = argparse.ArgumentParser(description="刪除超過指定時數沒更新的 claude／codex 對話記錄；預設只預覽")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-age-hours", type=float, default=12.0)
    args = ap.parse_args()
    if not (math.isfinite(args.min_age_hours) and args.min_age_hours > 0):
        ap.error("--min-age-hours 必須是大於 0 的有限數字")

    cutoff = time.time() - args.min_age_hours * 3600
    live = live_session_ids()
    busy = open_files()
    totals = {"claude": [0, 0], "codex": [0, 0]}
    emptied = set()
    kept = 0
    failed = 0
    for kind, f in transcripts():
        try:
            if f.stat().st_mtime >= cutoff or f.stem in live or str(f.resolve()) in busy:
                kept += 1
                continue
            side = f.with_suffix("")
            targets = [f] + ([side] if kind == "claude" and side.is_dir() and not side.is_symlink() else [])
            size = sum(size_of(t) for t in targets)
            if args.apply:
                for t in targets:
                    shutil.rmtree(t) if t.is_dir() else t.unlink()
                if kind == "codex":
                    emptied.add(f.parent)
        except OSError as exc:
            failed += 1
            print(f"失敗 {f}：{type(exc).__name__}")
            continue
        totals[kind][0] += 1
        totals[kind][1] += size
    if args.apply:
        root = HOME / ".codex/sessions"
        for d in emptied:
            while d != root:
                try:
                    d.rmdir()
                except OSError:
                    break
                d = d.parent

    verb = "已刪除" if args.apply else "將刪除"
    for kind, (count, size) in totals.items():
        print(f"{verb} {kind} 對話記錄 {count} 份，{size / 1e6:.1f} MB")
    print(f"保留 {kept} 份（未滿 {args.min_age_hours:g} 小時、正在使用或仍有程序開著）；失敗 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
