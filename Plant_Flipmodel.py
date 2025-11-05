# Plant_Flipmodel.py
# Streamlit tool to visualize plant-first payable curves (j1)
# - Distance vs payable (as-received & DM) + BE points
# - Payable vs biochar price + BE radius per mode
# Works from CSVs OR recomputes from parameters to let you tweak values on the fly.

import os
import math
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

# -----------------------
# Page config
# -----------------------
st.set_page_config(page_title="Plant-first payable (j1)", layout="wide")

st.title("Plant-first Payable & BE Radius — j1")
st.caption("Interactive visuals. Load CSVs from GAMS or recompute using the same formulas.")

# -----------------------
# Defaults (brochure & constants)
# -----------------------
DEFAULTS = dict(
    Qin_DM_h=0.299,     # t DM/h
    Y_char=0.25,        # t char / t DM
    E_elec_kW=130.0,    # kW
    E_heat_kW=200.0,    # kWth
    Hop_year=8000.0,    # h/yr
    P_char=600.0,       # €/t (biochar)
    P_el=0.11,          # €/kWh
    P_heat=0.06,        # €/kWh_th
    n_ops=1.0,          # operators/shift
    w_hour=28.0,        # €/h
    OM_hour=30.0,       # €/h
    P_buy=0.28,         # €/kWh (import elec, if any)
    E_buy_kWh=0.0,      # kWh/h imported
    MarginTarget=0.0,   # €/h target
    MC_asrec=0.35,      # fraction
    # KTBL-style blocks (as in your GAMS)
    Tractor_eur_h=41.84,
    PTOChipper_eur_h=22.63,
    Body_Tractor_eur_t=0.82,
    SemiTrailer_eur_t=0.89,
    Bucket_eur_t=0.39,
    FrontLoader_eur_h=8.68,
    Tractor_speed_kmh=40.0,
    Chipper_m3_h=25.0,
    BulkDensity_t_m3=0.30,
    Handling_tph=20.0,
    Truck_speed_kmh=70.0,
    PayloadTruck_t=25.0,
    Backhaul=2.0,
    IncludeLabor=1.0,
    IncludeChipOp=1.0,
    IncludeLoader=1.0,
    IncludeDriver=1.0,
    AddLaborToTruckTkm=1.0,
    WageBase_eur_h=12.82,
    OncostFrac=0.22,
    C_tkm_truck_mach=0.12
)

WORKDIR = os.path.dirname(__file__)
CSV_DISTANCE = os.path.join(WORKDIR, "distance_payable_curve_j1.csv")
CSV_PCHAR    = os.path.join(WORKDIR, "payable_vs_biochar_j1.csv")

# -----------------------
# Sidebar: data source and parameters
# -----------------------
st.sidebar.header("Data Source")
# Default FALSE so the plots respond to your sliders by recomputing
use_csv_distance = st.sidebar.checkbox("Load distance/payable CSV", value=False)
use_csv_pchar    = st.sidebar.checkbox("Load payable vs biochar CSV", value=False)

st.sidebar.header("Plant & Market (brochure)")
P_char = st.sidebar.number_input("Biochar price P_char (€/t)", min_value=0.0, step=10.0, value=float(DEFAULTS["P_char"]))
P_el   = st.sidebar.number_input("Electricity price P_el (€/kWh)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_el"]))
P_heat = st.sidebar.number_input("Heat price P_heat (€/kWh_th)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_heat"]))
MC_asrec = st.sidebar.slider("Moisture content of chips (as-received)", 0.0, 0.6, float(DEFAULTS["MC_asrec"]), 0.01)
MarginTarget = st.sidebar.number_input("Target plant margin (€/h)", value=float(DEFAULTS["MarginTarget"]), step=10.0)

