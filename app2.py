import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Biochar Profitability", layout="wide")

st.title("💰 Biochar Profitability Dashboard")
st.write("Interactive visualization of how **distance** and **biochar price** affect profitability based on your GAMS model outputs.")

# Check where Streamlit is running
st.caption(f"📁 Current working directory: {os.getcwd()}")

# Try to read CSVs from the current folder
try:
    df_surface = pd.read_csv("profit_surface.csv")
    df_dist = pd.read_csv("curve_distance.csv")
    df_price = pd.read_csv("curve_price.csv")
except FileNotFoundError:
    st.error("❌ CSV files not found. Please ensure profit_surface.csv, curve_distance.csv, and curve_price.csv are in the same folder.")
    st.stop()

# --- Sidebar controls ---
st.sidebar.header("Simulation Controls")

price_slider = st.sidebar.slider("Select Biochar Price (€ per ton)", 200, 800, 500, 50)
distance_slider = st.sidebar.slider("Select Transport Distance (km)", 0, 200, 50, 10)

# --- 1️⃣ Surface Chart ---
st.subheader("1️⃣ Profit Surface — Price vs Distance")
fig_surface = px.density_heatmap(
    df_surface,
    x="price_eur_per_t",
    y="dist_km",
    z="profit_eur",
    color_continuous_scale="RdYlGn",
    title="Profit (€) by Biochar Price and Transport Distance",
    labels={"price_eur_per_t": "Biochar Price (€ / ton)", "dist_km": "Distance (km)", "profit_eur": "Profit (€)"}
)
st.plotly_chart(fig_surface, use_container_width=True)

# --- 2️⃣ Profit vs Distance (at selected price) ---
st.subheader(f"2️⃣ Profit vs Distance (at Biochar Price = €{price_slider}/t)")
df_dist_filtered = df_surface[df_surface["price_eur_per_t"] == price_slider]
fig_dist = px.line(
    df_dist_filtered,
    x="dist_km",
    y="profit_eur",
    markers=True,
    title=f"Profit Decline with Distance (Price = €{price_slider}/t)"
)
st.plotly_chart(fig_dist, use_container_width=True)

# --- 3️⃣ Profit vs Price (at selected distance) ---
st.subheader(f"3️⃣ Profit vs Price (at Distance = {distance_slider} km)")
df_price_filtered = df_surface[df_surface["dist_km"] == distance_slider]
fig_price = px.line(
    df_price_filtered,
    x="price_eur_per_t",
    y="profit_eur",
    markers=True,
    title=f"Profit Increase with Price (Distance = {distance_slider} km)"
)
st.plotly_chart(fig_price, use_container_width=True)

st.success("✅ Dashboard loaded successfully!")
