# make_plant_viz.py
# Creates plant-level visuals from:
#   - plant_modeA_kpi_j1.csv
#   - plant_modeA_breakeven_j1.csv
#   - supply_vs_capacity_j1.csv
#
# Output PNGs in figures/plant/

import matplotlib
matplotlib.use("Agg")  # non-GUI backend for batch save
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

ROOT = Path(".")
FIGDIR = ROOT / "figures" / "plant"
FIGDIR.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
def read_csv_safe(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p.resolve()}")
    # safe read (handles potential quoting)
    return pd.read_csv(p)

def save_and_close(figpath):
    plt.tight_layout()
    plt.savefig(figpath, dpi=200)
    plt.close()

print("[make_plant_viz] using:", Path.cwd())

# ---------- 1) KPI: Revenue vs Costs vs GM ----------
# CSV layout (from your GAMS code):
# plant,P_char,E_net_kW,H_use_kW,P_chipDM_deliv,Rev,Cfs,Clab,Com,Cbuy,GM,GM_per_tDM,GM_per_year
kpi = read_csv_safe("plant_modeA_kpi_j1.csv")

# Pull values (assume single row for j1)
row = kpi.iloc[0]
plant_id = str(row["plant"])
rev  = float(row["Rev"])
cfs  = float(row["Cfs"])
clab = float(row["Clab"])
com  = float(row["Com"])
cbuy = float(row["Cbuy"])
gm   = float(row["GM"])

# Figure 1A: Grouped bar – Revenue vs each cost (€/h)
labels = ["Revenue", "Feedstock", "Labor", "O&M", "Purchased Elec"]
vals   = [rev,       cfs,         clab,     com,   cbuy]

plt.figure(figsize=(7,4))
plt.bar(labels, vals)
plt.ylabel("€/h")
plt.title(f"Plant {plant_id}: Revenue and Cost Components (€/h)")
save_and_close(FIGDIR / "plant_kpi_rev_costs_bar.png")

# Figure 1B: Net GM highlight (€/h)
plt.figure(figsize=(4.5,4))
plt.bar(["Gross Margin"], [gm])
plt.ylabel("€/h")
plt.title(f"Plant {plant_id}: Gross Margin (€/h)")
# Annotate value
plt.gca().bar_label(plt.gca().containers[0], fmt="%.2f")
save_and_close(FIGDIR / "plant_kpi_gm_bar.png")

# ---------- 2) Break-even prices ----------
# CSV layout:
# Pchar_BE_EURt,Pchip_BE_EURtDM
be = read_csv_safe("plant_modeA_breakeven_j1.csv")
pchar_be = float(be.iloc[0]["Pchar_BE_EURt"])
pchip_be = float(be.iloc[0]["Pchip_BE_EURtDM"])

plt.figure(figsize=(6,4))
plt.bar(["Char break-even (€/t)", "Chip break-even (€/t DM)"], [pchar_be, pchip_be])
plt.ylabel("€/t or €/t DM")
plt.title(f"Plant {plant_id}: Break-even Prices")
plt.gca().bar_label(plt.gca().containers[0], fmt="%.2f")
save_and_close(FIGDIR / "plant_break_even_prices.png")

# ---------- 3) Supply vs Capacity (DM basis) ----------
# CSV layout:
# Cap_DM_h,Cap_DM_yr,Cap_asrec_yr,Sup_asrec_yr,Sup_DM_yr,Sup_DM_h,Diff_DM_h,Diff_asrec_yr,Util_DM
sup = read_csv_safe("supply_vs_capacity_j1.csv")
Cap_DM_h  = float(sup.iloc[0]["Cap_DM_h"])
Sup_DM_h  = float(sup.iloc[0]["Sup_DM_h"])
Util_DM   = float(sup.iloc[0]["Util_DM"])

# Figure 3A: Capacity vs Upstream Supply (t DM/h)
plt.figure(figsize=(6,4))
plt.bar(["Capacity (DM/h)", "Upstream Supply (DM/h)"], [Cap_DM_h, Sup_DM_h])
plt.ylabel("t DM/h")
plt.title(f"Plant {plant_id}: Capacity vs Upstream Supply (DM/h)")
plt.gca().bar_label(plt.gca().containers[0], fmt="%.3f")
save_and_close(FIGDIR / "plant_capacity_vs_supply_DMh.png")

# Figure 3B: Utilization gauge (simple bar)
plt.figure(figsize=(5,3.2))
plt.bar(["Utilization (DM basis)"], [Util_DM])
plt.ylim(0, 1.0)
plt.ylabel("fraction of capacity")
plt.title(f"Plant {plant_id}: Utilization (DM basis)")
plt.gca().bar_label(plt.gca().containers[0], fmt="%.2f")
save_and_close(FIGDIR / "plant_utilization_DM.png")

# ---------- 4) Energy outputs (from KPI row) ----------
elec_kW = float(kpi.iloc[0]["E_net_kW"])
heat_kW = float(kpi.iloc[0]["H_use_kW"])  # column name in your CSV

plt.figure(figsize=(6,4))
plt.bar(["Net electricity (kW)", "Useful heat (kW_th)"], [elec_kW, heat_kW])
plt.ylabel("kW")
plt.title(f"Plant {plant_id}: Energy Co-products (nameplate)")
plt.gca().bar_label(plt.gca().containers[0], fmt="%.0f")
save_and_close(FIGDIR / "plant_energy_outputs.png")

print("Done. Plant figures saved to:", FIGDIR.resolve())