st.sidebar.header("Operations")
Qin_DM_h = st.sidebar.number_input("Intake capacity Qin_DM_h (t DM/h)", min_value=0.0, step=0.001, value=float(DEFAULTS["Qin_DM_h"]), format="%.3f")
Y_char   = st.sidebar.number_input("Char yield (t/t DM)", min_value=0.0, max_value=1.0, step=0.01, value=float(DEFAULTS["Y_char"]))
E_elec   = st.sidebar.number_input("Net electricity (kW)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_elec_kW"]))
E_heat   = st.sidebar.number_input("Net heat (kW)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_heat_kW"]))
Hop_year = st.sidebar.number_input("Operating hours (h/yr)", min_value=0.0, step=100.0, value=float(DEFAULTS["Hop_year"]))

st.sidebar.header("OPEX")
n_ops   = st.sidebar.number_input("Operators per shift", min_value=0.0, step=1.0, value=float(DEFAULTS["n_ops"]))
w_hour  = st.sidebar.number_input("Wage (€/h)", min_value=0.0, step=0.5, value=float(DEFAULTS["w_hour"]))
OM_hour = st.sidebar.number_input("O&M (€/h)", min_value=0.0, step=1.0, value=float(DEFAULTS["OM_hour"]))
P_buy   = st.sidebar.number_input("Import elec price (€/kWh)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_buy"]))
E_buy   = st.sidebar.number_input("Import elec (kWh/h)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_buy_kWh"]))

st.sidebar.header("KTBL-like Transport/Handling")
Backhaul = st.sidebar.selectbox("Backhaul factor", [1.0, 2.0], index=1)  # you wanted two-way
Tractor_speed = st.sidebar.number_input("Tractor speed (km/h)", 1.0, 200.0, float(DEFAULTS["Tractor_speed_kmh"]))
Truck_speed   = st.sidebar.number_input("Truck speed (km/h)",   1.0, 200.0, float(DEFAULTS["Truck_speed_kmh"]))
PayloadTruck  = st.sidebar.number_input("Truck payload (t)", 1.0, 60.0, float(DEFAULTS["PayloadTruck_t"]))
BulkDensity   = st.sidebar.number_input("Loose bulk density (t/m³)", 0.1, 1.0, float(DEFAULTS["BulkDensity_t_m3"]), step=0.01)
chip_box_m3   = st.sidebar.number_input("Chip box volume (m³) for tractor", 1.0, 60.0, 22.0, step=1.0)

# labor toggles
IncludeLabor = st.sidebar.checkbox("Include labor", value=True)
IncludeChipOp = st.sidebar.checkbox("Include chipper operator", value=True)
IncludeLoader = st.sidebar.checkbox("Include loader operator", value=True)
IncludeDriver = st.sidebar.checkbox("Include driver", value=True)
AddLaborToTruckTkm = st.sidebar.checkbox("Add driver labor to truck t-km", value=True)

WageBase = float(DEFAULTS["WageBase_eur_h"])
OncostFrac = float(DEFAULTS["OncostFrac"])
Wage_eur_h = WageBase * (1 + OncostFrac)

# fixed KTBL-like machine prices (keep as constants, you can expose later if you want)
Tractor_eur_h = float(DEFAULTS["Tractor_eur_h"])
PTOChipper_eur_h = float(DEFAULTS["PTOChipper_eur_h"])
Body_Tractor_eur_t = float(DEFAULTS["Body_Tractor_eur_t"])
SemiTrailer_eur_t = float(DEFAULTS["SemiTrailer_eur_t"])
Bucket_eur_t = float(DEFAULTS["Bucket_eur_t"])
FrontLoader_eur_h = float(DEFAULTS["FrontLoader_eur_h"])
Chipper_m3_h = float(DEFAULTS["Chipper_m3_h"])
Handling_tph = float(DEFAULTS["Handling_tph"])
C_tkm_truck_mach = float(DEFAULTS["C_tkm_truck_mach"])

