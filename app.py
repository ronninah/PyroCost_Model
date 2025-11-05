import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Biochar Profit (from GAMS CSVs)", layout="wide")
st.title("Biochar Profitability — GAMS Results Visualization")

# Load CSVs (adjust paths if your CSVs are elsewhere)
surf = pd.read_csv("profit_surface.csv").dropna()
curve_d = pd.read_csv("curve_distance.csv")
curve_p = pd.read_csv("curve_price.csv")

# Ensure numeric types
surf = surf.astype({"price_eur_per_t": float, "dist_km": float, "profit_eur": float})
curve_d = curve_d.astype({"dist_km": float, "profit_eur": float})
curve_p = curve_p.astype({"price_eur_per_t": float, "profit_eur": float})

with st.sidebar:
    st.header("Filter range")
    price_min, price_max = float(surf["price_eur_per_t"].min()), float(surf["price_eur_per_t"].max())
    dist_min,  dist_max  = float(surf["dist_km"].min()),          float(surf["dist_km"].max())

    price_range = st.slider("Price range (€/t)", price_min, price_max, (price_min, price_max), step=25.0)
    dist_range  = st.slider("Distance range (km)", dist_min, dist_max, (dist_min, dist_max), step=10.0)

    price_slice = st.slider("Slice price for Profit vs Distance (€/t)",
                            int(price_min), int(price_max), int((price_min+price_max)//2), step=25)
    dist_slice  = st.slider("Slice distance for Profit vs Price (km)",
                            int(dist_min), int(dist_max), int((dist_min+dist_max)//2), step=10)

# Filter for heatmap
surf_f = surf[
    surf["price_eur_per_t"].between(*price_range) &
    surf["dist_km"].between(*dist_range)
]

tab1, tab2, tab3 = st.tabs(["Surface (Price × Distance)", "Profit vs Distance", "Profit vs Price"])

with tab1:
    st.subheader("Profit Surface (from GAMS)")
    fig = px.density_heatmap(
        surf_f, x="price_eur_per_t", y="dist_km", z="profit_eur",
        histfunc="avg", color_continuous_scale="RdYlGn",
        labels={"price_eur_per_t":"Biochar Price (€/t)","dist_km":"Distance (km)","profit_eur":"Profit (€)"}
    )
    # Break-even contour
    fig.add_trace(go.Contour(
        x=surf_f["price_eur_per_t"], y=surf_f["dist_km"], z=surf_f["profit_eur"],
        contours=dict(start=0, end=0, size=1, coloring="lines"),
        showscale=False, line=dict(color="black", width=2), name="Break-even"
    ))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader(f"Profit vs Distance (price = {price_slice} €/t)")
    df = surf[surf["price_eur_per_t"] == price_slice].sort_values("dist_km")
    if df.empty:  # fall back to nearest values if exact not present
        df = surf.iloc[(surf["price_eur_per_t"]-price_slice).abs().argsort()].head(2)
        df = df.sort_values("dist_km")
    fig2 = px.line(df, x="dist_km", y="profit_eur", markers=True,
                   labels={"dist_km":"Distance (km)","profit_eur":"Profit (€)"})
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader(f"Profit vs Price (distance = {dist_slice} km)")
    df2 = surf[surf["dist_km"] == dist_slice].sort_values("price_eur_per_t")
    if df2.empty:
        df2 = surf.iloc[(surf["dist_km"]-dist_slice).abs().argsort()].head(2)
        df2 = df2.sort_values("price_eur_per_t")
    fig3 = px.line(df2, x="price_eur_per_t", y="profit_eur", markers=True,
                   labels={"price_eur_per_t":"Price (€/t)","profit_eur":"Profit (€)"})
    st.plotly_chart(fig3, use_container_width=True)

st.caption("Built from GAMS CSVs. The black contour is the break-even line (profit = 0 €).")
