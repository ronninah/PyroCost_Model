# Plant_Flipmodel_carbon.py
# Streamlit app for the Plant-First (Flip) model with carbon extension
# - Uses same formulas as GAMS Plantflip3.gms
# - Base case: P_char = 550 €/t, MC_chips = 25%
# - Shows:
#   (1) Distance vs delivered chip cost + payable price at gate
#   (2) Payable price vs biochar price + break-even radius
#   (3) Carbon credits: CO2 balance, carbon revenue, carbon premium on chip price

import os
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st


# ------------------------------------------------
# Page config
# ------------------------------------------------
st.set_page_config(page_title="Plant-first model with carbon", layout="wide")

st.title("Plant-first Pyrolysis Economics & Carbon — \"ClinX 150\"-type Plant")
st.caption(
    "Interactive visualisation of maximum payable chip price, transport break-even radius, "
    "and a simple carbon-credit extension."
)

# ------------------------------------------------
# Defaults (aligned with Plantflip3.gms)
# ------------------------------------------------
DEFAULTS = dict(
    # Brochure + operations
    Qin_DM_h=0.299,      # t DM/h
    Y_char=0.25,         # t char / t DM
    E_elec_kW=130.0,     # kW electricity
    E_heat_kW=200.0,     # kWth heat
    Hop_year=8000.0,     # h/year
    P_char=550.0,        # €/t (biochar)  <-- your base value
    P_el=0.11,           # €/kWh
    P_heat=0.06,         # €/kWh_th
    n_ops=1.0,           # operators/shift
    w_hour=28.0,         # €/h
    OM_hour=30.0,        # €/h fixed O&M
    P_buy=0.28,          # €/kWh imported electricity
    E_buy_kWh=0.0,       # kWh/h imported electricity
    MarginTarget=0.0,    # €/h target gross margin
    MC_asrec=0.25,       # 25% moisture in chips (as-received)

    # KTBL-style upstream cost blocks
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
    Backhaul=2.0,             # round trip

    WageBase_eur_h=12.82,
    OncostFrac=0.22,
    C_tkm_truck_mach=0.12,    # €/t-km for truck (machine)

    # Carbon extension (can be changed in sidebar)
    P_CO2=80.0,               # €/t CO2-eq
    CO2eq_per_tchar=2.87       # t CO2-eq per t char  (placeholder)
)

WORKDIR = os.path.dirname(__file__)

# ------------------------------------------------
# Sidebar controls
# ------------------------------------------------
st.sidebar.header("Plant & markets")
P_char = st.sidebar.number_input(
    "Biochar selling price (€/t)", min_value=0.0, step=10.0, value=float(DEFAULTS["P_char"])
)
P_el = st.sidebar.number_input(
    "Electricity price (€/kWh)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_el"])
)
P_heat = st.sidebar.number_input(
    "Heat price (€/kWh_th)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_heat"])
)
MC_asrec = st.sidebar.slider(
    "Moisture content of chips at plant gate (%)",
    min_value=0, max_value=60, value=int(DEFAULTS["MC_asrec"] * 100), step=1
) / 100.0
MarginTarget = st.sidebar.number_input(
    "Target plant margin (€/h)", value=float(DEFAULTS["MarginTarget"]), step=10.0
)

st.sidebar.header("Plant operations")
Qin_DM_h = st.sidebar.number_input(
    "Feedstock intake (t/h dry matter)", min_value=0.0, step=0.001,
    value=float(DEFAULTS["Qin_DM_h"]), format="%.3f"
)
Y_char = st.sidebar.number_input(
    "Biochar yield (t char / t dry matter)", min_value=0.0, max_value=1.0,
    step=0.01, value=float(DEFAULTS["Y_char"])
)
E_elec = st.sidebar.number_input(
    "Net electricity export (kW)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_elec_kW"])
)
E_heat = st.sidebar.number_input(
    "Net heat export (kW)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_heat_kW"])
)
Hop_year = st.sidebar.number_input(
    "Operating hours per year", min_value=0.0, step=100.0, value=float(DEFAULTS["Hop_year"])
)

