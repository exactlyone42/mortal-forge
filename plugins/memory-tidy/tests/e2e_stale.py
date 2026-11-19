import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

scripts = Path(__file__).resolve().parent.parent / "scripts"
home = Path(tempfile.mkdtemp())
old = time.time() - 30 * 3600
proj = home / ".claude/projects/-p"
day = home / ".codex/sessions/2026/11/01"
proj.mkdir(parents=True)
day.mkdir(parents=True)
(home / ".claude/sessions").mkdir()
files = {n: proj / f"{n}.jsonl" for n in ("old", "new", "open")}
files["codex_old"] = day / "rollout-old.jsonl"
files["codex_new"] = day / "rollout-new.jsonl"
for name, f in files.items():
    f.write_text("x")
    if "new" not in name:
        os.utime(f, (old, old))
(proj / "old").mkdir()
(proj / "old/sub.txt").write_text("y")
holder = subprocess.Popen([sys.executable, "-c", f"f=open({str(files['open'])!r});import time;time.sleep(60)"])
time.sleep(1)


def run(*args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, "-I", str(scripts / "stale_transcripts.py"), *args], capture_output=True, text=True, env=env).stdout


def fail(msg, out):
    holder.kill()
    print("FAIL:", msg, "\n", out)
    sys.exit(1)


out = run()
if not all(f.exists() for f in files.values()) or "將刪除 claude 對話記錄 1 份" not in out or "將刪除 codex 對話記錄 1 份" not in out:
    fail("preview must count 1+1 and delete nothing", out)
out = run("--min-age-hours", "99")
if "將刪除 claude 對話記錄 0 份" not in out:
    fail("age threshold must keep everything", out)
out = run("--apply")
gone = [n for n, f in files.items() if not f.exists()]
if sorted(gone) != ["codex_old", "old"] or (proj / "old").exists():
    fail(f"only old files may go, got {gone}", out)
if not files["open"].exists() or not files["new"].exists() or not files["codex_new"].exists():
    fail("open or recent file was deleted", out)
holder.kill()
print("OK", out.strip().splitlines()[-1])
