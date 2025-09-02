#!/usr/bin/env python3
import json, re, sys, datetime
from pathlib import Path

README = Path("README.md")
INPUT  = Path("daily/input.json")
CONFIG = Path("daily/config.json")

START = "<!-- DAILY_TABLE_START -->"
END   = "<!-- DAILY_TABLE_END -->"

# Defaults (can be overridden by daily/config.json)
CFG = {
    "weights": {"project":20, "oss":20, "concept":20, "leetcode":20, "reading":20},
    "leetcode_target": 3,
    "timezone": "America/New_York",
    "bar_len": 10,
    "filled_char": "█",
    "empty_char": "░",
}

def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default

def today_str(tzname):
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tzname)
        return datetime.datetime.now(tz).date().isoformat()
    except Exception:
        return datetime.date.today().isoformat()

def presence_score(value, weight):
    """Full credit if non-empty and not '—'."""
    txt = ""
    if isinstance(value, dict):
        txt = json.dumps(value, ensure_ascii=False)
    elif value is None:
        txt = ""
    else:
        txt = str(value).strip()
    return weight if txt and txt != "—" else 0

def leetcode_score(items, weight, target):
    try:
        count = len(items) if isinstance(items, list) else 0
    except Exception:
        count = 0
    if target <= 0:
        return weight if count > 0 else 0
    frac = min(max(count / target, 0), 1)
    return weight * frac

def reading_score(reading, weight):
    # Allow richer progress, else presence-based.
    if isinstance(reading, dict):
        done = reading.get("chapters_done") or reading.get("pages_done")
        target = reading.get("chapters_target") or reading.get("pages_target")
        if isinstance(done, (int, float)) and isinstance(target, (int, float)) and target > 0:
            frac = min(max(float(done) / float(target), 0), 1)
            return weight * frac
        # fallback to presence
        return presence_score(reading, weight)
    else:
        return presence_score(reading, weight)

def progress_bar(pct, bar_len, filled_char, empty_char):
    pct = max(0, min(100, int(round(pct))))
    filled = round(pct * bar_len / 100)
    return f"{filled_char*filled}{empty_char*(bar_len-filled)} {pct}%"

def mk_leetcode(details):
    if not isinstance(details, list) or len(details) == 0:
        return "—"
    lines = []
    for i, item in enumerate(details, 1):
        if isinstance(item, dict):
            title = item.get("title", f"Problem {i}")
            link = item.get("link", "")
        else:
            title = str(item)
            link = ""
        lines.append(f"{i}. [{title}]({link})" if link else f"{i}. {title}")
    return f"<details><summary>{len(details)} Problems</summary> " + " <br> ".join(lines) + " </details>"

def build_row(data):
    date = data.get("date", "auto")
    if str(date).lower() == "auto":
        date = today_str(CFG["timezone"])

    project = data.get("project", "—") or "—"
    oss = data.get("oss", "—") or "—"
    concept = data.get("concept", "—") or "—"
    leetcode = data.get("leetcode", [])
    reading = data.get("reading", "—")

    w = CFG["weights"]
    total = 0
    total += presence_score(project, w["project"])
    total += presence_score(oss, w["oss"])
    total += presence_score(concept, w["concept"])
    total += leetcode_score(leetcode, w["leetcode"], CFG["leetcode_target"])
    total += reading_score(reading, w["reading"])

    pct = max(0, min(100, round(total)))  # weights sum to 100 by default

    leetcode_md = mk_leetcode(leetcode)
    if isinstance(reading, dict):
        reading_title = reading.get("title") or reading.get("link") or "—"
    else:
        reading_title = reading

    bar = progress_bar(pct, CFG["bar_len"], CFG["filled_char"], CFG["empty_char"])
    row = f"| {date} | {project} | {oss} | {concept} | {leetcode_md} | {reading_title} | {bar} |"
    return date, row

def upsert_row(table_block, date, row_line):
    lines = [ln.rstrip() for ln in table_block.strip("\n").splitlines()]
    header = "| Day | Project | OSS | Concept | LeetCode | Reading | Daily Avg |"
    divider = "|-----|---------|-----|---------|----------|---------|-----------|"

    if not any(re.match(r"^\|\s*Day\s*\|", ln) for ln in lines):
        lines = [header, divider]
    pat = re.compile(rf"^\|\s*{re.escape(date)}\s*\|")
    for i, ln in enumerate(lines):
        if pat.search(ln):
            lines[i] = row_line
            break
    else:
        # insert below header divider
        if len(lines) >= 2 and lines[1].startswith("|---"):
            lines = lines[:2] + [row_line] + lines[2:]
        else:
            lines = [header, divider, row_line] + [ln for ln in lines if ln.strip() and not ln.startswith(header)]
    return "\n".join(lines)

def main():
    global CFG
    # load config overrides
    CFG.update(load_json(CONFIG, {}))

    if not README.exists():
        sys.exit("README.md not found.")
    data = load_json(INPUT, {"date":"auto","project":"—","oss":"—","concept":"—","leetcode":[],"reading":"—"})

    date, row = build_row(data)
    content = README.read_text(encoding="utf-8")
    if START not in content or END not in content:
        sys.exit("Markers not found. Add <!-- DAILY_TABLE_START --> and <!-- DAILY_TABLE_END --> to README.md.")

    head, tail = content.split(START, 1)
    table_block, rest = tail.split(END, 1)

    new_table = upsert_row(table_block, date, row)
    README.write_text(head + START + "\n" + new_table + "\n" + END + rest, encoding="utf-8")
    print(f"Updated Daily Log for {date}.")

if __name__ == "__main__":
    main()