st.sidebar.header("Labour & OPEX")
n_ops = st.sidebar.number_input(
    "Operators per shift", min_value=0.0, step=1.0, value=float(DEFAULTS["n_ops"])
)
w_hour = st.sidebar.number_input(
    "Operator wage (€/h)", min_value=0.0, step=0.5, value=float(DEFAULTS["w_hour"])
)
OM_hour = st.sidebar.number_input(
    "Fixed O&M (€/h)", min_value=0.0, step=1.0, value=float(DEFAULTS["OM_hour"])
)
P_buy = st.sidebar.number_input(
    "Imported electricity price (€/kWh)", min_value=0.0, step=0.01, value=float(DEFAULTS["P_buy"])
)
E_buy = st.sidebar.number_input(
    "Imported electricity (kWh/h)", min_value=0.0, step=1.0, value=float(DEFAULTS["E_buy_kWh"])
)

st.sidebar.header("Transport & handling (KTBL style)")
Backhaul = st.sidebar.selectbox("Backhaul factor", [1.0, 2.0], index=1)
Tractor_speed = st.sidebar.number_input(
    "Tractor speed (km/h)", min_value=1.0, max_value=200.0,
    value=float(DEFAULTS["Tractor_speed_kmh"])
)
Truck_speed = st.sidebar.number_input(
    "Truck speed (km/h)", min_value=1.0, max_value=200.0,
    value=float(DEFAULTS["Truck_speed_kmh"])
)
PayloadTruck = st.sidebar.number_input(
    "Truck payload (t)", min_value=1.0, max_value=60.0,
    value=float(DEFAULTS["PayloadTruck_t"])
)
BulkDensity = st.sidebar.number_input(
    "Loose bulk density of chips (t/m³)", min_value=0.1, max_value=1.0,
    value=float(DEFAULTS["BulkDensity_t_m3"]), step=0.01
)
chip_box_m3 = st.sidebar.number_input(
    "Chip box volume on tractor (m³)", min_value=1.0, max_value=60.0,
    value=22.0, step=1.0
)

IncludeLabor = st.sidebar.checkbox("Include labour in costs", value=True)
IncludeChipOp = st.sidebar.checkbox("Include chipper operator", value=True)
IncludeLoader = st.sidebar.checkbox("Include loader operator", value=True)
IncludeDriver = st.sidebar.checkbox("Include driver (tractor & truck)", value=True)
AddLaborToTruckTkm = st.sidebar.checkbox("Add driver labour into truck t·km", value=True)

# Carbon parameters
st.sidebar.header("Carbon credits (simple)")
P_CO2 = st.sidebar.number_input(
    "Carbon price (€/t CO₂-eq)", min_value=0.0, step=5.0, value=float(DEFAULTS["P_CO2"])
)
CO2eq_per_tchar = st.sidebar.number_input(
    "Net CO₂-eq per t biochar (t CO₂-eq / t char)",
    min_value=-10.0, max_value=10.0, step=0.1,
    value=float(DEFAULTS["CO2eq_per_tchar"])
)
IncludeCarbonInPayable = st.sidebar.checkbox(
    "Add carbon value on top of payable chip price", value=True
)

# Fixed machine costs
Tractor_eur_h = float(DEFAULTS["Tractor_eur_h"])
PTOChipper_eur_h = float(DEFAULTS["PTOChipper_eur_h"])
Body_Tractor_eur_t = float(DEFAULTS["Body_Tractor_eur_t"])
SemiTrailer_eur_t = float(DEFAULTS["SemiTrailer_eur_t"])
Bucket_eur_t = float(DEFAULTS["Bucket_eur_t"])
FrontLoader_eur_h = float(DEFAULTS["FrontLoader_eur_h"])
Chipper_m3_h = float(DEFAULTS["Chipper_m3_h"])
Handling_tph = float(DEFAULTS["Handling_tph"])
C_tkm_truck_mach = float(DEFAULTS["C_tkm_truck_mach"])

WageBase = float(DEFAULTS["WageBase_eur_h"])
OncostFrac = float(DEFAULTS["OncostFrac"])
Wage_eur_h = WageBase * (1 + OncostFrac)

