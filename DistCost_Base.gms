*-------------  COST-EFFICIENT PYROLYSIS / BIOCHAR PLANT (MILP)  -------------
* Nahid Hasan Ronnie
* Distance between farms and candidate plant sites enters via dist(i,j) [km]
* Transport tonne-km = backhaul * sum_i dist(i,j) * x(i,j)
*-----------------------------------------------------------------------------

* -------- TECHNOLOGY: Pyro-ClinX 150 (single unit) --------

$ontext
Minimal distance–cost siting (single plant on 1D corridor)
- X: plant location (km). di(i) >= |X - pos_i(i)| via two inequalities.
- Must meet DemandChar > 0 so solution is never zero.
- Objective: transport + simple handling + annualized CAPEX.
$offtext

Set i "farms" / i1*i5 / ;

* --- Data (EDIT) ---
Parameter
    pos_i(i)       "farm position (km)"
    Supply(i)      "available as-received feed (t/yr)"
    Moisture(i)    "as-received moisture fraction";

pos_i("i1")=10 ; pos_i("i2")=35 ; pos_i("i3")=60 ; pos_i("i4")=85 ; pos_i("i5")=110 ;
Supply("i1")=800 ; Supply("i2")=900 ; Supply("i3")=700 ; Supply("i4")=600 ; Supply("i5")=500 ;
Moisture(i) = 0.05 ;

Scalar
    DemandChar      "required biochar (t/yr)"               / 500 /
    YieldChar       "t char per t dry feed"                 / 0.25 /
    backhaul        "t-km multiplier (1 one-way, 2 round)"  / 2    /
    CTrans          "EUR per t-km"                          / 0.12 /
    Wage            "EUR per labor-hour"                    / 35   /
    LaborPerTon     "labor hours per t feed"                / 0.2  /
    VarOMperTon     "variable O&M per t feed (EUR/t)"       / 0    /
    r               "discount rate"                         / 0.08 /
    life            "economic lifetime (y)"                 / 15   /
    CRF             "capital recovery factor"
    CapexPlant      "EUR plant CAPEX"                       / 5000000 /
    FixOMFrac       "fixed O&M as frac of CAPEX (1/y)"      / 0.05 / ;

CRF = r*power(1+r,life)/(power(1+r,life)-1) ;

Positive Variable
    x(i)        "flow from farm i (t/yr ASR)"
    di(i)       "distance to farm i (km)"
    FeedASR     "ASR feed total (t/yr)"
    FeedDry     "DRY feed total (t/yr)"
    Char        "biochar (t/yr)"
    Tkm         "tonne-km (t-km/yr)";

Variable
    X           "plant location (km)"
    TotalCost   "annual cost (EUR/yr)";

Scalar Xmin /0/, Xmax /200/; X.lo = Xmin ; X.up = Xmax ;

Equation
    SupplyLim(i)
    FeedAgg
    FeedDryDef
    CharDef
    DistLB1(i)      "di(i) >= X - pos_i(i)"
    DistLB2(i)      "di(i) >= pos_i(i) - X"
    TkmDef
    DemandReq
    CostDef ;

SupplyLim(i)..   x(i) =L= Supply(i) ;
FeedAgg..        FeedASR =E= sum(i, x(i)) ;
FeedDryDef..     FeedDry =E= sum(i, x(i)*(1 - Moisture(i))) ;
CharDef..        Char    =E= YieldChar * FeedDry ;

DistLB1(i)..     di(i) =G= X - pos_i(i) ;
DistLB2(i)..     di(i) =G= pos_i(i) - X ;

TkmDef..         Tkm =E= backhaul * sum(i, di(i) * x(i)) ;

DemandReq..      Char =G= DemandChar ;

CostDef..
  TotalCost =E=
      CRF*CapexPlant + FixOMFrac*CapexPlant
    + CTrans*Tkm
    + Wage*LaborPerTon*FeedASR
    + VarOMperTon*FeedASR ;

Model DistCost / all / ;
Solve DistCost using LP minimizing TotalCost ;

Display X.l, TotalCost.l, Char.l, FeedASR.l, FeedDry.l, Tkm.l, x.l, di.l ;
