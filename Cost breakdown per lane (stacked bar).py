import re
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# -------- CONFIG --------
dump_file = Path("UC_lane.csv")   # your gdxdump output (not a true CSV)
# ------------------------

if not dump_file.exists():
    raise FileNotFoundError(f"File not found: {dump_file.resolve()}")

# Read raw text (tolerate non-UTF8 glyphs like the mangled euro sign)
text = dump_file.read_text(encoding="utf-8", errors="ignore")

# Regex to capture lines like:  'i1'.'j1'.'truck' 18.3349015238095
# It will also handle an optional trailing "/;" at the end of the last line
pat = re.compile(r"'([^']+)'\.'([^']+)'\.'([^']+)'\s+([-+0-9Ee\.]+)")

rows = []
for line in text.splitlines():
    line = line.strip()
    if not line or line.startswith("Parameter "):
        continue
    # remove possible "/;" at line end
    line = line.replace("/;", "").strip()
    m = pat.search(line)
    if m:
        i, j, mde, val = m.groups()
        try:
            val = float(val)
        except ValueError:
            continue
        rows.append((i, j, mde, val))

if not rows:
    raise ValueError(
        "No data rows parsed. Make sure the file format matches the screenshot "
        "('i'.'j'.'mode' <number> per line)."
    )

df = pd.DataFrame(rows, columns=["i", "j", "m", "value"])

# Build lane label like i1→j1 (truck)
df["lane"] = df["i"] + "→" + df["j"] + " (" + df["m"] + ")"

# Sort by value and plot
df_plot = df[["lane", "value"]].set_index("lane").sort_values("value")

ax = df_plot.plot(kind="bar", legend=False, figsize=(9, 4))
ax.set_ylabel("€/t")
ax.set_title("Unit Cost per Lane (UC_lane)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()

# If you want a tidy CSV for later reuse:
df.to_csv("UC_lane_tidy.csv", index=False)
print("Wrote tidy data to UC_lane_tidy.csv")