# ------------------------------------------------
# Core economics (same logic as GAMS)
# ------------------------------------------------
def compute_kpis():
    # Hourly outputs and revenues
    Qchar_h = Y_char * Qin_DM_h
    Rchar = P_char * Qchar_h
    Rel = P_el * E_elec
    Rheat = P_heat * E_heat
    Rev = Rchar + Rel + Rheat

    # Hourly non-feedstock costs
    Clab = n_ops * w_hour
    Com = OM_hour
    Cbuy = P_buy * E_buy

    # Max payable chip price at plant gate (€/t dry matter)
    P_chip_DM = (Rev - (Clab + Com + Cbuy) - MarginTarget) / max(1e-9, Qin_DM_h)
    P_chip_asrec = P_chip_DM * (1 - MC_asrec)

    # Chipping & handling €/t (dry matter)
    C_chip_mach = (Tractor_eur_h + PTOChipper_eur_h) / max(1e-9, Chipper_m3_h * BulkDensity)
    C_hand_mach = Bucket_eur_t + FrontLoader_eur_h / max(1e-9, Handling_tph)
    Labor_chip_hpt = 1.0 / max(1e-9, Chipper_m3_h * BulkDensity)
    Labor_hand_hpt = 1.0 / max(1e-9, Handling_tph)

    C_chip = C_chip_mach + (Wage_eur_h * Labor_chip_hpt if (IncludeLabor and IncludeChipOp) else 0.0)
    C_hand = C_hand_mach + (Wage_eur_h * Labor_hand_hpt if (IncludeLabor and IncludeLoader) else 0.0)

    # Transport €/t·km
    PayloadTractor = chip_box_m3 * BulkDensity
    C_tkm_tractor = (
        Tractor_eur_h / max(1e-9, Tractor_speed * PayloadTractor)
        + (Wage_eur_h if (IncludeLabor and IncludeDriver) else 0.0)
        / max(1e-9, Tractor_speed * PayloadTractor)
    )
    C_tkm_truck = (
        C_tkm_truck_mach
        + (Wage_eur_h if (IncludeLabor and IncludeDriver and AddLaborToTruckTkm) else 0.0)
        / max(1e-9, Truck_speed * PayloadTruck)
    )

    # Break-even radius (km one-way) without carbon
    BE_trac = max(
        0.0,
        (P_chip_DM - (C_chip + C_hand + Body_Tractor_eur_t))
        / max(1e-9, Backhaul * C_tkm_tractor),
    )
    BE_truck = max(
        0.0,
        (P_chip_DM - (C_chip + C_hand + SemiTrailer_eur_t))
        / max(1e-9, Backhaul * C_tkm_truck),
    )

    # Annual KPIs
    PayableBudget_yr = P_chip_DM * Qin_DM_h * Hop_year
    CharOutput_yr = Y_char * Qin_DM_h * Hop_year
    Qin_asrec_yr = Qin_DM_h * Hop_year / max(1e-9, (1 - MC_asrec))

    # Carbon extension
    CO2_balance_yr = CharOutput_yr * CO2eq_per_tchar
    CO2_rev_yr = CO2_balance_yr * P_CO2
    CarbonPremium_DM = Y_char * CO2eq_per_tchar * P_CO2
    CarbonPremium_asrec = CarbonPremium_DM * (1 - MC_asrec)

    if IncludeCarbonInPayable:
        P_chip_DM_withC = P_chip_DM + CarbonPremium_DM
        P_chip_asrec_withC = P_chip_DM_withC * (1 - MC_asrec)
    else:
        P_chip_DM_withC = P_chip_DM
        P_chip_asrec_withC = P_chip_asrec

    k = dict(
        P_chip_DM=P_chip_DM,
        P_chip_asrec=P_chip_asrec,
        C_chip=C_chip,
        C_hand=C_hand,
        C_tkm_tractor=C_tkm_tractor,
        C_tkm_truck=C_tkm_truck,
        BE_trac=BE_trac,
        BE_truck=BE_truck,
        PayableBudget_yr=PayableBudget_yr,
        CharOutput_yr=CharOutput_yr,
        Qin_asrec_yr=Qin_asrec_yr,
        # carbon stuff
        CO2_balance_yr=CO2_balance_yr,
        CO2_rev_yr=CO2_rev_yr,
        CarbonPremium_DM=CarbonPremium_DM,
        CarbonPremium_asrec=CarbonPremium_asrec,
        P_chip_DM_withC=P_chip_DM_withC,
        P_chip_asrec_withC=P_chip_asrec_withC,
    )
    return k


kpis = compute_kpis()