# -----------------------
# Helper: recompute from parameters
# -----------------------
def compute_payable_and_costs():
    # revenues & non-feedstock costs
    Qchar_h = Y_char * Qin_DM_h
    Rchar = P_char * Qchar_h
    Rel   = P_el * E_elec
    Rheat = P_heat * E_heat
    Rev   = Rchar + Rel + Rheat

    Clab = n_ops * w_hour
    Com  = OM_hour
    Cbuy = P_buy * E_buy

    # payable €/t DM at plant gate
    P_chip_payable_DM = (Rev - (Clab + Com + Cbuy) - MarginTarget) / max(1e-9, Qin_DM_h)
    P_chip_payable_asrec = P_chip_payable_DM * (1 - MC_asrec)

    # chipping & handling
    C_chip_eurt_mach = (Tractor_eur_h + PTOChipper_eur_h) / max(1e-9, Chipper_m3_h * BulkDensity)
    C_hand_eurt_mach = Bucket_eur_t + FrontLoader_eur_h / max(1e-9, Handling_tph)
    Labor_chip_hpt   = 1.0 / max(1e-9, Chipper_m3_h * BulkDensity)
    Labor_hand_hpt   = 1.0 / max(1e-9, Handling_tph)

    C_chip_eurt = C_chip_eurt_mach + (Wage_eur_h * Labor_chip_hpt if (IncludeLabor and IncludeChipOp) else 0.0)
    C_handle_eurt = C_hand_eurt_mach + (Wage_eur_h * Labor_hand_hpt if (IncludeLabor and IncludeLoader) else 0.0)

    # t-km costs
    PayloadTractor = chip_box_m3 * BulkDensity
    C_tkm_tractor = (Tractor_eur_h / max(1e-9, Tractor_speed * PayloadTractor)) \
                    + ((Wage_eur_h if (IncludeLabor and IncludeDriver) else 0.0) / max(1e-9, Tractor_speed * PayloadTractor))
    C_tkm_truck = C_tkm_truck_mach + ((Wage_eur_h if (IncludeLabor and IncludeDriver and AddLaborToTruckTkm) else 0.0) / max(1e-9, Truck_speed * PayloadTruck))

    # BE radius by mode (km one-way)
    BE_trac = max(0.0, (P_chip_payable_DM - (C_chip_eurt + C_handle_eurt + Body_Tractor_eur_t)) / max(1e-9, Backhaul * C_tkm_tractor))
    BE_truck = max(0.0, (P_chip_payable_DM - (C_chip_eurt + C_handle_eurt + SemiTrailer_eur_t)) / max(1e-9, Backhaul * C_tkm_truck))

    kpis = dict(
        P_chip_payable_DM=P_chip_payable_DM,
        P_chip_payable_asrec=P_chip_payable_asrec,
        BE_radius_tractor=BE_trac,
        BE_radius_truck=BE_truck,
        PayableBudget_yr=P_chip_payable_DM * Qin_DM_h * Hop_year,
        CharOutput_yr=Y_char * Qin_DM_h * Hop_year,
        Qin_asrec_yr=Qin_DM_h * Hop_year / max(1e-9, (1 - MC_asrec)),
        C_chip_eurt=C_chip_eurt,
        C_handle_eurt=C_handle_eurt,
        C_tkm_tractor=C_tkm_tractor,
        C_tkm_truck=C_tkm_truck
    )
    return kpis

kpis = compute_payable_and_costs()

# -----------------------
# Section 1: Distance vs payable line (recompute OR load CSV)
# -----------------------
st.subheader("1) Delivered Cost vs Distance, and Payable Line (as-received)")

colA, colB = st.columns([2,1])
with colB:
    st.markdown("**Options**")
    max_km = st.number_input("Max distance (km)", min_value=10, max_value=300, value=200, step=10)
    km_step = st.number_input("Step (km)", min_value=1, max_value=50, value=1, step=1)
    show_dm = st.checkbox("Show payable €/t DM", value=False)
    show_asrec = st.checkbox("Show payable €/t as-received", value=True)
    show_modes = st.multiselect("Show modes", ["tractor","truck"], default=["tractor","truck"], key="modes_distance")

