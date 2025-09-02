## How the “Daily Avg” Progress Is Calculated

The daily percentage is computed from five buckets (default total = 100%):
- **Project** (20%) — full credit if non-empty for the day, else 0.
- **Open Source** (20%) — full credit if non-empty, else 0.
- **Concept/Notes** (20%) — full credit if non-empty, else 0.
- **LeetCode** (20%) — proportional to solved count: `min(solved / target, 1) × 20`. Default target = **3**.
- **Reading** (20%)  
  - If numeric progress is provided (e.g., `chapters_done/chapters_target` or `pages_done/pages_target`), uses `min(done / target, 1) × 20`.  
  - Otherwise presence-based (non-empty = full 20, empty = 0).

**Total %** = rounded sum of all bucket scores, clamped to `[0, 100]`.

**Progress bar**: with a fixed length (default `10`),  
`filled = round(percent × bar_len / 100)`  
Bar = `█` repeated `filled` + `░` repeated `(bar_len − filled)`, followed by `" percent%"`.

**Example**  
- Project ✅ (20) + OSS ✅ (20) + Concept ❌ (0)  
- LeetCode: 2 solved / target 3 → `20 × (2/3) ≈ 13.3`  
- Reading ✅ (20)  
Total ≈ `20 + 20 + 0 + 13.3 + 20 = 73.3 → 73%` → `███████░░░ 73%`.

**Config (in `daily/config.json`)**  
- `weights` per bucket, `leetcode_target`, `bar_len`, `filled_char`, `empty_char`, `timezone`, and `mode` (`merge`/`replace`/`multirow`).

// merge or multirow