# ------------------------------------------------
# Tabs
# ------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Distance & delivered chip cost",
    "Biochar price & break-even radius",
    "Carbon credits & premiums",
    "Plant profit vs payable chip price",
    "Farm margin vs distance"

])

# ------------------------------------------------
# TAB 1: Distance vs delivered chip cost
# ------------------------------------------------
with tab1:
    st.subheader("1. Delivered chip cost vs distance, and payable price at gate")

    colA, colB = st.columns([2, 1])
    with colB:
        max_km = st.number_input("Maximum distance shown (km)", min_value=10, max_value=300,
                                 value=200, step=10)
        km_step = st.number_input("Step size (km)", min_value=1, max_value=50,
                                  value=1, step=1)
        modes = st.multiselect("Transport modes", ["tractor", "truck"],
                               default=["tractor", "truck"])

        show_carbon_line = st.checkbox(
            "Show payable price including carbon value", value=True
        )

    # Build distance grid
    kms = np.arange(0, max_km + km_step, km_step, dtype=float)
    rows = []
    for mode in ["tractor", "truck"]:
        if mode == "tractor":
            C_surcharge = Body_Tractor_eur_t
            C_tkm_mode = kpis["C_tkm_tractor"]
        else:
            C_surcharge = SemiTrailer_eur_t
            C_tkm_mode = kpis["C_tkm_truck"]

        for d in kms:
            # delivered cost per t of chips at plant gate (as-received)
            cost_asrec = (
                (kpis["C_chip"] + kpis["C_hand"] + C_surcharge) * (1 - MC_asrec)
                + Backhaul * C_tkm_mode * d * (1 - MC_asrec)
            )
            rows.append(
                dict(
                    distance_km=d,
                    mode=mode,
                    delivered_cost_chips_eurpt=cost_asrec,
                )
            )

    df_dist = pd.DataFrame(rows)
    df_modes = df_dist[df_dist["mode"].isin(modes)]

    # Find approximate BE points (where delivered cost ≈ payable)
    df_modes["payable_asrec_base"] = kpis["P_chip_asrec"]
    df_modes["gap_base"] = (df_modes["delivered_cost_chips_eurpt"]
                            - df_modes["payable_asrec_base"]).abs()

    be_rows = []
    for mode in modes:
        sub = df_modes[df_modes["mode"] == mode]
        if sub.empty:
            continue
        idx = sub["gap_base"].idxmin()
        be_rows.append(sub.loc[idx])

    df_be = pd.DataFrame(be_rows) if be_rows else pd.DataFrame(columns=df_modes.columns)

    with colA:
        # Payable lines
        base_line_df = pd.DataFrame({
            "distance_km": [df_dist["distance_km"].min(), df_dist["distance_km"].max()],
            "payable_price": [kpis["P_chip_asrec"], kpis["P_chip_asrec"]],
            "line_type": ["Base payable", "Base payable"],
        })

        lines = [
            alt.Chart(base_line_df)
            .mark_line(strokeDash=[6, 3])
            .encode(
                x=alt.X("distance_km:Q", title="Distance from plant (km)"),
                y=alt.Y("payable_price:Q", title="Price / cost for chips at plant gate (€/t, as-received)"),
                color=alt.value("black"),
                tooltip=["distance_km", "payable_price"],
            )
        ]

        if show_carbon_line:
            carbon_line_df = base_line_df.copy()
            carbon_line_df["payable_price"] = kpis["P_chip_asrec_withC"]
            lines.append(
                alt.Chart(carbon_line_df)
                .mark_line(strokeDash=[2, 2])
                .encode(
                    x="distance_km:Q",
                    y="payable_price:Q",
                    color=alt.value("gray"),
                    tooltip=["distance_km", "payable_price"],
                )
            )

        payable_chart = alt.layer(*lines).properties(height=220)

        # Delivered cost curves
        cost_chart = (
            alt.Chart(df_modes)
            .mark_line()
            .encode(
                x=alt.X("distance_km:Q", title="Distance from plant (km)"),
                y=alt.Y("delivered_cost_chips_eurpt:Q",
                        title="Delivered chip cost at plant gate (€/t, as-received)"),
                color=alt.Color("mode:N", title="Mode"),
                tooltip=["distance_km", "mode", "delivered_cost_chips_eurpt"],
            )
            .properties(height=260)
        )

        # BE points (base case)
        if not df_be.empty:
            be_points = (
                alt.Chart(df_be)
                .mark_point(size=80, filled=True)
                .encode(
                    x="distance_km:Q",
                    y="delivered_cost_chips_eurpt:Q",
                    color=alt.Color("mode:N", legend=None),
                    tooltip=[
                        "mode",
                        "distance_km",
                        "delivered_cost_chips_eurpt",
                        "payable_asrec_base",
                    ],
                )
            )
        else:
            be_points = alt.Chart()

        chart1 = alt.vconcat(payable_chart, cost_chart + be_points, spacing=10)
        st.altair_chart(chart1, use_container_width=True)

    st.info(
        f"Base payable price at plant gate (dry matter): {kpis['P_chip_DM']:.2f} €/t DM "
        f"→ as chips (at {MC_asrec*100:.0f}% moisture): {kpis['P_chip_asrec']:.2f} €/t.\n"
        f"Break-even radius (no carbon): tractor ≈ {kpis['BE_trac']:.1f} km, "
        f"truck ≈ {kpis['BE_truck']:.1f} km."
    )

# ------------------------------------------------
# TAB 2: Payable vs biochar price + BE radius
# ------------------------------------------------
with tab2:
    st.subheader("2. Payable chip price vs biochar price, and break-even radius")

    col1, col2 = st.columns([2, 1])
    with col2:
        dP = st.number_input("Step in biochar price for grid (€/t)", min_value=1, max_value=500,
                             value=50, step=1)
        points = st.slider("Number of grid points", min_value=5, max_value=25,
                           value=11, step=2)
        modes_for_grid = st.multiselect(
            "Transport modes for radius", ["tractor", "truck"],
            default=["tractor", "truck"]
        )
        add_carbon_in_grid = st.checkbox(
            "Include carbon value in payable price in this grid", value=False
        )

    # Build price grid centered on current P_char
    idxs = np.arange(points) - (points // 2)
    Pchar_grid = P_char + idxs * dP

    rows = []
    for Pc in Pchar_grid:
        # Revenue at given biochar price (Pc)
        Qchar_h = Y_char * Qin_DM_h
        Rchar = Pc * Qchar_h
        Rel = P_el * E_elec
        Rheat = P_heat * E_heat
        Rev = Rchar + Rel + Rheat

        Clab = n_ops * w_hour
        Com = OM_hour
        Cbuy = P_buy * E_buy

        pay_DM = (Rev - (Clab + Com + Cbuy) - MarginTarget) / max(1e-9, Qin_DM_h)
        if add_carbon_in_grid and P_CO2 > 0.0:
            pay_DM = pay_DM + (Y_char * CO2eq_per_tchar * P_CO2)
        pay_asrec = pay_DM * (1 - MC_asrec)

        # Transport coefficients (same for all Pc)
        PayloadTractor = chip_box_m3 * BulkDensity
        C_tkm_tractor = (
            Tractor_eur_h / max(1e-9, Tractor_speed * PayloadTractor)
            + (Wage_eur_h if (IncludeLabor and IncludeDriver) else 0.0)
            / max(1e-9, Tractor_speed * PayloadTractor)
        )
        C_tkm_truck = (
            C_tkm_truck_mach
            + (Wage_eur_h if (IncludeLabor and IncludeDriver and AddLaborToTruckTkm) else 0.0)
            / max(1e-9, Truck_speed * PayloadTruck)
        )

        C_chip_mach = (Tractor_eur_h + PTOChipper_eur_h) / max(1e-9, Chipper_m3_h * BulkDensity)
        C_hand_mach = Bucket_eur_t + FrontLoader_eur_h / max(1e-9, Handling_tph)
        Labor_chip_hpt = 1.0 / max(1e-9, Chipper_m3_h * BulkDensity)
        Labor_hand_hpt = 1.0 / max(1e-9, Handling_tph)
        C_chip = C_chip_mach + (Wage_eur_h * Labor_chip_hpt if (IncludeLabor and IncludeChipOp) else 0.0)
        C_hand = C_hand_mach + (Wage_eur_h * Labor_hand_hpt if (IncludeLabor and IncludeLoader) else 0.0)

        BE_trac = max(
            0.0,
            (pay_DM - (C_chip + C_hand + Body_Tractor_eur_t))
            / max(1e-9, Backhaul * C_tkm_tractor),
        )
        BE_truck = max(
            0.0,
            (pay_DM - (C_chip + C_hand + SemiTrailer_eur_t))
            / max(1e-9, Backhaul * C_tkm_truck),
        )

        rows.append(
            dict(
                Pchar_eurpt=Pc,
                Pchip_pay_DM_eurptDM=pay_DM,
                Pchip_pay_asrec_eurpt=pay_asrec,
                BE_radius_tractor_km=BE_trac,
                BE_radius_truck_km=BE_truck,
            )
        )

    df_pchar = pd.DataFrame(rows)

    with col1:
        # Upper chart: payable chip price vs biochar price
        pay_lines = [
            alt.Chart(df_pchar)
            .mark_line()
            .encode(
                x=alt.X("Pchar_eurpt:Q", title="Biochar selling price (€/t)"),
                y=alt.Y(
                    "Pchip_pay_DM_eurptDM:Q",
                    title="Payable chip price at plant gate (€/t dry matter)",
                ),
                tooltip=["Pchar_eurpt", "Pchip_pay_DM_eurptDM"],
            )
        ]

        pay_lines.append(
            alt.Chart(df_pchar)
            .mark_line(strokeDash=[6, 3])
            .encode(
                x="Pchar_eurpt:Q",
                y=alt.Y(
                    "Pchip_pay_asrec_eurpt:Q",
                    title="Payable chip price at plant gate (€/t chips, as-received)",
                ),
                tooltip=["Pchar_eurpt", "Pchip_pay_asrec_eurpt"],
            )
        )

        top = alt.layer(*pay_lines).properties(height=230)

        # Lower chart: BE radius vs biochar price (long format)
        radius_df = df_pchar.melt(
            id_vars=["Pchar_eurpt"],
            value_vars=["BE_radius_tractor_km", "BE_radius_truck_km"],
            var_name="mode",
            value_name="radius_km",
        )
        if modes_for_grid:
            radius_df = radius_df[
                radius_df["mode"].isin([f"BE_radius_{m}_km" for m in modes_for_grid])
            ]

        bottom = (
            alt.Chart(radius_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("Pchar_eurpt:Q", title="Biochar selling price (€/t)"),
                y=alt.Y("radius_km:Q", title="Break-even transport radius (km one-way)"),
                color=alt.Color("mode:N", title="Mode"),
                tooltip=["Pchar_eurpt", "mode", "radius_km"],
            )
            .properties(height=230)
        )

        chart2 = alt.vconcat(top, bottom, spacing=12)
        st.altair_chart(chart2, use_container_width=True)

    st.info(
        "The upper panel shows how the **maximum payable chip price at the plant gate** rises with "
        "higher biochar selling prices. The lower panel shows how this translates into a larger "
        "break-even collection radius for tractor and truck transport."
    )

# ------------------------------------------------
# TAB 3: Carbon credits & premiums
# ------------------------------------------------
with tab3:
    st.subheader("3. Carbon credits, CO₂ balance and chip price premium")

    colL, colR = st.columns([2, 1])

    with colL:
        st.markdown("### Summary table")

        df_carbon = pd.DataFrame(
            [
                dict(
                    item="CO₂ balance from biochar (t CO₂-eq/year)",
                    value=f"{kpis['CO2_balance_yr']:.0f}",
                ),
                dict(
                    item="Carbon credit revenue (€/year)",
                    value=f"{kpis['CO2_rev_yr']:.0f}",
                ),
                dict(
                    item="Carbon premium on chip price (€/t dry matter)",
                    value=f"{kpis['CarbonPremium_DM']:.2f}",
                ),
                dict(
                    item="Carbon premium on chip price (€/t chips, as-received)",
                    value=f"{kpis['CarbonPremium_asrec']:.2f}",
                ),
                dict(
                    item="Payable chip price at gate w/o carbon (€/t DM)",
                    value=f"{kpis['P_chip_DM']:.2f}",
                ),
                dict(
                    item="Payable chip price at gate WITH carbon (€/t DM)",
                    value=f"{kpis['P_chip_DM_withC']:.2f}",
                ),
            ]
        )
        st.table(df_carbon)

    with colR:
        st.markdown("### Interpretation")
        st.write(
            f"- With P_CO₂ = **{P_CO2:.0f} €/t CO₂-eq** and "
            f"CO₂eq_per_tchar = **{CO2eq_per_tchar:.1f} t CO₂-eq/t char**, "
            f"your plant produces about **{kpis['CO2_balance_yr']:.0f} t CO₂-eq/year** "
            f"via biochar.\n"
            f"- This corresponds to roughly **{kpis['CO2_rev_yr']:.0f} €/year** in potential "
            f"carbon-credit revenue.\n"
            f"- Per tonne of *dry matter chips*, this carbon value adds about "
            f"**{kpis['CarbonPremium_DM']:.2f} €/t DM** on top of the payable chip price "
            f"(if fully internalised by the plant).\n"
            f"- If you ticked **'Add carbon value on top of payable chip price'** in the sidebar, "
            f"this premium is already built into the payable values and break-even radii in the other tabs."
        )

    st.info(
    "CO₂eq_per_tchar is currently set to match the Pyro-ClinX brochure (8000 h/year). "
    "You can still overwrite it in the sidebar or later replace it with values from a detailed LCA."
)


# ------------------------------------------------
# TAB 4: Plant gross margin vs payable chip price (from GAMS CSV)
# ------------------------------------------------
with tab4:
    st.subheader("4. Plant gross margin vs payable chip price (GAMS results)")

    st.info(
        "This tab reads **fixed results from GAMS** "
        "(`plant_profit_curve_j1.csv`). It does **not** react to the sidebar sliders. "
        "To change these curves, rerun the GAMS model (`Plantflip3.gms`) so it rewrites "
        "the CSV file, then reload this app."
    )

    csv_path_profit = os.path.join(WORKDIR, "plant_profit_curve_j1.csv")

    if not os.path.exists(csv_path_profit):
        st.error(f"CSV file not found: {csv_path_profit}")
        st.write(
            "Please run the GAMS file `Plantflip3.gms` so that it exports "
            "`plant_profit_curve_j1.csv`, then reload this app."
        )
    else:
        df_profit = pd.read_csv(csv_path_profit)

        st.caption("Source: `plant_profit_curve_j1.csv` from GAMS (Plantflip3.gms).")
        st.dataframe(df_profit.head(), use_container_width=True)

        # Long format for Altair
        df_profit_long = df_profit.melt(
            id_vars=["plant", "P_chip_EUR_per_tDM"],
            value_vars=["GM_base_EUR_per_yr", "GM_withC_EUR_per_yr"],
            var_name="scenario",
            value_name="GM_EUR_per_yr",
        )

        # Clean scenario labels
        df_profit_long["scenario"] = df_profit_long["scenario"].replace(
            {
                "GM_base_EUR_per_yr": "No carbon",
                "GM_withC_EUR_per_yr": "With carbon",
            }
        )

        # Fixed color mapping for scenarios (adjust hex codes to match your paper)
        color_scale = alt.Scale(
            domain=["No carbon", "With carbon"],
            range=["#1f77b4", "#ff7f0e"]  # blue = no carbon, orange = with carbon
        )

        chart_profit = (
            alt.Chart(df_profit_long)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "P_chip_EUR_per_tDM:Q",
                    title="Payable chip price at plant gate (€/t dry matter)",
                ),
                y=alt.Y(
                    "GM_EUR_per_yr:Q",
                    title="Plant gross margin (€/year)",
                ),
                color=alt.Color(
                    "scenario:N",
                    title="Scenario",
                    scale=color_scale,
                ),
                tooltip=[
                    "plant",
                    "P_chip_EUR_per_tDM",
                    "scenario",
                    "GM_EUR_per_yr",
                ],
            )
            .properties(height=380)
        )

        st.altair_chart(chart_profit, use_container_width=True)

        st.info(
            "Curve labels:\n"
            "- **No carbon** = gross margin from the plant economics only.\n"
            "- **With carbon** = same plant plus annual carbon-credit revenue from GAMS.\n"
            "All values are taken directly from the GAMS output file."
        )