# Prepare data
if use_csv_distance and os.path.exists(CSV_DISTANCE):
    df_dist = pd.read_csv(CSV_DISTANCE)
    required_cols = {"km","mode","cost_asrec_eurpt","payable_asrec_eurpt","is_be"}
    if not required_cols.issubset(set(df_dist.columns)):
        use_csv_distance = False
else:
    use_csv_distance = False

if not use_csv_distance:
    # Recompute grid using current parameters
    kms = np.arange(0, max_km+km_step, km_step, dtype=float)
    rows = []
    # delivered cost per t (as-received) = (machine+labor chipping+handling) * (1-MC) + Backhaul*C_tkm*km*(1-MC)
    for mode in ["tractor","truck"]:
        C_surcharge = Body_Tractor_eur_t if mode=="tractor" else SemiTrailer_eur_t
        C_tkm_mode = kpis["C_tkm_tractor"] if mode=="tractor" else kpis["C_tkm_truck"]
        for d in kms:
            cost_asrec = ((kpis["C_chip_eurt"] + kpis["C_handle_eurt"] + C_surcharge) * (1 - MC_asrec)) \
                         + (Backhaul * C_tkm_mode * d * (1 - MC_asrec))
            rows.append({
                "km": d,
                "mode": mode,
                "cost_asrec_eurpt": cost_asrec,
                "payable_asrec_eurpt": kpis["P_chip_payable_asrec"]
            })
    df_dist = pd.DataFrame(rows)
    # BE per mode: closest to payable line
    df_dist["is_be"] = 0
    for mode in df_dist["mode"].unique():
        sub = df_dist[df_dist["mode"]==mode].copy()
        sub["diff"] = (sub["cost_asrec_eurpt"] - sub["payable_asrec_eurpt"]).abs()
        be_km = float(sub.loc[sub["diff"].idxmin(), "km"])
        df_dist.loc[(df_dist["mode"]==mode) & (df_dist["km"]==be_km), "is_be"] = 1

with colA:
    # Payable line(s)
    pay_layers = []
    if show_asrec:
        pay_layers.append(
            alt.Chart(df_dist.drop_duplicates(subset=["km"]))
            .mark_line(strokeDash=[6,3])
            .encode(
                x=alt.X("km:Q", title="Distance from plant (km)"),
                y=alt.Y("payable_asrec_eurpt:Q", title="€/t (as-received)"),
                tooltip=["km","payable_asrec_eurpt"]
            )
        )
    if show_dm:
        pay_layers.append(
            alt.Chart(pd.DataFrame({"km": [df_dist["km"].min(), df_dist["km"].max()],
                                    "payable_dm": [kpis["P_chip_payable_DM"]]*2}))
            .mark_line()
            .encode(
                x="km:Q",
                y=alt.Y("payable_dm:Q", title="€/t (DM)"),
                tooltip=["km","payable_dm"]
            )
        )
    payable_chart = alt.layer(*pay_layers).properties(height=240) if pay_layers else alt.Chart().properties(height=240)

    # Delivered cost lines per mode
    df_modes = df_dist[df_dist["mode"].isin(show_modes)]
    cost_chart = (
        alt.Chart(df_modes)
        .mark_line()
        .encode(
            x=alt.X("km:Q", title="Distance from plant (km)"),
            y=alt.Y("cost_asrec_eurpt:Q", title="Delivered cost (€/t as-received)"),
            color=alt.Color("mode:N", title="Mode"),
            tooltip=["km","mode","cost_asrec_eurpt"]
        )
        .properties(height=240)
    )

    # BE points
    be_points = (
        alt.Chart(df_modes[df_modes["is_be"]==1])
        .mark_point(size=80)
        .encode(
            x="km:Q",
            y="cost_asrec_eurpt:Q",
            color=alt.Color("mode:N", legend=None),
            tooltip=["km","mode","cost_asrec_eurpt"]
        )
    )

    chart1 = alt.vconcat(payable_chart, cost_chart + be_points, spacing=8)
    st.altair_chart(chart1, use_container_width=True)

