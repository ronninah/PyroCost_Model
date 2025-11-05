from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from gdx_dump_parser import parse_gdx_dump

# ---------- config ----------
OUTDIR = Path("figures")
OUTDIR.mkdir(exist_ok=True)
FONT_SIZE = 10
plt.rcParams.update({"font.size": FONT_SIZE})

def lane_label(df, i="i", j="j", m="m"):
    return df[i] + "→" + df[j] + " (" + df[m] + ")"

def save_bar(series: pd.Series, title: str, ylabel: str, fname: str, rotate=45):
    ax = series.plot(kind="bar", figsize=(10, 4), legend=False)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=rotate, ha="right")
    plt.tight_layout()
    plt.savefig(OUTDIR / fname, dpi=200)
    plt.close()

def save_grouped_bar(df: pd.DataFrame, title: str, ylabel: str, fname: str):
    # df has columns ['lane','Revenue','Cost']
    df = df.set_index("lane").sort_values("Revenue")
    ax = df.plot(kind="bar", figsize=(11, 4))
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(OUTDIR / fname, dpi=200)
    plt.close()

def uc_lane_total(csv_path="UC_lane.csv"):
    df = parse_gdx_dump(csv_path)   # i,j,m,value
    df["lane"] = lane_label(df)
    s = df.set_index("lane")["value"].sort_values(ascending=True)
    save_bar(s, "Unit Cost per Lane (UC_lane)", "€/t", "UC_lane_bar.png")

def um_lane_total(csv_path="UM_lane.csv"):
    df = parse_gdx_dump(csv_path)
    df["lane"] = lane_label(df)
    s = df.set_index("lane")["value"].sort_values(ascending=True)
    save_bar(s, "Unit Margin per Lane (UM_lane)", "€/t", "UM_lane_bar.png")

def gm_lane_total(csv_path="GM_lane.csv"):
    df = parse_gdx_dump(csv_path)
    df["lane"] = lane_label(df)
    s = df.set_index("lane")["value"].sort_values(ascending=True)
    save_bar(s, "Gross Margin per Lane (€/yr) (GM_lane)", "€/yr", "GM_lane_bar.png")

def rev_cost_grouped(rev_csv="Rev_lane.csv", cost_csv="Cost_lane.csv"):
    dfr = parse_gdx_dump(rev_csv)   # i,j,m,value  (€/yr)
    dfc = parse_gdx_dump(cost_csv)  # i,j,m,value  (€/yr)
    dfr["lane"] = lane_label(dfr)
    dfc["lane"] = lane_label(dfc)
    merged = (dfr[["lane","value"]].rename(columns={"value":"Revenue"})
              .merge(dfc[["lane","value"]].rename(columns={"value":"Cost"}), on="lane", how="inner"))
    save_grouped_bar(merged, "Revenue vs Cost by Lane (€/yr)", "€/yr", "Rev_vs_Cost_lane.png")

def be_radius(csv_path="BE_radius.csv"):
    # 2-tuple: j,m,value (km)
    df = parse_gdx_dump(csv_path)
    df["plant_mode"] = df["j"] + " (" + df["m"] + ")"
    s = df.set_index("plant_mode")["value"].sort_values(ascending=True)
    save_bar(s, "Break-even One-way Radius by Plant & Mode (BE_radius)", "km", "BE_radius_bar.png", rotate=0)

def uc_by_ij_sum_modes(csv_path="UC_lane.csv"):
    # Optional: sum UC across modes by (i,j) to see per-lane average cost ignoring mode detail
    df = parse_gdx_dump(csv_path)
    df["ij"] = df["i"] + "→" + df["j"]
    s = df.groupby("ij")["value"].mean().sort_values(ascending=True)  # mean of modes
    save_bar(s, "Unit Cost by (i→j) (mean across modes)", "€/t", "UC_by_ij_mean_modes.png")

def gm_by_i(csv_path="GM_lane.csv"):
    df = parse_gdx_dump(csv_path)
    s = df.groupby("i")["value"].sum().sort_values(ascending=True)  # €/yr by farm
    save_bar(s, "Gross Margin by Farm (sum over j,m)", "€/yr", "GM_by_farm.png")

def gm_by_j(csv_path="GM_lane.csv"):
    df = parse_gdx_dump(csv_path)
    s = df.groupby("j")["value"].sum().sort_values(ascending=True)  # €/yr by plant
    save_bar(s, "Gross Margin by Plant (sum over i,m)", "€/yr", "GM_by_plant.png")

def main():
    files = {
        "UC_lane.csv": uc_lane_total,
        "UM_lane.csv": um_lane_total,
        "GM_lane.csv": gm_lane_total,
        ("Rev_lane.csv","Cost_lane.csv"): rev_cost_grouped,
        "BE_radius.csv": be_radius,
        "UC_lane.csv*ij": uc_by_ij_sum_modes,
        "GM_lane.csv*i": gm_by_i,
        "GM_lane.csv*j": gm_by_j,
    }

    # Run what exists; skip cleanly if missing
    here = Path(".")
    print(f"[make_all_upstream_viz] looking in: {here.resolve()}")
    # 3-tuple charts
    if Path("UC_lane.csv").exists():
        print("  • UC_lane.csv -> UC charts")
        uc_lane_total("UC_lane.csv")
        uc_by_ij_sum_modes("UC_lane.csv")
    else:
        print("  • UC_lane.csv not found — skipping")

    if Path("UM_lane.csv").exists():
        print("  • UM_lane.csv -> UM charts")
        um_lane_total("UM_lane.csv")
    else:
        print("  • UM_lane.csv not found — skipping")

    if Path("GM_lane.csv").exists():
        print("  • GM_lane.csv -> GM charts")
        gm_lane_total("GM_lane.csv")
        gm_by_i("GM_lane.csv")
        gm_by_j("GM_lane.csv")
    else:
        print("  • GM_lane.csv not found — skipping")

    if Path("Rev_lane.csv").exists() and Path("Cost_lane.csv").exists():
        print("  • Rev_lane + Cost_lane -> grouped chart")
        rev_cost_grouped("Rev_lane.csv", "Cost_lane.csv")
    else:
        print("  • Rev_lane.csv or Cost_lane.csv missing — skipping grouped chart")

    # 2-tuple chart
    if Path("BE_radius.csv").exists():
        print("  • BE_radius.csv -> BE radius chart")
        be_radius("BE_radius.csv")
    else:
        print("  • BE_radius.csv not found — skipping")

    print(f"Done. PNGs saved in: {OUTDIR.resolve()}")

if __name__ == "__main__":
    main()
