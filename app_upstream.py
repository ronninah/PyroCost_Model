# app_upstream_mini.py
import os, io, re
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Upstream Option B — Minimal Viz", layout="wide")
st.title("🌲 Upstream (Option B) — Minimal, robust visualization")

# ---------- tiny robust CSV reader ----------
def read_small_csv(path):
    if not os.path.exists(path):
        return None
    # try common separators
    for kw in (dict(sep=","), dict(sep=";"), dict(delim_whitespace=True)):
        try:
            df = pd.read_csv(path, **kw)
            if df is not None and df.shape[1] >= 2:
                return df
        except Exception:
            pass
    # last resort: normalize whitespace to commas
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()
    lines = [re.sub(r"[ \t]+", ",", ln.strip()) for ln in txt.splitlines() if ln.strip()]
    try:
        return pd.read_csv(io.StringIO("\n".join(lines)))
    except Exception:
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
be_raw = read_small_csv("BE_radius.csv")

UM = tidy_um(um_raw)
BE = tidy_be(be_raw)

if UM.empty:
    st.error("UM_lane.csv not found or empty. Ensure you dumped it (format=csv is best).")
    st.stop()

# ---------- sidebar: mode filter if available ----------
modes = sorted(UM["m"].unique())
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

with st.expander("💡 Tips"):
    st.write("""
- If a chart is empty, standardize dumps in GAMS:

