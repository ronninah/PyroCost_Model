# gdx_dump_parser.py
import re
import pandas as pd
from pathlib import Path

def parse_gdx_dump(path, names_3=("i","j","m"), name_value="value"):
    """
    Parse gdxdump-style lines like:
      'i1'.'j1'.'truck' 18.3349015238095
    and return a tidy DataFrame with cols i,j,m,value.

    Also works for 2-tuple dumps (e.g., 'j1'.'truck' 62.69) and
    returns cols j,m,value in that case.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")

    # Try 3-tuple first
    pat3 = re.compile(r"'([^']+)'\.'([^']+)'\.'([^']+)'\s+([-+0-9Ee\.]+)")
    rows3 = [m.groups() for m in pat3.finditer(text)]
    if rows3:
        out = pd.DataFrame(rows3, columns=[*names_3, name_value])
        out[name_value] = pd.to_numeric(out[name_value], errors="coerce")
        return out.dropna(subset=[name_value])

    # Fallback: 2-tuple
    pat2 = re.compile(r"'([^']+)'\.'([^']+)'\s+([-+0-9Ee\.]+)")
    rows2 = [m.groups() for m in pat2.finditer(text)]
    if rows2:
        out = pd.DataFrame(rows2, columns=[names_3[1], names_3[2], name_value])  # j,m,value by default
        out[name_value] = pd.to_numeric(out[name_value], errors="coerce")
        return out.dropna(subset=[name_value])

    raise ValueError(f"No parseable rows found in {path}. Check the file content.")


# viz_um_lane_bar.py
import pandas as pd
import matplotlib.pyplot as plt
from gdx_dump_parser import parse_gdx_dump

df = parse_gdx_dump("UM_lane.csv")  # -> i,j,m,value
df["lane"] = df["i"] + "→" + df["j"] + " (" + df["m"] + ")"
dfp = df[["lane","value"]].set_index("lane").sort_values("value")

ax = dfp.plot(kind="bar", legend=False, figsize=(10,4))
ax.set_ylabel("€/t")
ax.set_title("Unit Margin per Lane (UM_lane)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig("UM_lane_bar.png", dpi=200)
plt.show()
