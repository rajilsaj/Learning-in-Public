#!/usr/bin/env python3
import json, re, sys, datetime
from pathlib import Path

# --- Config ---
TZ = "America/New_York"
BAR_LEN = 10
FILLED = "█"
EMPTY = "░"
README = Path("README.md")
INPUT = Path("daily/input.json")
START = "<!-- DAILY_TABLE_START -->"
END = "<!-- DAILY_TABLE_END -->"

def today_str():
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(TZ)
        return datetime.datetime.now(tz).date().isoformat()
    except Exception:
        # Fallback to system local date if zoneinfo unavailable
        return datetime.date.today().isoformat()

def progress_bar(pct: int) -> str:
    try:
        pct = int(pct)
    except Exception:
        pct = 0
    pct = max(0, min(100, pct))
    filled = round(pct * BAR_LEN / 100)
    return f"{FILLED*filled}{EMPTY*(BAR_LEN - filled)} {pct}%"

def mk_leetcode(details):
    if not isinstance(details, list) or len(details) == 0:
        return "—"
    lines = []
    for i, item in enumerate(details, 1):
        title = item.get("title", f"Problem {i}")
        link = item.get("link", "")
        if link:
            lines.append(f"{i}. [{title}]({link})")
        else:
            lines.append(f"{i}. {title}")
    summary = f"{len(details)} Problems"
    # <details> works inside GitHub tables
    return f"<details><summary>{summary}</summary> " + " <br> ".join(lines) + " </details>"

def build_row(d):
    date = d.get("date", "auto")
    if str(date).lower() == "auto":
        date = today_str()
    project = d.get("project", "—") or "—"
    oss = d.get("oss", "—") or "—"
    concept = d.get("concept", "—") or "—"
    reading = d.get("reading", "—") or "—"
    leetcode = mk_leetcode(d.get("leetcode", []))
    bar = progress_bar(d.get("percent", 0))
    return date, f"| {date} | {project} | {oss} | {concept} | {leetcode} | {reading} | {bar} |"

def upsert_row(table_block: str, new_row_date: str, new_row_line: str) -> str:
    lines = [ln.rstrip() for ln in table_block.strip("\n").splitlines()]

    # Ensure header exists
    if not any(re.match(r"^\|\s*Day\s*\|", ln) for ln in lines):
        lines = [
            "| Day | Project | OSS | Concept | LeetCode | Reading | Daily Avg |",
            "|-----|---------|-----|---------|----------|---------|-----------|",
        ]

    # Replace if today's row exists
    pat = re.compile(rf"^\|\s*{re.escape(new_row_date)}\s*\|")
    for i, ln in enumerate(lines):
        if pat.search(ln):
            lines[i] = new_row_line
            break
    else:
        # Insert under divider (index 1) if present
        if len(lines) >= 2 and re.match(r"^\|[-\s|]+\|$", lines[1]):
            lines = lines[:2] + [new_row_line] + lines[2:]
        else:
            # Reconstruct header properly if malformed
            hdr = "| Day | Project | OSS | Concept | LeetCode | Reading | Daily Avg |"
            div = "|-----|---------|-----|---------|----------|---------|-----------|"
            lines = [hdr, div, new_row_line] + [ln for ln in lines if ln.strip() and not ln.startswith(hdr)]

    return "\n".join(lines)

def main():
    if not README.exists():
        sys.exit("README.md not found.")

    # Load input (if missing, create a minimal default)
    if INPUT.exists():
        data = json.loads(INPUT.read_text(encoding="utf-8"))
    else:
        data = {"date": "auto", "project": "—", "oss": "—", "concept": "—", "leetcode": [], "reading": "—", "percent": 0}

    date, row_line = build_row(data)

    content = README.read_text(encoding="utf-8")
    if START not in content or END not in content:
        sys.exit("Markers not found. Add <!-- DAILY_TABLE_START --> and <!-- DAILY_TABLE_END --> to README.md.")

    head, tail = content.split(START, 1)
    table_block, rest = tail.split(END, 1)

    new_table = upsert_row(table_block, date, row_line)
    new_content = head + START + "\n" + new_table + "\n" + END + rest

    README.write_text(new_content, encoding="utf-8")
    print(f"Updated Daily Log for {date}.")

if __name__ == "__main__":
    main()