st.info(
    f"Computed @ P_char={P_char:.0f} €/t, P_el={P_el:.2f} €/kWh, P_heat={P_heat:.2f} €/kWh_th, MC={MC_asrec:.2f}. "
    f"Payable: {kpis['P_chip_payable_DM']:.2f} €/t DM ({kpis['P_chip_payable_asrec']:.2f} €/t as-received). "
    f"BE radius: tractor {kpis['BE_radius_tractor']:.1f} km, truck {kpis['BE_radius_truck']:.1f} km."
)

# -----------------------
# Section 2: Payable vs biochar price (grid) + BE radius per mode
# -----------------------
st.subheader("2) Payable vs Biochar Price (€/t) and Break-Even Radius")

col1, col2 = st.columns([2,1])
with col2:
    st.markdown("**Grid options**")
    dP = st.number_input("Step ΔP_char (€/t)", min_value=1, max_value=500, value=50, step=1)
    points = st.slider("# of points", min_value=5, max_value=25, value=11, step=2)
    modes_for_grid = st.multiselect("Show modes", ["tractor","truck"], default=["tractor","truck"], key="modes_biochar")

# Prepare data
if use_csv_pchar and os.path.exists(CSV_PCHAR):
    df_pchar = pd.read_csv(CSV_PCHAR)
    required_cols = {"Pchar_eurpt","Pchip_pay_DM_eurptDM","Pchip_pay_asrec_eurpt","BE_radius_tractor_km","BE_radius_truck_km"}
    if not required_cols.issubset(set(df_pchar.columns)):
        use_csv_pchar = False
else:
    use_csv_pchar = False

