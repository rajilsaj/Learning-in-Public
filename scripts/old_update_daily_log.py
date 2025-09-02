#!/usr/bin/env python3
import json, re, sys, datetime
from pathlib import Path

README = Path("README.md")
INPUT  = Path("daily/input.json")
CONFIG = Path("daily/config.json")

START = "<!-- DAILY_TABLE_START -->"
END   = "<!-- DAILY_TABLE_END -->"

# Defaults (overridable via daily/config.json)
CFG = {
    "weights": {"project":20, "oss":20, "concept":20, "leetcode":20, "reading":20},
    "leetcode_target": 3,
    "timezone": "America/New_York",
    "bar_len": 10,
    "filled_char": "█",
    "empty_char": "░",
    "mode": "merge"  # merge | replace | multirow
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

def progress_bar(pct, bar_len, filled_char, empty_char):
    pct = max(0, min(100, int(round(pct))))
    filled = round(pct * bar_len / 100)
    return f"{filled_char*filled}{empty_char*(bar_len-filled)} {pct}%"

def presence_score(value, weight):
    txt = ""
    if isinstance(value, dict):
        txt = json.dumps(value, ensure_ascii=False)
    elif value is None:
        txt = ""
    else:
        txt = str(value).strip()
    return weight if txt and txt != "—" else 0

def leetcode_score(items, weight, target):
    count = len(items) if isinstance(items, list) else 0
    if target <= 0:
        return weight if count > 0 else 0
    frac = min(max(count / target, 0), 1)
    return weight * frac

def reading_score(reading, weight):
    if isinstance(reading, dict):
        done = reading.get("chapters_done") or reading.get("pages_done")
        target = reading.get("chapters_target") or reading.get("pages_target")
        if isinstance(done, (int, float)) and isinstance(target, (int, float)) and target > 0:
            frac = min(max(float(done) / float(target), 0), 1)
            return weight * frac
        return presence_score(reading, weight)
    else:
        return presence_score(reading, weight)

# ---------- Markdown helpers ----------

def split_row_cells(row_line: str):
    # "| a | b | c |" -> ["a","b","c"]
    parts = [c.strip() for c in row_line.strip().split("|")]
    return [c for c in parts if c != ""][1:-1] if parts and parts[0] == "" else [c for c in parts if c]

def parse_table_block(table_block: str):
    lines = [ln.rstrip() for ln in table_block.strip("\n").splitlines()]
    return lines

def find_row_index_for_date(lines, date):
    pat = re.compile(rf"^\|\s*{re.escape(date)}\s*\|")
    for i, ln in enumerate(lines):
        if pat.search(ln):
            return i
    return -1

def parse_leetcode_cell(cell: str):
    """Return list of {'title':..., 'link':...} from the cell."""
    if "details" not in cell and "Problems" not in cell:
        return []
    items = []
    # Matches "n. [Title](link)"
    for m in re.finditer(r"\d+\.\s*\[([^\]]+)\]\(([^)]+)\)", cell):
        items.append({"title": m.group(1).strip(), "link": m.group(2).strip()})
    # Matches "n. Title" (no link)
    # Split on <br> and scan plain entries too
    for part in re.split(r"(?:<br>|</?details>|</?summary>)", cell):
        m = re.match(r"\s*\d+\.\s+([^\[][^<]+)\s*$", part or "")
        if m:
            title = m.group(1).strip()
            if not any(x["title"] == title for x in items):
                items.append({"title": title, "link": ""})
    return items

def mk_leetcode_md(details):
    if not details:
        return "—"
    lines = []
    for i, item in enumerate(details, 1):
        t = item.get("title", f"Problem {i}")
        l = item.get("link", "")
        lines.append(f"{i}. [{t}]({l})" if l else f"{i}. {t}")
    return f"<details><summary>{len(details)} Problems</summary> " + " <br> ".join(lines) + " </details>"

def merge_str_cell(old: str, new: str) -> str:
    old = (old or "").strip()
    new = (new or "").strip()
    if not new or new == "—":
        return old or "—"
    if not old or old == "—":
        return new
    # append with bullet on a new line within the cell
    return f"{old} <br> • {new}"

def merge_leetcode(old_list, new_list):
    out = []
    seen = set()
    def key(x):
        link = (x.get("link") or "").strip()
        title = (x.get("title") or "").strip()
        return (link.lower(), title.lower())
    for src in (old_list or []):
        k = key(src); 
        if k not in seen:
            seen.add(k); out.append({"title":src.get("title",""), "link":src.get("link","")})
    for src in (new_list or []):
        k = key(src); 
        if k not in seen:
            seen.add(k); out.append({"title":src.get("title",""), "link":src.get("link","")})
    return out

# ---------- Build/merge row data ----------

def build_row_from_data(data, merged_leetcode=None, merged_reading=None):
    date = data.get("date", "auto")
    if str(date).lower() == "auto":
        date = today_str(CFG["timezone"])

    project = data.get("project", "—") or "—"
    oss = data.get("oss", "—") or "—"
    concept = data.get("concept", "—") or "—"
    leetcode = merged_leetcode if merged_leetcode is not None else data.get("leetcode", [])
    reading = merged_reading if merged_reading is not None else data.get("reading", "—")

    # Compute % from merged values
    w = CFG["weights"]
    total = 0
    total += presence_score(project, w["project"])
    total += presence_score(oss,     w["oss"])
    total += presence_score(concept, w["concept"])
    total += leetcode_score(leetcode, w["leetcode"], CFG["leetcode_target"])
    total += reading_score(reading,   w["reading"])
    pct = max(0, min(100, round(total)))

    # Render cells
    leetcode_md = mk_leetcode_md(leetcode)
    if isinstance(reading, dict):
        reading_title = reading.get("title") or reading.get("link") or "—"
    else:
        reading_title = reading or "—"

    bar = progress_bar(pct, CFG["bar_len"], CFG["filled_char"], CFG["empty_char"])
    row_line = f"| {date} | {project} | {oss} | {concept} | {leetcode_md} | {reading_title} | {bar} |"
    return date, row_line

def upsert_row(table_block: str, date: str, new_row_line: str) -> str:
    lines = parse_table_block(table_block)
    header = "| Day | Project | OSS | Concept | LeetCode | Reading | Daily Avg |"
    divider = "|-----|---------|-----|---------|----------|---------|-----------|"
    if not any(re.match(r"^\|\s*Day\s*\|", ln) for ln in lines):
        lines = [header, divider]

    idx = find_row_index_for_date(lines, date)

    mode = CFG.get("mode", "merge")
    if mode == "multirow":
        # Always insert a fresh row under divider
        insert_pos = 2 if len(lines) >= 2 and lines[1].startswith("|---") else len(lines)
        new_lines = lines[:]
        if insert_pos >= len(new_lines):  # append if header only
            if len(new_lines) < 2:
                new_lines = [header, divider]
            new_lines.append(new_row_line)
        else:
            new_lines = new_lines[:insert_pos] + [new_row_line] + new_lines[insert_pos:]
        return "\n".join(new_lines)

    # replace/merge: replace the specific line
    if idx >= 0:
        lines[idx] = new_row_line
    else:
        # insert under divider if present
        if len(lines) >= 2 and lines[1].startswith("|---"):
            lines = lines[:2] + [new_row_line] + lines[2:]
        else:
            lines = [header, divider, new_row_line] + [ln for ln in lines if ln.strip() and not ln.startswith(header)]
    return "\n".join(lines)

def main():
    global CFG
    CFG.update(load_json(CONFIG, {}))  # allow mode/weights overrides

    if not README.exists():
        sys.exit("README.md not found.")
    data = load_json(INPUT, {"date":"auto","project":"—","oss":"—","concept":"—","leetcode":[],"reading":"—"})

    # Determine date first
    date = data.get("date", "auto")
    if str(date).lower() == "auto":
        date = today_str(CFG["timezone"])

    content = README.read_text(encoding="utf-8")
    if START not in content or END not in content:
        sys.exit("Markers not found. Add <!-- DAILY_TABLE_START --> and <!-- DAILY_TABLE_END --> to README.md.")

    head, tail = content.split(START, 1)
    table_block, rest = tail.split(END, 1)
    lines = parse_table_block(table_block)
    idx = find_row_index_for_date(lines, date)

    # Parse existing row (if present) for MERGE mode
    merge_mode = CFG.get("mode", "merge") == "merge"
    prev_cells = None
    if merge_mode and idx >= 0:
        prev_cells = split_row_cells(lines[idx])  # ["Day","Project","OSS","Concept","LeetCode","Reading","Avg"]
        if len(prev_cells) < 7:
            prev_cells = None

    # Build merged values
    if prev_cells:
        # Cells: 0 Day | 1 Project | 2 OSS | 3 Concept | 4 LC | 5 Reading | 6 Avg
        old_project = prev_cells[1]
        old_oss     = prev_cells[2]
        old_concept = prev_cells[3]
        old_lc_cell = prev_cells[4]
        old_reading = prev_cells[5]

        new_project = merge_str_cell(old_project, data.get("project", "—"))
        new_oss     = merge_str_cell(old_oss,     data.get("oss", "—"))
        new_concept = merge_str_cell(old_concept, data.get("concept", "—"))

        old_lc_list = parse_leetcode_cell(old_lc_cell)
        new_lc_list = data.get("leetcode", [])
        # normalize new lc items (strings → dicts)
        norm_new_lc = []
        for it in (new_lc_list or []):
            if isinstance(it, dict):
                norm_new_lc.append({"title": it.get("title","").strip(), "link": (it.get("link") or "").strip()})
            else:
                norm_new_lc.append({"title": str(it).strip(), "link": ""})
        merged_lc = merge_leetcode(old_lc_list, norm_new_lc)

        # reading: allow dict in input; otherwise merge strings
        in_reading = data.get("reading", "—")
        if isinstance(in_reading, dict):
            merged_reading = in_reading  # prefer numeric progress
            reading_title = in_reading.get("title") or in_reading.get("link") or "—"
            # also merge display text so previous string isn't lost
            if old_reading and old_reading != "—" and reading_title and reading_title != old_reading:
                merged_reading["title"] = merge_str_cell(old_reading, reading_title)
        else:
            merged_reading = merge_str_cell(old_reading, in_reading)

        # assemble a merged data view to compute %
        merged_data = {
            "date": date,
            "project": new_project,
            "oss": new_oss,
            "concept": new_concept,
            "leetcode": merged_lc,
            "reading": merged_reading
        }
        _, new_row_line = build_row_from_data(merged_data,
                                            merged_leetcode=merged_lc,
                                            merged_reading=merged_reading)
        date_key = date
    else:
        # no previous row or not in merge mode → compute from input only
        date_key, new_row_line = build_row_from_data(data)

    new_table = upsert_row(table_block, date_key, new_row_line)
    README.write_text(head + START + "\n" + new_table + "\n" + END + rest, encoding="utf-8")
    print(f"Updated Daily Log for {date_key} (mode={CFG.get('mode','merge')}).")

if __name__ == "__main__":
    main()
