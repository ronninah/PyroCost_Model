# Plant_Flipmodel_viz.py
# Streamlit app for Plant-first payable analysis Pyropower GmbH
# - Distance vs payable (as-received & DM) + BE points
# - Payable vs biochar price + BE radius (modes)
# - Heatmap + 3D surface (BE radius vs P_char & MC)
# - Cost breakdown (stacked bars at chosen distance)

import os
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

try:
    import plotly.graph_objects as go  # for 3D surface (optional)
    PLOTLY_OK = True
except Exception:
    PLOTLY_OK = False

# -----------------------
# Page config
# -----------------------
st.set_page_config(page_title="Plant-first payable (j1)", layout="wide")
st.title("Plant-first Payable & Break-even Radius — j1")
st.caption("Interactive visuals. Uses your GAMS logic; recomputes instantly from sidebar parameters.")

# -----------------------
# Defaults (brochure & constants)
# -----------------------
DEFAULTS = dict(
    Qin_DM_h=0.299,     # t DM/h
    Y_char=0.25,        # t char / t DM
    E_elec_kW=130.0,    # kW
    E_heat_kW=200.0,    # kWth
    Hop_year=8000.0,    # h/yr
    P_char=550.0,       # €/t (biochar)
    P_el=0.11,          # €/kWh
    P_heat=0.06,        # €/kWh_th
    n_ops=1.0,          # operators/shift
    w_hour=28.0,        # €/h
    OM_hour=30.0,       # €/h
    P_buy=0.28,         # €/kWh (import elec, if any)
    E_buy_kWh=0.0,      # kWh/h imported
    MarginTarget=0.0,   # €/h target
    MC_asrec=0.25,      # fraction

    # KTBL-style blocks
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
# Sidebar
# -----------------------
st.sidebar.header("Data Source")
use_csv_distance = st.sidebar.checkbox("Load distance/payable CSV", value=False, key="csv_distance")
use_csv_pchar    = st.sidebar.checkbox("Load payable vs biochar CSV", value=False, key="csv_pchar")

st.sidebar.header("Plant & Market")
P_char = st.sidebar.number_input("Biochar price P_char (€/t)", min_value=0.0, step=10.0, value=float(DEFAULTS["P_char"]), key="P_char")
P_el   = st.sidebar.number_input("Electricity price P_el (€/kWh)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_el"]), key="P_el")
P_heat = st.sidebar.number_input("Heat price P_heat (€/kWh_th)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_heat"]), key="P_heat")
MC_asrec = st.sidebar.slider("Moisture content of chips (as-received)", 0.0, 0.6, float(DEFAULTS["MC_asrec"]), 0.01, key="MC")
MarginTarget = st.sidebar.number_input("Target plant margin (€/h)", value=float(DEFAULTS["MarginTarget"]), step=10.0, key="margin")

st.sidebar.header("Operations")
Qin_DM_h = st.sidebar.number_input("Intake capacity Qin_DM_h (t DM/h)", min_value=0.0, step=0.001, value=float(DEFAULTS["Qin_DM_h"]), format="%.3f", key="Qin")
Y_char   = st.sidebar.number_input("Char yield (t/t DM)", min_value=0.0, max_value=1.0, step=0.01, value=float(DEFAULTS["Y_char"]), key="Ychar")
E_elec   = st.sidebar.number_input("Net electricity (kW)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_elec_kW"]), key="Eelec")
E_heat   = st.sidebar.number_input("Net heat (kW)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_heat_kW"]), key="Eheat")
Hop_year = st.sidebar.number_input("Operating hours (h/yr)", min_value=0.0, step=100.0, value=float(DEFAULTS["Hop_year"]), key="Hop")

st.sidebar.header("OPEX")
n_ops   = st.sidebar.number_input("Operators per shift", min_value=0.0, step=1.0, value=float(DEFAULTS["n_ops"]), key="ops")
w_hour  = st.sidebar.number_input("Wage (€/h)", min_value=0.0, step=0.5, value=float(DEFAULTS["w_hour"]), key="w")
OM_hour = st.sidebar.number_input("O&M (€/h)", min_value=0.0, step=1.0, value=float(DEFAULTS["OM_hour"]), key="om")
P_buy   = st.sidebar.number_input("Import elec price (€/kWh)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_buy"]), key="pbuy")
E_buy   = st.sidebar.number_input("Import elec (kWh/h)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_buy_kWh"]), key="ebuy")

