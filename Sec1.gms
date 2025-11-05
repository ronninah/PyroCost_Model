*-------------  COST-EFFICIENT PYROLYSIS / BIOCHAR PLANT (MILP)  -------------
* Nahid Hasan Ronnie
* Distance between farms and candidate plant sites enters via dist(i,j) [km]
* Transport tonne-km = backhaul * sum_i dist(i,j) * x(i,j)
*-----------------------------------------------------------------------------

* -------- TECHNOLOGY: Pyro-ClinX 150 (single unit) --------

$ontext
COST-EFFICIENT PYROLYSIS / BIOCHAR SITING & LOGISTICS (MILP)
- Distance appears via dist(i,j) in tonne-km cost and emissions.
- Integer number of identical units per site.
- One energy system per built site (can relax).
$offtext

* ---------- SETS ----------
Sets
    i   "biomass sources"           / i1*i3 /
    j   "candidate plant sites"     / j1*j2 /
    e   "energy systems"            / grid biomass_chp pvgrid /
    m   "transport modes"           / diesel ev / ;

* ---------- SCALARS ----------
Scalars
    r               "discount rate"                          / 0.08 /
    life            "economic lifetime (years)"              / 15    /
    CRF             "capital recovery factor"
    HoursPerYear    "operating hours per year"               / 8000  /
    backhaul        "t-km multiplier (1 one-way, 2 round-trip)"/ 2   /
    CarbonPrice     "EUR per tCO2e (0 to ignore)"            / 0     /
    Wage            "EUR per labor-hour"                     / 35    /
    LaborPerTon     "labor hours per t (as-received)"        / 0.2   /
    VarOMperTon     "variable O&M EUR per t (as-received)"   / 0     /
    FixOMFrac       "fixed O&M fraction of CAPEX (1/yr)"     / 0.05  /
    YieldChar       "t char per t dry feed"                  / 0.25  /
    MoistureASRdef  "default moisture fraction (as-received)"/ 0.05  /
    PriceChar       "EUR per t char (revenue)"               / 0     /
    CapexPerUnit    "EUR per pyrolysis unit"                 / 5000000 /
    CapUnit_asr_tpy "t/yr capacity per unit (as-received)"
    CO2perC         "tCO2 per tC"                            / 44/12 / ;

* For a Pyro-ClinX-like unit: 315 kg/h = 0.315 t/h
CapUnit_asr_tpy = 0.315 * HoursPerYear ;

* Capital recovery factor
CRF = r * power(1 + r, life) / ( power(1 + r, life) - 1 );

* ---------- PARAMETERS (demo data) ----------
Table dist(i,j) "distance from source i to site j (km)"
          j1   j2
    i1    20   60
    i2    45   30
    i3    80   25 ;

Parameter Supply(i)      "available feed at source i (t/yr, as-received)";
Supply("i1") = 1200 ;
Supply("i2") =  900 ;
Supply("i3") =  700 ;

Parameter MoistureASR(i) "as-received moisture fraction by source";
MoistureASR(i) = MoistureASRdef ;

Parameter Umax(j)        "max number of units allowed at site j";
Umax(j) = 2 ;

Parameter PriceElec(e)   "EUR per kWh";
PriceElec("grid")        = 0.18 ;
PriceElec("biomass_chp") = 0.06 ;
PriceElec("pvgrid")      = 0.12 ;

Parameter EFelec(e)      "kgCO2e per kWh";
EFelec("grid")        = 0.30 ;
EFelec("biomass_chp") = 0.05 ;
EFelec("pvgrid")      = 0.10 ;

Parameter CapexAddE(e)   "EUR add-on CAPEX by energy system";
CapexAddE(e) = 0 ;
CapexAddE("biomass_chp") = 1000000 ;
CapexAddE("pvgrid")      = 1500000 ;

Scalar ElecUse_kWh_per_tDry "kWh per t dry feed" / 200 / ;

Parameter CTrans(m)   "EUR per t-km";
CTrans("diesel") = 0.12 ;
CTrans("ev")     = 0.10 ;

Parameter EFtrans(m)  "kgCO2e per t-km";
EFtrans("diesel") = 0.10 ;
EFtrans("ev")     = 0.02 ;

* If you want per-ton-char sequestration as a scalar: uncomment and set.
* Scalar Sequest "tCO2e per t char" / 2.88 / ;

* Or derive sequestration from carbon content & stability (same for all sources here)
Scalar CfracChar "tC per t char"      / 0.80 / ;
Scalar StabFrac  "stable fraction (-)" / 0.75 / ;

Parameter kDry(i) "tCO2e credit per t DRY feed from source i";
kDry(i) = YieldChar * CfracChar * StabFrac * CO2perC ;

