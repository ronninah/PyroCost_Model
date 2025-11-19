import pandas as pd
import matplotlib.pyplot as plt

df_gm = pd.read_csv("plant_profit_curve_j1.csv")

print(df_gm.head())

plt.figure()
plt.plot(
    df_gm["P_chip_EUR_per_tDM"],
    df_gm["GM_base_EUR_per_yr"],
    label="Without carbon"
)
plt.plot(
    df_gm["P_chip_EUR_per_tDM"],
    df_gm["GM_withC_EUR_per_yr"],
    linestyle="--",
    label="With carbon revenue"
)

plt.axhline(0, linestyle=":")
plt.xlabel("Payable chip price at plant gate [€/t DM]")
plt.ylabel("Plant gross margin [€/yr]")
plt.title("Plant gross margin vs payable chip price (Pyro-ClinX 150)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()



df_farm = pd.read_csv("farm_margin_vs_distance_j1.csv")

print(df_farm.head())

# choose one mode to plot, e.g. tractor
mode_sel = "tractor"
sub = df_farm[df_farm["mode"] == mode_sel]

plt.figure()
for scen in ["base", "withC"]:
    sub_scen = sub[sub_scen := sub["scenario"] == scen]  # just a filter
    sub_scen = sub[sub["scenario"] == scen]
    plt.plot(
        sub_scen["km"],
        sub_scen["GM_farm_asrec_eurpt"],
        label=f"{scen} gate price"
    )

plt.axhline(0, linestyle=":")
plt.xlabel("One-way distance [km]")
plt.ylabel("Farm margin [€/t as-received]")
plt.title(f"Farm margin vs distance ({mode_sel})")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