# ------------------------------------------------
# TAB 5: Farm margin vs distance (from GAMS CSV)
# ------------------------------------------------
with tab5:
    st.subheader("5. Farm margin vs distance (GAMS results)")

    st.info(
        "This tab reads **fixed results from GAMS** "
        "(`farm_margin_vs_distance_j1.csv`). It does **not** react to the sidebar sliders. "
        "To change these curves, rerun the GAMS model (`Plantflip3.gms`) so it rewrites "
        "the CSV file, then reload this app."
    )

    csv_path_farm = os.path.join(WORKDIR, "farm_margin_vs_distance_j1.csv")

    if not os.path.exists(csv_path_farm):
        st.error(f"CSV file not found: {csv_path_farm}")
        st.write(
            "Please run the GAMS file `Plantflip3.gms` so that it exports "
            "`farm_margin_vs_distance_j1.csv`, then reload this app."
        )
    else:
        df_farm = pd.read_csv(csv_path_farm)

        st.caption("Source: `farm_margin_vs_distance_j1.csv` from GAMS (Plantflip3.gms).")
        st.dataframe(df_farm.head(), use_container_width=True)

        col_ctrl, col_plot = st.columns([1, 2])

        with col_ctrl:
            modes_farm = st.multiselect(
                "Transport modes (farm margin plot)",
                ["tractor", "truck"],
                default=["tractor", "truck"],
                key="modes_tab5",
            )
            scen_sel = st.multiselect(
                "Scenarios",
                ["base", "withC"],
                default=["base", "withC"],
                key="scen_tab5",
            )

        df_plot = df_farm.copy()
        df_plot = df_plot[df_plot["mode"].isin(modes_farm)]
        df_plot = df_plot[df_plot["scenario"].isin(scen_sel)]

        if df_plot.empty:
            with col_plot:
                st.warning("No data to plot for the selected modes/scenarios.")
        else:
            # Fixed colors for modes, fixed dash for scenarios
            mode_color_scale = alt.Scale(
                domain=["tractor", "truck"],
                range=["#1f77b4", "#ff7f0e"]  # e.g. blue = tractor, orange = truck
            )

            dash_scale = alt.Scale(
                domain=["base", "withC"],
                range=[[], [4, 4]]  # solid = base, dashed = with carbon
            )

            farm_chart = (
                alt.Chart(df_plot)
                .mark_line()
                .encode(
                    x=alt.X("km:Q", title="Distance from farm to plant (km)"),
                    y=alt.Y(
                        "GM_farm_asrec_eurpt:Q",
                        title="Farm margin (€/t chips, as-received)",
                    ),
                    color=alt.Color(
                        "mode:N",
                        title="Mode",
                        scale=mode_color_scale,
                    ),
                    strokeDash=alt.StrokeDash(
                        "scenario:N",
                        title="Scenario",
                        scale=dash_scale,
                    ),
                    tooltip=[
                        "km",
                        "mode",
                        "scenario",
                        "gate_price_asrec_eurpt",
                        "delivered_cost_asrec_eurpt",
                        "GM_farm_asrec_eurpt",
                    ],
                )
                .properties(height=380)
            )
            with col_plot:
                st.altair_chart(farm_chart, use_container_width=True)

        st.info(
            "Farm margin is defined here exactly as in the GAMS CSV: "
            "`GM_farm_asrec_eurpt = gate_price_asrec_eurpt − delivered_cost_asrec_eurpt` "
            "(€/t chips, as-received).\n\n"
            "- **Mode color**: blue = tractor, orange = truck.\n"
            "- **Line style**: solid = base gate price, dashed = gate price including carbon value."
        )
    
# ------------------------------------------------
# KPIs panel at bottom
# ------------------------------------------------
st.subheader("Key plant KPIs (base case, without carbon unless stated)")

kpi_cols = st.columns(3)
kpi_cols[0].metric("Payable chip price @ gate (€/t DM)", f"{kpis['P_chip_DM']:.2f}")
kpi_cols[1].metric(
    "Payable chip price @ gate (€/t chips, as-received)",
    f"{kpis['P_chip_asrec']:.2f}",
)
kpi_cols[2].metric("Annual biochar output (t/year)", f"{kpis['CharOutput_yr']:.0f}")

kpi_cols2 = st.columns(3)
kpi_cols2[0].metric("Annual chip requirement (t/year, as-received)",
                    f"{kpis['Qin_asrec_yr']:.0f}")
kpi_cols2[1].metric("Break-even radius tractor (km)", f"{kpis['BE_trac']:.1f}")
kpi_cols2[2].metric("Break-even radius truck (km)", f"{kpis['BE_truck']:.1f}")