if not use_csv_pchar:
    # recompute grid centered at current P_char
    idxs = np.arange(points) - (points//2)
    Pchar_grid = P_char + idxs * dP

    C_surch_trac = Body_Tractor_eur_t
    C_surch_truck = SemiTrailer_eur_t
    rows = []
    for Pc in Pchar_grid:
        # revenues (hourly)
        R_el_h = P_el * E_elec
        R_ht_h = P_heat * E_heat
        Rev_h  = Pc * (Y_char * Qin_DM_h) + R_el_h + R_ht_h
        # payable €/t DM
        pay_DM = (Rev_h - (n_ops*w_hour + OM_hour + P_buy*E_buy) - MarginTarget) / max(1e-9, Qin_DM_h)
        pay_asrec = pay_DM * (1 - MC_asrec)
        # t-km
        PayloadTractor = chip_box_m3 * BulkDensity
        C_tkm_tractor = (Tractor_eur_h / max(1e-9, Tractor_speed * PayloadTractor)) \
                        + ((Wage_eur_h if (IncludeLabor and IncludeDriver) else 0.0) / max(1e-9, Tractor_speed * PayloadTractor))
        C_tkm_truck = C_tkm_truck_mach + ((Wage_eur_h if (IncludeLabor and IncludeDriver and AddLaborToTruckTkm) else 0.0) / max(1e-9, Truck_speed * PayloadTruck))
        # chipping+handling €/t DM
        C_chip_eurt_mach = (Tractor_eur_h + PTOChipper_eur_h) / max(1e-9, Chipper_m3_h * BulkDensity)
        C_hand_eurt_mach = Bucket_eur_t + FrontLoader_eur_h / max(1e-9, Handling_tph)
        Labor_chip_hpt   = 1.0 / max(1e-9, Chipper_m3_h * BulkDensity)
        Labor_hand_hpt   = 1.0 / max(1e-9, Handling_tph)
        C_chip_eurt = C_chip_eurt_mach + (Wage_eur_h * Labor_chip_hpt if (IncludeLabor and IncludeChipOp) else 0.0)
        C_handle_eurt = C_hand_eurt_mach + (Wage_eur_h * Labor_hand_hpt if (IncludeLabor and IncludeLoader) else 0.0)

        BE_trac = max(0.0, (pay_DM - (C_chip_eurt + C_handle_eurt + C_surch_trac)) / max(1e-9, Backhaul*C_tkm_tractor))
        BE_truck = max(0.0, (pay_DM - (C_chip_eurt + C_handle_eurt + C_surch_truck)) / max(1e-9, Backhaul*C_tkm_truck))

        rows.append({
            "Pchar_eurpt": Pc,
            "Pchip_pay_DM_eurptDM": pay_DM,
            "Pchip_pay_asrec_eurpt": pay_asrec,
            "BE_radius_tractor_km": BE_trac,
            "BE_radius_truck_km": BE_truck
        })
    df_pchar = pd.DataFrame(rows)

with col1:
    # Upper chart: payable vs biochar price (DM + as-received)
    pay_lines = []
    pay_lines.append(
        alt.Chart(df_pchar)
        .mark_line()
        .encode(
            x=alt.X("Pchar_eurpt:Q", title="Biochar selling price (€/t)"),
            y=alt.Y("Pchip_pay_DM_eurptDM:Q", title="Payable (€/t DM) / (€/t as-received)"),
            tooltip=["Pchar_eurpt","Pchip_pay_DM_eurptDM"]
        )
    )
    pay_lines.append(
        alt.Chart(df_pchar)
        .mark_line(strokeDash=[6,3])
        .encode(
            x="Pchar_eurpt:Q",
            y=alt.Y("Pchip_pay_asrec_eurpt:Q", title=None),
            tooltip=["Pchar_eurpt","Pchip_pay_asrec_eurpt"]
        )
    )
    top = alt.layer(*pay_lines).properties(height=230)

    # Lower chart: BE radius vs biochar price (long format for multiple modes)
    radius_df = df_pchar.melt(
        id_vars=["Pchar_eurpt"],
        value_vars=["BE_radius_tractor_km","BE_radius_truck_km"],
        var_name="mode",
        value_name="radius_km"
    )
    if modes_for_grid:
        radius_df = radius_df[radius_df["mode"].isin([f"BE_radius_{m}_km" for m in modes_for_grid])]

    bottom = (
        alt.Chart(radius_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Pchar_eurpt:Q", title="Biochar selling price (€/t)"),
            y=alt.Y("radius_km:Q", title="Break-even radius (km)"),
            color=alt.Color("mode:N", title="Mode"),
            tooltip=["Pchar_eurpt","mode","radius_km"]
        )
        .properties(height=230)
    )

    chart2 = alt.vconcat(top, bottom, spacing=12)
    st.altair_chart(chart2, use_container_width=True)

# -----------------------
# Download current frames (optional)
# -----------------------
st.download_button("Download distance/payable CSV (current)", data=df_dist.to_csv(index=False), file_name="distance_payable_curve_j1_live.csv", mime="text/csv")
st.download_button("Download payable vs biochar CSV (current)", data=df_pchar.to_csv(index=False), file_name="payable_vs_biochar_j1_live.csv", mime="text/csv")

# -----------------------
# KPIs panel
# -----------------------
st.subheader("Key KPIs (computed)")
kpi_cols = st.columns(3)
kpi_cols[0].metric("Payable @ gate (€/t DM)", f"{kpis['P_chip_payable_DM']:.2f}")
kpi_cols[1].metric("Payable @ gate (€/t as-received)", f"{kpis['P_chip_payable_asrec']:.2f}")
kpi_cols[2].metric("Char output (t/yr)", f"{kpis['CharOutput_yr']:.0f}")
kpi_cols = st.columns(3)
kpi_cols[0].metric("BE radius tractor (km)", f"{kpis['BE_radius_tractor']:.1f}")
kpi_cols[1].metric("BE radius truck (km)", f"{kpis['BE_radius_truck']:.1f}")
kpi_cols[2].metric("As-received intake needed (t/yr)", f"{kpis['Qin_asrec_yr']:.0f}")
