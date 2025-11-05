# app_from_csv.py
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Biochar Profit (from GAMS CSVs)", layout="wide")
st.title("💰 Biochar Profitability — GAMS CSV Visualization")

# ---------- Load CSVs ----------
def load_csv(name, required_cols):
    if not os.path.exists(name):
        st.error(f"Missing file: {name}")
        st.stop()
    df = pd.read_csv(name)
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"{name} is missing columns: {missing}")
        st.stop()
    return df

surf = load_csv("profit_surface.csv", ["price_eur_per_t", "dist_km", "profit_eur"])
curve_d = load_csv("curve_distance.csv", ["dist_km", "profit_eur"])
curve_p = load_csv("curve_price.csv", ["price_eur_per_t", "profit_eur"])

# ensure numeric types
for col in ["price_eur_per_t", "dist_km", "profit_eur"]:
    surf[col] = pd.to_numeric(surf[col], errors="coerce")
surf = surf.dropna()

# Build a pivot matrix for the heatmap / slices
pivot_full = (
    surf.pivot(index="dist_km", columns="price_eur_per_t", values="profit_eur")
        .sort_index(axis=0)
        .sort_index(axis=1)
)

# Discrete grids (exact values available in the CSV)
price_vals = list(pivot_full.columns.astype(float))
dist_vals  = list(pivot_full.index.astype(float))

# derive steps (fallback to 1 if single value)
def step(values):
    if len(values) < 2:
        return 1
    diffs = sorted(set(round(values[i+1]-values[i], 10) for i in range(len(values)-1)))
    return int(diffs[0]) if diffs[0].is_integer() else float(diffs[0])

price_step = step(price_vals)
dist_step  = step(dist_vals)

# ---------- Sidebar controls ----------
st.sidebar.header("Controls")

# --- Heatmap filter ranges (use floats consistently) ---
price_min, price_max = float(price_vals[0]), float(price_vals[-1])
dist_min,  dist_max  = float(dist_vals[0]),  float(dist_vals[-1])

price_range = st.sidebar.slider(
    "Heatmap price range (€/t)",
    min_value=price_min,
    max_value=price_max,
    value=(price_min, price_max),
    step=float(price_step),
)

dist_range = st.sidebar.slider(
    "Heatmap distance range (km)",
    min_value=dist_min,
    max_value=dist_max,
    value=(dist_min, dist_max),
    step=float(dist_step),
)

# Slice selectors must use values that exist in the CSV
price_slice = st.sidebar.select_slider(
    "Slice price for Profit vs Distance (€/t)", options=price_vals,
    value=price_vals[len(price_vals)//2]
)
dist_slice = st.sidebar.select_slider(
    "Slice distance for Profit vs Price (km)", options=dist_vals,
    value=dist_vals[len(dist_vals)//2]
)

# ---------- Filtered pivot for heatmap ----------
# Keep only rows/cols inside selected ranges
pivot_hm = pivot_full.loc[
    [d for d in dist_vals if dist_range[0] <= d <= dist_range[1]],
    [p for p in price_vals if price_range[0] <= p <= price_range[1]],
]

tab1, tab2, tab3 = st.tabs(
    ["Surface (Price × Distance)", "Profit vs Distance", "Profit vs Price"]
)

# ---------- 1) Heatmap with break-even contour ----------
with tab1:
    st.subheader("Profit Surface (from GAMS CSVs)")
    if pivot_hm.empty:
        st.warning("No cells in the selected range.")
    else:
        fig = px.imshow(
            pivot_hm.values,
            x=pivot_hm.columns,
            y=pivot_hm.index,
            origin="lower",
            aspect="auto",
            color_continuous_scale="RdYlGn",
            labels=dict(x="Biochar Price (€/t)", y="Distance (km)", color="Profit (€)")
        )
        # Break-even contour (profit = 0 €) using only CSV data
        fig.add_trace(go.Contour(
            x=pivot_hm.columns,
            y=pivot_hm.index,
            z=pivot_hm.values,
            contours=dict(start=0, end=0, size=1, coloring="lines"),
            showscale=False,
            line=dict(color="black", width=3),
            name="Break-even (Profit = 0 €)"
        ))
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ---------- 2) Profit vs Distance (at selected price) ----------
with tab2:
    st.subheader(f"Profit vs Distance (Price = €{price_slice:.0f}/t)")
    if price_slice not in pivot_full.columns:
        st.warning("Selected price not in CSV grid.")
    else:
        s_dist = pivot_full.loc[:, price_slice]  # column (index → distance)
        s_dist = s_dist.sort_index()
        fig2 = px.line(
            x=s_dist.index, y=s_dist.values, markers=True,
            labels={"x":"Distance (km)", "y":"Profit (€)"}
        )
        st.plotly_chart(fig2, use_container_width=True)

# ---------- 3) Profit vs Price (at selected distance) ----------
with tab3:
    st.subheader(f"Profit vs Price (Distance = {dist_slice:.0f} km)")
    if dist_slice not in pivot_full.index:
        st.warning("Selected distance not in CSV grid.")
    else:
        s_price = pivot_full.loc[dist_slice, :]  # row (index → price)
        s_price = s_price.sort_index()
        fig3 = px.line(
            x=s_price.index, y=s_price.values, markers=True,
            labels={"x":"Biochar Price (€/t)", "y":"Profit (€)"}
        )
        st.plotly_chart(fig3, use_container_width=True)

st.caption(
    "Built directly from GAMS CSVs. Heatmap shows Profit across Price × Distance. "
    "The black contour is the break-even line (Profit = 0 €). "
    "Slice charts show one-dimensional sensitivities along the selected price or distance."
)