st.sidebar.header("KTBL Transport/Handling")
Backhaul = st.sidebar.selectbox("Backhaul factor", [1.0, 2.0], index=1, key="backhaul")  # two-way default
Tractor_speed = st.sidebar.number_input("Tractor speed (km/h)", 1.0, 200.0, float(DEFAULTS["Tractor_speed_kmh"]), key="tspeed")
Truck_speed   = st.sidebar.number_input("Truck speed (km/h)",   1.0, 200.0, float(DEFAULTS["Truck_speed_kmh"]), key="trspeed")
PayloadTruck  = st.sidebar.number_input("Truck payload (t)", 1.0, 60.0, float(DEFAULTS["PayloadTruck_t"]), key="payload")
BulkDensity   = st.sidebar.number_input("Loose bulk density (t/m³)", 0.1, 1.0, float(DEFAULTS["BulkDensity_t_m3"]), step=0.01, key="rho")
chip_box_m3   = st.sidebar.number_input("Chip box volume (m³) for tractor", 1.0, 60.0, 22.0, step=1.0, key="box")

# labor toggles
IncludeLabor = st.sidebar.checkbox("Include labor", value=True, key="lab")
IncludeChipOp = st.sidebar.checkbox("Include chipper operator", value=True, key="chipop")
IncludeLoader = st.sidebar.checkbox("Include loader operator", value=True, key="loadop")
IncludeDriver = st.sidebar.checkbox("Include driver", value=True, key="driver")
AddLaborToTruckTkm = st.sidebar.checkbox("Add driver labor to truck t-km", value=True, key="tkmlabor")

# Fixed constants
Tractor_eur_h       = float(DEFAULTS["Tractor_eur_h"])
PTOChipper_eur_h    = float(DEFAULTS["PTOChipper_eur_h"])
Body_Tractor_eur_t  = float(DEFAULTS["Body_Tractor_eur_t"])
SemiTrailer_eur_t   = float(DEFAULTS["SemiTrailer_eur_t"])
Bucket_eur_t        = float(DEFAULTS["Bucket_eur_t"])
FrontLoader_eur_h   = float(DEFAULTS["FrontLoader_eur_h"])
Chipper_m3_h        = float(DEFAULTS["Chipper_m3_h"])
Handling_tph        = float(DEFAULTS["Handling_tph"])
C_tkm_truck_mach    = float(DEFAULTS["C_tkm_truck_mach"])
Wage_eur_h          = float(DEFAULTS["WageBase_eur_h"]) * (1 + float(DEFAULTS["OncostFrac"]))

# -----------------------
# Core computations
# -----------------------
def compute_payable_and_costs():
    # Hourly revenues
    Qchar_h = Y_char * Qin_DM_h
    Rchar   = P_char * Qchar_h
    Rel     = P_el * E_elec
    Rheat   = P_heat * E_heat
    Rev     = Rchar + Rel + Rheat

    # Hourly non-feedstock costs
    Clab = n_ops * w_hour
    Com  = OM_hour
    Cbuy = P_buy * E_buy

    # Payable (EUR/t DM) at plant gate
    P_chip_payable_DM = (Rev - (Clab + Com + Cbuy) - MarginTarget) / max(1e-9, Qin_DM_h)
    P_chip_payable_asrec = P_chip_payable_DM * (1 - MC_asrec)

    # Chipping & handling (EUR/t DM)
    C_chip_eurt_mach = (Tractor_eur_h + PTOChipper_eur_h) / max(1e-9, Chipper_m3_h * BulkDensity)
    C_hand_eurt_mach = Bucket_eur_t + FrontLoader_eur_h / max(1e-9, Handling_tph)
    Labor_chip_hpt   = 1.0 / max(1e-9, Chipper_m3_h * BulkDensity)
    Labor_hand_hpt   = 1.0 / max(1e-9, Handling_tph)

    C_chip_eurt   = C_chip_eurt_mach + (Wage_eur_h * Labor_chip_hpt if (IncludeLabor and IncludeChipOp) else 0.0)
    C_handle_eurt = C_hand_eurt_mach + (Wage_eur_h * Labor_hand_hpt if (IncludeLabor and IncludeLoader) else 0.0)

    # t-km costs
    PayloadTractor = chip_box_m3 * BulkDensity
    C_tkm_tractor = (Tractor_eur_h / max(1e-9, Tractor_speed * PayloadTractor)) \
                  + ((Wage_eur_h if (IncludeLabor and IncludeDriver) else 0.0) / max(1e-9, Tractor_speed * PayloadTractor))
    C_tkm_truck = C_tkm_truck_mach \
                + ((Wage_eur_h if (IncludeLabor and IncludeDriver and AddLaborToTruckTkm) else 0.0) / max(1e-9, Truck_speed * PayloadTruck))

    # BE radius (km, one-way)
    BE_trac  = max(0.0, (P_chip_payable_DM - (C_chip_eurt + C_handle_eurt + Body_Tractor_eur_t)) / max(1e-9, Backhaul * C_tkm_tractor))
    BE_truck = max(0.0, (P_chip_payable_DM - (C_chip_eurt + C_handle_eurt + SemiTrailer_eur_t)) / max(1e-9, Backhaul * C_tkm_truck))

    return dict(
        P_chip_payable_DM=P_chip_payable_DM,
        P_chip_payable_asrec=P_chip_payable_asrec,
        C_chip_eurt=C_chip_eurt,
        C_handle_eurt=C_handle_eurt,
        C_tkm_tractor=C_tkm_tractor,
        C_tkm_truck=C_tkm_truck,
        BE_radius_tractor=BE_trac,
        BE_radius_truck=BE_truck,
        PayableBudget_yr=P_chip_payable_DM * Qin_DM_h * Hop_year,
        CharOutput_yr=Y_char * Qin_DM_h * Hop_year,
        Qin_asrec_yr=Qin_DM_h * Hop_year / max(1e-9, (1 - MC_asrec))
    )

