#!/usr/bin/env python3
import os, re, datetime
from zoneinfo import ZoneInfo

# Config
TZ = ZoneInfo("America/New_York")  # your timezone
BAR_LEN = 10
FILLED = "█"
EMPTY = "░"

def bar(pct: int) -> str:
    pct = max(0, min(100, int(pct)))
    filled = round(pct * BAR_LEN / 100)
    return f"{FILLED*filled}{EMPTY*(BAR_LEN-filled)} {pct}%"

today = datetime.datetime.now(TZ).date().isoformat()  # YYYY-MM-DD
default_pct = int(os.getenv("DAILY_PERCENT", "0"))    # set via env if you want

row_template = (
    f"| {today} | — | — | — | — | — | {bar(default_pct)} |"
)

START = "<!-- DAILY_TABLE_START -->"
END   = "<!-- DAILY_TABLE_END -->"

with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

if START not in content or END not in content:
    raise SystemExit("Markers <!-- DAILY_TABLE_START/END --> not found in README.md")

head, tail = content.split(START, 1)
table_block, rest = tail.split(END, 1)

# Ensure header exists; if not, create a fresh header
lines = [ln.rstrip() for ln in table_block.strip("\n").splitlines()]
if not any(re.match(r'^\|\s*Day\s*\|', ln) for ln in lines):
    lines = [
        "| Day | Project | OSS | Concept | LeetCode | Reading | Daily Avg |",
        "|-----|---------|-----|---------|----------|---------|-----------|",
    ]

# Already added today?
today_pattern = re.compile(rf'^\|\s*{re.escape(today)}\s*\|')
if any(today_pattern.search(ln) for ln in lines):
    # Nothing to do
    new_block = "\n".join(lines)
else:
    # Insert today's row just under the header separator (line 2)
    if len(lines) >= 2 and lines[1].startswith("|---"):
        new_lines = lines[:2] + [row_template] + lines[2:]
    else:
        new_lines = [lines[0], "|-----|---------|-----|---------|----------|---------|-----------|", row_template] + lines[1:]
    new_block = "\n".join(new_lines)

new_content = head + START + "\n" + new_block + "\n" + END + rest

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Inserted/kept daily row for {today}.")
