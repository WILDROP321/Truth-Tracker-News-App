import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

def run(script_name: str):
    path = os.path.join(ROOT, script_name)
    if not os.path.exists(path):
        raise SystemExit(f"Missing script: {path}")

    print(f"\n🚀 Running {script_name}...")
    proc = subprocess.run([sys.executable, path], capture_output=True, text=True)

    if proc.returncode != 0:
        print(f"❌ {script_name} failed (exit {proc.returncode})")
        if proc.stdout:
            print("\n--- stdout ---\n" + proc.stdout)
        if proc.stderr:
            print("\n--- stderr ---\n" + proc.stderr)
        raise SystemExit(proc.returncode)

    print(f"✅ {script_name} completed.")
    if proc.stdout.strip():
        print(proc.stdout)

def main():
    print("\n===============================")
    print("🌍 WORLD MOOD CRON JOB STARTED")
    print("🕒", datetime.now().isoformat(timespec="seconds"))
    print("===============================\n")

    # 1) Fetch RSS → news_articles.json
    run("main.py")

    # 2) Score with AI → news_articles_scored.json
    # If you kept the updated scorer as analysis_updated.py, rename it to analysis.py
    # OR change this line to run("analysis_updated.py")
    run("analysis.py")

    # 3) Build icons once (only if missing)
    if not os.path.exists(os.path.join(ROOT, "news_icons.json")):
        run("Get_News_Icons.py")
    else:
        print("\nℹ️ news_icons.json already exists. Skipping icon build.")

    print("\n===============================")
    print("✅ WORLD MOOD PIPELINE COMPLETE")
    print("===============================\n")

if __name__ == "__main__":
    main()