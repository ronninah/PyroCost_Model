# app_upstream_mini.py
import os, io, re
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Upstream Option B — Minimal Viz", layout="wide")
st.title("🌲 Upstream (Option B) — Minimal, robust visualization")

st.sidebar.caption(f"📁 Working dir: {os.getcwd()}")
st.sidebar.write("📄 Files here:", os.listdir())

# Show first lines as text to confirm encoding/delimiter
def preview_text(path, n=8):
    if os.path.exists(path):
        with open(path, "rb") as fb:
            raw = fb.read(400)
        st.sidebar.write(f"🔎 {path} (first {n} lines, raw bytes length {len(raw)}):")
        with open(path, "r", encoding="utf-8", errors="ignore") as ft:
            st.sidebar.code("\n".join(ft.read().splitlines()[:n]))
    else:
        st.sidebar.write(f"❌ Missing: {path}")

preview_text("UM_lane.csv")
preview_text("BE_radius.csv")

import re, io

def parse_gdxdump_triple_param(path):
    """
    Parse lines like: 'i1'.'j1'.'tractor' 3.14,
    Returns DataFrame with columns: i, j, m, value
    """
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()
    # regex for 'i'.'j'.'m' <number>
    pat = re.compile(r"'([^']+)'\.'([^']+)'\.'([^']+)'\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
    rows = [(a,b,c,float(v)) for (a,b,c,v) in pat.findall(txt)]
    if not rows:
        return None
    import pandas as pd
    df = pd.DataFrame(rows, columns=["i","j","m","value"])
    return df

def parse_gdxdump_double_param(path):
    """
    Parse lines like: 'j1'.'tractor' 27.31,
    Returns DataFrame with columns: j, m, value
    """
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()
    pat = re.compile(r"'([^']+)'\.'([^']+)'\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
    rows = [(a,b,float(v)) for (a,b,v) in pat.findall(txt)]
    if not rows:
        return None
    import pandas as pd
    df = pd.DataFrame(rows, columns=["j","m","value"])
    return df



# ---------- tiny robust CSV reader ----------
def read_small_csv(path):
    """Robust CSV reader for files saved by gdxdump or Excel."""
    if not os.path.exists(path):
        return None
    trials = [
        dict(sep=",", encoding="utf-8"),
        dict(sep=",", encoding="utf-8-sig"),
        dict(sep=";", encoding="utf-8"),
        dict(sep=";", encoding="utf-8-sig"),
        dict(sep=",", encoding="utf-16"),
        dict(sep=";", encoding="utf-16"),
        dict(delim_whitespace=True, encoding="utf-8"),
    ]
    for kw in trials:
        try:
            df = pd.read_csv(path, engine="python", **kw)
            if df is not None and df.shape[0] > 0 and df.shape[1] > 0:
                return df
        except Exception:
            pass
    # Last resort: convert whitespace to commas and parse
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()
    lines = [re.sub(r"[ \t]+", ",", ln.strip()) for ln in txt.splitlines() if ln.strip()]
    try:
        df = pd.read_csv(io.StringIO("\n".join(lines)))
        if df.shape[0] > 0:
            return df
    except Exception:
        return None
    return None

VALUE_NAMES = {"value","val","level","lev","data","vals"}

def coerce_value_col(df):
    cols = list(df.columns)
    lower = {c: c.lower() for c in cols}
    # preferred aliases
    for c in cols:
        if lower[c] in VALUE_NAMES:
            return df.rename(columns={c: "value"})
    # pick last numeric as value
    num = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if num:
        return df.rename(columns={num[-1]: "value"})
    # try coercion then retry
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="ignore")
    num = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if num:
        return df.rename(columns={num[-1]: "value"})
    # fallback: last column
    return df.rename(columns={cols[-1]: "value"})

def tidy_um(df):
    """Normalize UM_lane to columns: i, j, (optional m), value."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["i","j","m","value"])
    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    df = coerce_value_col(df)

    # ensure i/j exist; map first two non-value columns to i/j if needed
    base = [c for c in df.columns if c != "value"]
    if "i" not in df.columns and len(base) > 0:
        df = df.rename(columns={base[0]:"i"})
    if "j" not in df.columns and len(base) > 1:
        df = df.rename(columns={base[1]:"j"})
    # mode optional; if missing, create single bucket
    if "m" not in df.columns:
        df["m"] = "all"

    # keep only needed
    keep = [c for c in ["i","j","m","value"] if c in df.columns]
    out = df[keep].copy()
    # clean labels
    for c in [c for c in ["i","j","m"] if c in out.columns]:
        out[c] = out[c].astype(str).str.strip().str.replace("'", "", regex=False)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["value"])
    return out

def tidy_be(df):
    """Normalize BE_radius to j, m, value (accept j,value or m,value too)."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["j","m","value"])
    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    df = coerce_value_col(df)
    base = [c for c in df.columns if c != "value"]
    if "j" not in df.columns and len(base) > 0:
        df = df.rename(columns={base[0]:"j"})
    if "m" not in df.columns:
        df["m"] = "all"
    out = df[["j","m","value"]].copy()
    for c in ["j","m"]:
        out[c] = out[c].astype(str).str.strip().str.replace("'", "", regex=False)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    return out.dropna(subset=["value"])

# ---------- load the tiny CSVs ----------
um_raw = read_small_csv("UM_lane.csv")
if um_raw is None or um_raw.shape[0] == 0:
    # fallback: parse gdxdump text like the preview you showed
    um_raw = parse_gdxdump_triple_param("UM_lane.csv")

be_raw = read_small_csv("BE_radius.csv")
if be_raw is None or be_raw.shape[0] == 0:
    be_raw = parse_gdxdump_double_param("BE_radius.csv")

UM = tidy_um(um_raw)
BE = tidy_be(be_raw)

if UM.empty:
    st.error("UM_lane.csv not found or empty. Ensure you dumped it (format=csv is best).")
    st.stop()

# ---------- sidebar: mode filter if available ----------
modes = sorted(UM["m"].unique()) if "m" in UM.columns else ["all"]
sel_mode = st.sidebar.selectbox("Mode", modes, index=0)
UMf = UM[UM["m"] == sel_mode] if "m" in UM.columns else UM

# ---------- Heatmap: Unit Margin €/t by farm × plant ----------
st.subheader(f"Unit Margin (€/t) — mode: {sel_mode}")
hm = UMf.pivot(index="i", columns="j", values="value").sort_index(axis=0).sort_index(axis=1)
fig = px.imshow(
    hm.values,
    x=hm.columns, y=hm.index, origin="upper", aspect="auto",
    color_continuous_scale="RdYlGn",
    labels=dict(x="Plant j", y="Farm i", color="UM (€/t)")
)
st.plotly_chart(fig, use_container_width=True)

# ---------- Bars: Break-even radius (if available) ----------
st.subheader("Break-even radius (km) by plant")
if not BE.empty:
    fig2 = px.bar(
        BE, x="j", y="value", color="m",
        labels={"j":"Plant", "value":"Break-even radius (km)", "m":"Mode"},
        barmode="group"
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No BE_radius.csv found — skipping break-even chart.")

# ---------- Tips: markdown + code (no triple quotes) ----------
with st.expander("💡 Tips"):
    st.markdown(
        "- If a chart is empty, standardize dumps in GAMS (comma separator, dot decimals, full header)."
    )
    st.code(
        "$call gdxdump excel_out.gdx symb=UM_lane    format=csv decimal=dot separator=comma header=full > UM_lane.csv\n"
        "$call gdxdump excel_out.gdx symb=BE_radius  format=csv decimal=dot separator=comma header=full > BE_radius.csv",
        language="bash",
    )
    st.markdown(
        "- This app auto-detects the numeric value column (`value`/`level`/`val`) and handles both `i,j,value` and `i,j,m,value` shapes."
    )