kpis = compute_payable_and_costs()

# -----------------------
# Cached helpers (grids)
# -----------------------
@st.cache_data
def make_distance_grid(max_km, km_step, MC_asrec, kpis, Backhaul,
                       Body_Tractor_eur_t, SemiTrailer_eur_t):
    kms = np.arange(0, max_km + km_step, km_step, dtype=float)
    rows = []
    for mode in ["tractor", "truck"]:
        C_surcharge  = Body_Tractor_eur_t if mode == "tractor" else SemiTrailer_eur_t
        C_tkm_mode   = kpis["C_tkm_tractor"] if mode == "tractor" else kpis["C_tkm_truck"]
        for d in kms:
            cost_asrec = (kpis["C_chip_eurt"] + kpis["C_handle_eurt"] + C_surcharge) \
             + (Backhaul * C_tkm_mode * d)
            rows.append({
                "km": d,
                "mode": mode,
                "cost_asrec_eurpt": cost_asrec,
                "payable_asrec_eurpt": kpis["P_chip_payable_asrec"]
            })
    df = pd.DataFrame(rows)
    df["is_be"] = 0
    for mode in df["mode"].unique():
        sub = df[df["mode"] == mode].copy()
        sub["diff"] = (sub["cost_asrec_eurpt"] - sub["payable_asrec_eurpt"]).abs()
        be_km = float(sub.loc[sub["diff"].idxmin(), "km"])
        df.loc[(df["mode"] == mode) & (df["km"] == be_km), "is_be"] = 1
    return df