Scalar BigX "big-M for flows"    / 1e6 / ;
Scalar BigE "big-M for energy"   / 1e9 / ;
Scalar NumPlantsMax "optional plant count cap" / 2 / ;

* ---------- VARIABLES ----------
Positive Variables
    x(i,j,m)        "flow i->j via mode m (t/yr, as-received)"
    FeedASR(j)      "total as-received feed at site j (t/yr)"
    FeedDry(j)      "total dry feed at site j (t/yr)"
    Char(j)         "biochar at site j (t/yr)"
    EnergyUse(j)    "electricity use at site j (kWh/yr)"
    EnergyUse_e(j,e)"electricity by energy system (kWh/yr)"
    Tkm(j)          "tonne-km into site j (t-km/yr)" ;

* Objective must be FREE (not positive)
Variable
    TotalEmis       "total net emissions (tCO2e/yr)"
    TotalCost       "total annualized cost (EUR/yr)" ;

Binary Variables
    y(j)        "1 if site j is built"
    zE(j,e)     "1 if energy system e is chosen at site j" ;

Integer Variables
    u(j)        "number of units at site j (integer)" ;

* ---------- EQUATIONS ----------
Equations
    FeedAgg(j)
    FeedDryDef(j)
    CharDef(j)
    EnergyDef1(j)
    EnergyDef2(j)
    EnergyLink(j,e)
    SupplyLim(i)
    CapUB1(j)
    UnitBuildLink1(j)
    UnitBuildLink2(j)
    OneEnergy(j)
    TkmDef(j)
    ModeLink(i,j)
    EmisDef
    CostDef
    PlantCount ;

FeedAgg(j)..        FeedASR(j) =E= sum((i,m), x(i,j,m)) ;

FeedDryDef(j)..     FeedDry(j) =E= sum((i,m), x(i,j,m) * (1 - MoistureASR(i))) ;

CharDef(j)..        Char(j)    =E= YieldChar * FeedDry(j) ;

EnergyDef1(j)..     EnergyUse(j) =E= ElecUse_kWh_per_tDry * FeedDry(j) ;

EnergyDef2(j)..     sum(e, EnergyUse_e(j,e)) =E= EnergyUse(j) ;

EnergyLink(j,e)..   EnergyUse_e(j,e) =L= BigE * zE(j,e) ;

SupplyLim(i)..      sum((j,m), x(i,j,m)) =L= Supply(i) ;

CapUB1(j)..         FeedASR(j) =L= CapUnit_asr_tpy * u(j) ;

UnitBuildLink1(j).. u(j) =L= Umax(j) * y(j) ;

UnitBuildLink2(j).. y(j) =L= u(j) ;

OneEnergy(j)..      sum(e, zE(j,e)) =E= y(j) ;

TkmDef(j)..         Tkm(j) =E= backhaul * sum((i,m), dist(i,j) * x(i,j,m)) ;

ModeLink(i,j)..     sum(m, x(i,j,m)) =L= BigX * y(j) ;

* Emissions: energy + transport - sequestration (feed-based credit)
EmisDef..
    TotalEmis =E=
        sum((j,e), EFelec(e) * EnergyUse_e(j,e) / 1000)
      + sum((i,j,m), EFtrans(m) * backhaul * dist(i,j) * x(i,j,m) / 1000)
      - sum((i,j,m), kDry(i) * (1 - MoistureASR(i)) * x(i,j,m)) ;

* If you prefer a single per-ton-char factor, replace the last line with:
*    - Sequest * sum(j, Char(j))

CostDef..
    TotalCost =E=
        sum(j,
            CRF * CapexPerUnit * u(j)
          + FixOMFrac * CapexPerUnit * u(j)
          + sum(e, CRF * CapexAddE(e) * zE(j,e))
          + sum(e, PriceElec(e)       * EnergyUse_e(j,e))
        )
      + sum((i,j,m), CTrans(m) * backhaul * dist(i,j) * x(i,j,m))
      + Wage * LaborPerTon * sum(j, FeedASR(j))
      + VarOMperTon       * sum(j, FeedASR(j))
      + CarbonPrice * TotalEmis
      - PriceChar  * sum(j, Char(j)) ;

PlantCount..        sum(j, y(j)) =L= NumPlantsMax ;

Model BiocharCost / all / ;

option mip = cplex ;
Solve BiocharCost using MIP minimizing TotalCost ;

Scalar LCOB "EUR per t char" ;
LCOB = TotalCost.l / max(1e-6, sum(j, Char.l(j))) ;

Display TotalCost.l, TotalEmis.l, LCOB, y.l, u.l, zE.l, FeedASR.l, FeedDry.l, Char.l, Tkm.l, x.l ;