@st.cache_data
def make_pchar_grid(P_char, dP, points, params, toggles):
    # params: dict of constants and current values needed
    # toggles: dict of boolean choices for labor, etc.
    idxs = np.arange(points) - (points // 2)
    Pgrid = P_char + idxs * dP
    rows = []
    for Pc in Pgrid:
        # Hourly revenues
        R_el_h = params["P_el"] * params["E_elec"]
        R_ht_h = params["P_heat"] * params["E_heat"]
        Rev_h  = Pc * (params["Y_char"] * params["Qin_DM_h"]) + R_el_h + R_ht_h
        # Payable €/t DM
        pay_DM   = (Rev_h - (params["n_ops"]*params["w_hour"] + params["OM_hour"] + params["P_buy"]*params["E_buy"]) - params["MarginTarget"]) / max(1e-9, params["Qin_DM_h"])
        pay_asrc = pay_DM * (1 - params["MC_asrec"])

        # t-km costs
        PayloadTractor = params["chip_box_m3"] * params["BulkDensity"]
        C_tkm_tractor = (params["Tractor_eur_h"] / max(1e-9, params["Tractor_speed"] * PayloadTractor)) \
                      + ((params["Wage_eur_h"] if (toggles["IncludeLabor"] and toggles["IncludeDriver"]) else 0.0) / max(1e-9, params["Tractor_speed"] * PayloadTractor))
        C_tkm_truck = params["C_tkm_truck_mach"] \
                    + ((params["Wage_eur_h"] if (toggles["IncludeLabor"] and toggles["IncludeDriver"] and toggles["AddLaborToTruckTkm"]) else 0.0) / max(1e-9, params["Truck_speed"] * params["PayloadTruck"]))

        # Chipping + handling €/t DM
        C_chip_eurt_mach = (params["Tractor_eur_h"] + params["PTOChipper_eur_h"]) / max(1e-9, params["Chipper_m3_h"] * params["BulkDensity"])
        C_hand_eurt_mach = params["Bucket_eur_t"] + params["FrontLoader_eur_h"] / max(1e-9, params["Handling_tph"])
        Labor_chip_hpt   = 1.0 / max(1e-9, params["Chipper_m3_h"] * params["BulkDensity"])
        Labor_hand_hpt   = 1.0 / max(1e-9, params["Handling_tph"])

        C_chip_eurt = C_chip_eurt_mach + (params["Wage_eur_h"] * Labor_chip_hpt if (toggles["IncludeLabor"] and toggles["IncludeChipOp"]) else 0.0)
        C_handle_eurt = C_hand_eurt_mach + (params["Wage_eur_h"] * Labor_hand_hpt if (toggles["IncludeLabor"] and toggles["IncludeLoader"]) else 0.0)

        BE_trac = max(0.0, (pay_DM - (C_chip_eurt + C_handle_eurt + params["Body_Tractor_eur_t"])) / max(1e-9, params["Backhaul"]*C_tkm_tractor))
        BE_truck = max(0.0, (pay_DM - (C_chip_eurt + C_handle_eurt + params["SemiTrailer_eur_t"])) / max(1e-9, params["Backhaul"]*C_tkm_truck))

        rows.append({
            "Pchar_eurpt": Pc,
            "Pchip_pay_DM_eurptDM": pay_DM,
            "Pchip_pay_asrec_eurpt": pay_asrc,
            "BE_radius_tractor_km": BE_trac,
            "BE_radius_truck_km": BE_truck
        })
    return pd.DataFrame(rows)

@st.cache_data
def make_be_heatmap(P_char_center, dP, nP, MC_min, MC_max, nMC, base_params, toggles):
    # grid over P_char and MC, compute BE radius for chosen mode
    Ps  = np.linspace(P_char_center - (nP//2)*dP, P_char_center + (nP//2)*dP, nP)
    MCs = np.linspace(MC_min, MC_max, nMC)
    df_rows = []
    for mc in MCs:
        for Pc in Ps:
            # hourly revenues
            R_el_h = base_params["P_el"] * base_params["E_elec"]
            R_ht_h = base_params["P_heat"] * base_params["E_heat"]
            Rev_h  = Pc * (base_params["Y_char"] * base_params["Qin_DM_h"]) + R_el_h + R_ht_h
            pay_DM = (Rev_h - (base_params["n_ops"]*base_params["w_hour"] + base_params["OM_hour"] + base_params["P_buy"]*base_params["E_buy"]) - base_params["MarginTarget"]) / max(1e-9, base_params["Qin_DM_h"])

            # chipping + handling €/t DM
            C_chip_eurt_mach = (base_params["Tractor_eur_h"] + base_params["PTOChipper_eur_h"]) / max(1e-9, base_params["Chipper_m3_h"] * base_params["BulkDensity"])
            C_hand_eurt_mach = base_params["Bucket_eur_t"] + base_params["FrontLoader_eur_h"] / max(1e-9, base_params["Handling_tph"])
            Labor_chip_hpt   = 1.0 / max(1e-9, base_params["Chipper_m3_h"] * base_params["BulkDensity"])
            Labor_hand_hpt   = 1.0 / max(1e-9, base_params["Handling_tph"])

            C_chip_eurt = C_chip_eurt_mach + (base_params["Wage_eur_h"] * Labor_chip_hpt if (toggles["IncludeLabor"] and toggles["IncludeChipOp"]) else 0.0)
            C_handle_eurt = C_hand_eurt_mach + (base_params["Wage_eur_h"] * Labor_hand_hpt if (toggles["IncludeLabor"] and toggles["IncludeLoader"]) else 0.0)

            # t-km for tractor & truck
            PayloadTractor = base_params["chip_box_m3"] * base_params["BulkDensity"]
            C_tkm_tractor = (base_params["Tractor_eur_h"] / max(1e-9, base_params["Tractor_speed"] * PayloadTractor)) \
                          + ((base_params["Wage_eur_h"] if (toggles["IncludeLabor"] and toggles["IncludeDriver"]) else 0.0) / max(1e-9, base_params["Tractor_speed"] * PayloadTractor))
            C_tkm_truck = base_params["C_tkm_truck_mach"] \
                        + ((base_params["Wage_eur_h"] if (toggles["IncludeLabor"] and toggles["IncludeDriver"] and toggles["AddLaborToTruckTkm"]) else 0.0) / max(1e-9, base_params["Truck_speed"] * base_params["PayloadTruck"]))

            BE_trac = max(0.0, (pay_DM - (C_chip_eurt + C_handle_eurt + base_params["Body_Tractor_eur_t"])) / max(1e-9, base_params["Backhaul"]*C_tkm_tractor))
            BE_truck = max(0.0, (pay_DM - (C_chip_eurt + C_handle_eurt + base_params["SemiTrailer_eur_t"])) / max(1e-9, base_params["Backhaul"]*C_tkm_truck))

            df_rows.append(dict(P_char=Pc, MC=mc, BE_trac=BE_trac, BE_truck=BE_truck))
    return pd.DataFrame(df_rows)

# -----------------------
# Tabs
# -----------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Distance View",
    "Price Sensitivity",
    "Heatmap & 3D Surface",
    "Cost Breakdown"
])

# -----------------------
# TAB 1: Distance View
# -----------------------
with tab1:
    st.subheader("1) Delivered Cost vs Distance, and Payable Line (as-received)")
    colA, colB = st.columns([2,1], gap="large")
    with colB:
        st.markdown("**Options**")
        max_km = st.number_input("Max distance (km)", min_value=10, max_value=300, value=200, step=10, key="maxkm")
        km_step = st.number_input("Step (km)", min_value=1, max_value=50, value=1, step=1, key="kmstep")
        show_dm = st.checkbox("Show payable €/t DM", value=False, key="showdm")
        show_asrec = st.checkbox("Show payable €/t as-received", value=True, key="showasrec")
        show_modes_dist = st.multiselect("Show modes", ["tractor","truck"], default=["tractor","truck"], key="modes_distance_tab1")

    # Load or compute distance grid
    if use_csv_distance and os.path.exists(CSV_DISTANCE):
        df_dist = pd.read_csv(CSV_DISTANCE)
        needed = {"km","mode","cost_asrec_eurpt","payable_asrec_eurpt","is_be"}
        if not needed.issubset(df_dist.columns):
            df_dist = make_distance_grid(max_km, km_step, MC_asrec, kpis, Backhaul,
                                         Body_Tractor_eur_t, SemiTrailer_eur_t)
    else:
        df_dist = make_distance_grid(max_km, km_step, MC_asrec, kpis, Backhaul,
                                     Body_Tractor_eur_t, SemiTrailer_eur_t)

    with colA:
        # Payable lines
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
                alt.Chart(pd.DataFrame({"km":[df_dist["km"].min(), df_dist["km"].max()],
                                        "payable_dm":[kpis["P_chip_payable_DM"]]*2}))
                .mark_line()
                .encode(
                    x="km:Q",
                    y=alt.Y("payable_dm:Q", title="€/t (DM)"),
                    tooltip=["km","payable_dm"]
                )
            )
        top = alt.layer(*pay_layers).properties(height=230) if pay_layers else alt.Chart().properties(height=230)

        # Delivered cost lines per mode
        df_modes = df_dist[df_dist["mode"].isin(show_modes_dist)]
        cost_chart = (
            alt.Chart(df_modes)
            .mark_line()
            .encode(
                x=alt.X("km:Q", title="Distance from plant (km)"),
                y=alt.Y("cost_asrec_eurpt:Q", title="Delivered cost (€/t as-received)"),
                color=alt.Color("mode:N", title="Mode"),
                tooltip=["km","mode","cost_asrec_eurpt"]
            )
            .properties(height=260)
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

        st.altair_chart(alt.vconcat(top, cost_chart + be_points, spacing=10), use_container_width=True)

    st.info(
        f"Computed @ P_char={P_char:.0f} €/t, P_el={P_el:.2f} €/kWh, P_heat={P_heat:.2f} €/kWh_th, MC={MC_asrec:.2f}. "
        f"Payable: {kpis['P_chip_payable_DM']:.2f} €/t DM ({kpis['P_chip_payable_asrec']:.2f} €/t as-received). "
        f"BE radius: tractor {kpis['BE_radius_tractor']:.1f} km, truck {kpis['BE_radius_truck']:.1f} km."
    )

    coldl, coldw = st.columns(2)
    with coldl:
        st.download_button(
            "Download distance/payable CSV (current)",
            data=df_dist.to_csv(index=False),
            file_name="distance_payable_curve_j1_live.csv",
            mime="text/csv",
            key="dl_dist"
        )

# -----------------------
# TAB 2: Price Sensitivity
# -----------------------
with tab2:
    st.subheader("2) Payable vs Biochar Price (€/t) and Break-Even Radius")

    col1, col2 = st.columns([2,1], gap="large")
    with col2:
        st.markdown("**Grid options**")
        dP = st.number_input("Step ΔP_char (€/t)", min_value=1, max_value=500, value=50, step=1, key="dP")
        points = st.slider("# of points", min_value=5, max_value=25, value=11, step=2, key="npoints")
        modes_for_grid = st.multiselect("Show modes", ["tractor","truck"], default=["tractor","truck"], key="modes_biochar_tab2")

    if use_csv_pchar and os.path.exists(CSV_PCHAR):
        df_pchar = pd.read_csv(CSV_PCHAR)
        needed = {"Pchar_eurpt","Pchip_pay_DM_eurptDM","Pchip_pay_asrec_eurpt","BE_radius_tractor_km","BE_radius_truck_km"}
        if not needed.issubset(df_pchar.columns):
            use_csv_pchar = False
    if not use_csv_pchar:
        params = dict(
            P_el=P_el, P_heat=P_heat, E_elec=E_elec, E_heat=E_heat,
            Y_char=Y_char, Qin_DM_h=Qin_DM_h, n_ops=n_ops, w_hour=w_hour,
            OM_hour=OM_hour, P_buy=P_buy, E_buy=E_buy, MarginTarget=MarginTarget,
            MC_asrec=MC_asrec,
            Tractor_eur_h=Tractor_eur_h, PTOChipper_eur_h=PTOChipper_eur_h,
            Body_Tractor_eur_t=Body_Tractor_eur_t, SemiTrailer_eur_t=SemiTrailer_eur_t,
            Bucket_eur_t=Bucket_eur_t, FrontLoader_eur_h=FrontLoader_eur_h,
            Tractor_speed=Tractor_speed, Truck_speed=Truck_speed,
            Chipper_m3_h=Chipper_m3_h, BulkDensity=BulkDensity,
            Handling_tph=Handling_tph, PayloadTruck=PayloadTruck,
            C_tkm_truck_mach=C_tkm_truck_mach, Backhaul=Backhaul,
            Wage_eur_h=Wage_eur_h, chip_box_m3=chip_box_m3
        )
        toggles = dict(
            IncludeLabor=IncludeLabor, IncludeChipOp=IncludeChipOp,
            IncludeLoader=IncludeLoader, IncludeDriver=IncludeDriver,
            AddLaborToTruckTkm=AddLaborToTruckTkm
        )
        df_pchar = make_pchar_grid(P_char, dP, points, params, toggles)

    with col1:
        # Payable lines (DM and as-received)
        pay_lines = [
            alt.Chart(df_pchar).mark_line().encode(
                x=alt.X("Pchar_eurpt:Q", title="Biochar price (€/t)"),
                y=alt.Y("Pchip_pay_DM_eurptDM:Q", title="Payable (€/t DM) / (€/t as-received)"),
                tooltip=["Pchar_eurpt","Pchip_pay_DM_eurptDM"]
            ),
            alt.Chart(df_pchar).mark_line(strokeDash=[6,3]).encode(
                x="Pchar_eurpt:Q",
                y=alt.Y("Pchip_pay_asrec_eurpt:Q", title=None),
                tooltip=["Pchar_eurpt","Pchip_pay_asrec_eurpt"]
            )
        ]
        top = alt.layer(*pay_lines).properties(height=230)

        # BE radius vs biochar price
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
                x=alt.X("Pchar_eurpt:Q", title="Biochar price (€/t)"),
                y=alt.Y("radius_km:Q", title="Break-even radius (km)"),
                color=alt.Color("mode:N", title="Mode"),
                tooltip=["Pchar_eurpt","mode","radius_km"]
            )
            .properties(height=230)
        )

        st.altair_chart(alt.vconcat(top, bottom, spacing=12), use_container_width=True)

    st.download_button(
        "Download payable vs biochar CSV (current)",
        data=df_pchar.to_csv(index=False),
        file_name="payable_vs_biochar_j1_live.csv",
        mime="text/csv",
        key="dl_pchar"
    )

# -----------------------
# TAB 3: Heatmap
# -----------------------
with tab3:
    st.subheader("3) Sensitivity Heatmap ")

    colh1, colh2 = st.columns([2,1], gap="large")
    with colh2:
        metric_choice = st.selectbox(
            "Heatmap metric",
            ["Cost gap @ distance (as-received)", "Break-even radius (km, DM basis)"],
            index=0,
            help="Gap = payable_as-received − delivered_cost-as-received at the chosen distance."
        )
        dP_hm  = st.number_input("ΔP_char grid step (€/t)", min_value=5, max_value=200, value=50, step=5, key="hm_dP")
        nP_hm  = st.slider("Points across P_char", min_value=5, max_value=31, value=11, step=2, key="hm_nP")

        MC_min = st.slider("MC min", 0.0, 0.6, 0.15, 0.01, key="hm_mcmin")
        MC_max = st.slider("MC max", 0.0, 0.6, 0.45, 0.01, key="hm_mcmax")
        nMC    = st.slider("MC points", min_value=5, max_value=31, value=11, step=2, key="hm_nmc")

        mode_for_map = st.selectbox("Mode for transport", ["tractor","truck"], index=1, key="hm_mode")

        dist_sel_hm  = st.number_input(
            "Distance for gap (km one-way)",
            min_value=0.0, value=float(max(10.0, kpis["BE_radius_truck"])), step=5.0, key="hm_dist",
            help="Only used when metric = Cost gap. Try BE radius ±20–50 km to see contrast."
        )

    # Base params & toggles
    base = dict(
        P_el=P_el, P_heat=P_heat, E_elec=E_elec, E_heat=E_heat,
        Y_char=Y_char, Qin_DM_h=Qin_DM_h, n_ops=n_ops, w_hour=w_hour,
        OM_hour=OM_hour, P_buy=P_buy, E_buy=E_buy, MarginTarget=MarginTarget,
        Tractor_eur_h=Tractor_eur_h, PTOChipper_eur_h=PTOChipper_eur_h,
        Body_Tractor_eur_t=Body_Tractor_eur_t, SemiTrailer_eur_t=SemiTrailer_eur_t,
        Bucket_eur_t=Bucket_eur_t, FrontLoader_eur_h=FrontLoader_eur_h,
        Tractor_speed=Tractor_speed, Truck_speed=Truck_speed,
        Chipper_m3_h=Chipper_m3_h, BulkDensity=BulkDensity,
        Handling_tph=Handling_tph, PayloadTruck=PayloadTruck,
        C_tkm_truck_mach=C_tkm_truck_mach, Backhaul=Backhaul,
        Wage_eur_h=Wage_eur_h, chip_box_m3=chip_box_m3
    )
    tog = dict(
        IncludeLabor=IncludeLabor, IncludeChipOp=IncludeChipOp,
        IncludeLoader=IncludeLoader, IncludeDriver=IncludeDriver,
        AddLaborToTruckTkm=AddLaborToTruckTkm
    )

    # Grid
    Ps  = np.linspace(P_char - (nP_hm//2)*dP_hm, P_char + (nP_hm//2)*dP_hm, nP_hm)
    MCs = np.linspace(MC_min, MC_max, nMC)

    def delivered_gap_or_be(Pc, mc):
        # payable
        R_el_h = base["P_el"] * base["E_elec"]
        R_ht_h = base["P_heat"] * base["E_heat"]
        Rev_h  = Pc * (base["Y_char"] * base["Qin_DM_h"]) + R_el_h + R_ht_h
        pay_DM = (Rev_h - (base["n_ops"]*base["w_hour"] + base["OM_hour"] + base["P_buy"]*base["E_buy"]) - base["MarginTarget"]) / max(1e-9, base["Qin_DM_h"])
        pay_asrc = pay_DM * (1 - mc)

        # chip/handle (€/t DM → as-rec)
        C_chip_mach = (base["Tractor_eur_h"] + base["PTOChipper_eur_h"]) / max(1e-9, base["Chipper_m3_h"] * base["BulkDensity"])
        C_hand_mach = base["Bucket_eur_t"] + base["FrontLoader_eur_h"] / max(1e-9, base["Handling_tph"])
        L_chip = 1.0 / max(1e-9, base["Chipper_m3_h"] * base["BulkDensity"])
        L_hand = 1.0 / max(1e-9, base["Handling_tph"])
        C_chip_DM = C_chip_mach + (base["Wage_eur_h"] * L_chip if (tog["IncludeLabor"] and tog["IncludeChipOp"]) else 0.0)
        C_hand_DM = C_hand_mach + (base["Wage_eur_h"] * L_hand if (tog["IncludeLabor"] and tog["IncludeLoader"]) else 0.0)

        surcharge = base["Body_Tractor_eur_t"] if mode_for_map=="tractor" else base["SemiTrailer_eur_t"]
        C0_DM = C_chip_DM + C_hand_DM + surcharge
        C0_asrc = C0_DM * (1 - mc)

        # transport €/t as-rec at chosen dist
        payload_trac  = base["chip_box_m3"] * base["BulkDensity"]
        C_tkm_trac  = (base["Tractor_eur_h"] / max(1e-9, base["Tractor_speed"] * payload_trac)) \
                    + ((base["Wage_eur_h"] if (tog["IncludeLabor"] and tog["IncludeDriver"]) else 0.0) / max(1e-9, base["Tractor_speed"] * payload_trac))
        C_tkm_truck = base["C_tkm_truck_mach"] \
                    + ((base["Wage_eur_h"] if (tog["IncludeLabor"] and tog["IncludeDriver"] and tog["AddLaborToTruckTkm"]) else 0.0) / max(1e-9, base["Truck_speed"] * base["PayloadTruck"]))
        C_tkm_mode  = C_tkm_trac if mode_for_map=="tractor" else C_tkm_truck

        if metric_choice.startswith("Cost gap"):
            C_trans_asrc = base["Backhaul"] * C_tkm_mode * dist_sel_hm * (1 - mc)
            gap = pay_asrc - (C0_asrc + C_trans_asrc)
            return gap
        else:
            denom = max(1e-9, base["Backhaul"] * C_tkm_mode)
            be_km = max(0.0, (pay_DM - C0_DM) / denom)   # DM basis
            return be_km

    rows = []
    for mc in MCs:
        for Pc in Ps:
            rows.append({"P_char": np.round(Pc, 3), "MC": np.round(mc, 3), "value": delivered_gap_or_be(Pc, mc)})

    df_map = pd.DataFrame(rows)

    # Treat axes as discrete grid cells so Altair doesn't aggregate
    df_map["P_char_lab"] = df_map["P_char"].astype(str)
    df_map["MC_lab"]     = df_map["MC"].map(lambda x: f"{x:.2f}")

    with colh1:
        if metric_choice.startswith("Cost gap"):
            title = f"Cost gap (€/t as-received) at {dist_sel_hm:.0f} km — {mode_for_map}"
            # Center color at 0 to highlight affordable vs unaffordable
            vmax = float(np.nanmax(np.abs(df_map["value"]))) or 1.0
            c_scale = alt.Scale(scheme="redblue", domain=[-vmax, 0, vmax])
            legend_title = "Gap (€/t)"
            note = "Positive = affordable; Zero = break-even; Negative = unaffordable."
        else:
            title = f"Break-even radius (km, DM basis) — {mode_for_map}"
            c_scale = alt.Scale(scheme="blues")
            legend_title = "BE radius (km)"
            note = "BE radius here is independent of MC with this model."

        hm = (
            alt.Chart(df_map)
            .mark_rect()
            .encode(
                x=alt.X("P_char_lab:O", title="Biochar price (€/t)"),
                y=alt.Y("MC_lab:O", title="Moisture content (fraction)"),
                color=alt.Color("value:Q", title=legend_title, scale=c_scale),
                tooltip=[
                    alt.Tooltip("P_char:Q", title="P_char (€/t)"),
                    alt.Tooltip("MC:Q", title="MC"),
                    alt.Tooltip("value:Q", title=legend_title)
                ],
            )
            .properties(title=title, height=420)
        )
        st.altair_chart(hm, use_container_width=True)
        st.caption(note)

    st.download_button(
        "Download heatmap grid CSV",
        data=df_map[["P_char","MC","value"]].to_csv(index=False),
        file_name=("gap_heatmap_grid.csv" if metric_choice.startswith("Cost gap") else "be_radius_heatmap_grid.csv"),
        mime="text/csv",
        key="dl_heatmap_fixed2"
    )

# -----------------------
# TAB 4: Cost Breakdown (stacked bars at selected distance)
# -----------------------
with tab4:
    st.subheader("4) Delivered Cost Breakdown at a Distance (as-received)")
    colc1, colc2 = st.columns([2,1], gap="large")
    with colc2:
        dist_sel = st.number_input("Distance (km, one-way)", min_value=0.0, value=float(kpis["BE_radius_truck"]), step=5.0, key="cb_dist")
        modes_cb = st.multiselect("Modes to compare", ["tractor","truck"], default=["tractor","truck"], key="cb_modes")

    # Build stacked bars: chipping, handling, surcharge, transport
    rows = []
    for mode in modes_cb:
        C_surcharge = Body_Tractor_eur_t if mode=="tractor" else SemiTrailer_eur_t
        C_tkm_mode  = kpis["C_tkm_tractor"] if mode=="tractor" else kpis["C_tkm_truck"]

        comp = {
            "Chipping (€/t as-rec)": kpis["C_chip_eurt"] * (1 - MC_asrec),
            "Handling (€/t as-rec)": kpis["C_handle_eurt"] * (1 - MC_asrec),
            "Surcharge (€/t as-rec)": C_surcharge * (1 - MC_asrec),
            "Transport (€/t as-rec)": Backhaul * C_tkm_mode * dist_sel * (1 - MC_asrec)
        }
        total_cost = sum(comp.values())

        for k, v in comp.items():
            rows.append(dict(mode=mode, component=k, value=v, total=total_cost))

    df_cb = pd.DataFrame(rows)

    with colc1:
        stacked = (
            alt.Chart(df_cb)
            .mark_bar()
            .encode(
                x=alt.X("mode:N", title="Mode"),
                y=alt.Y("value:Q", title="Delivered cost (€/t as-received)"),
                color=alt.Color("component:N", title="Component"),
                tooltip=["mode","component","value"]
            )
            .properties(height=420)
        )
        st.altair_chart(stacked, use_container_width=True)

    # Show totals
    totals = df_cb.groupby("mode", as_index=False)["value"].sum()
    st.dataframe(totals.rename(columns={"value":"Total delivered cost (€/t as-rec)"}))

# -----------------------
# KPIs footer
# -----------------------
st.subheader("Key KPIs (computed)")
k1, k2, k3 = st.columns(3)
k1.metric("Payable @ gate (€/t DM)", f"{kpis['P_chip_payable_DM']:.2f}")
k2.metric("Payable @ gate (€/t as-received)", f"{kpis['P_chip_payable_asrec']:.2f}")
k3.metric("Char output (t/yr)", f"{kpis['CharOutput_yr']:.0f}")
k4, k5, k6 = st.columns(3)
k4.metric("BE radius tractor (km)", f"{kpis['BE_radius_tractor']:.1f}")
k5.metric("BE radius truck (km)", f"{kpis['BE_radius_truck']:.1f}")
k6.metric("As-received intake needed (t/yr)", f"{kpis['Qin_asrec_yr']:.0f}")
