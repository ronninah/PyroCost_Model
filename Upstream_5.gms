*======================================================================*
*  Pyrolysis Upstream: Chipping + Handling + Transport (Farm -> Plant) *
*  KTBL-driven costs + LABOR adders (Option B only)                    *
*======================================================================*

$onText
This version:
- Keeps only Option B (profit maximization).
- Uses KTBL-driven machine costs; labor toggles are active (IncludeLabor=1).
- Computes Supply(i) from area, α_wood (24/48/96 m alleys), SRC yield, losses, MC.
- Transport modes: tractor & truck with fixed-per-ton overhead + €/t·km.
- Backhaul = 2 (two-way distance).
- Feedstock price set once via scalar FeedstockPrice; applies to all plants
  (or uncomment per-plant if needed).
$offText

*------------------*
* Sets & distances *
*------------------*
Sets
    i   "farms (alley-width scenarios)" / i1*i3 /
    j   "plants"                         / j1*j2 /
    m   "modes"                          / tractor, truck / ;
Alias (i,ii);

Table dist(i,j)  "km"
           j1   j2
i1         20   60
i2         45   30
i3         80   25 ;

*----------------------------------------------*
* Geometry (ALMA): α_wood from 6 m tree strip  *
*----------------------------------------------*
Parameter AlleyWidth_m(i)  "crop alley width (m)"
          TreeStrip_m      "tree strip total width (m)"
          alphaWood(i)     "wooded share of farm area (fraction)";

AlleyWidth_m("i1") = 24 ;
AlleyWidth_m("i2") = 48 ;
AlleyWidth_m("i3") = 96 ;
TreeStrip_m        = 6 ;

alphaWood(i) = TreeStrip_m / (TreeStrip_m + AlleyWidth_m(i));

*------------------------------*
* Supply (endogenous, as-recv) *
*------------------------------*
Scalar
  A_ha        "Farm arable area (ha, same for all i)"           / 200 /
  Y_SR_DM     "SRC baseline yield (t DM/ha/yr)"                 / 16  /
  delta_edge  "Edge-effect uplift (fraction)"                   / 0.40/
  lambdaLoss  "Harvest/handling loss fraction"                  / 0.05/
  MC          "Moisture content of delivered chips (fraction)"  / 0.35/ ;

Parameter Supply(i) "as-received t/yr (computed)";
Supply(i) = (A_ha * alphaWood(i) * Y_SR_DM * (1 + delta_edge) * (1 - lambdaLoss))
            / max(1e-6, 1 - MC) ;
display Supply;

Scalar Backhaul "1=one-way, 2=round-trip" / 2 / ;

*------------------------------*
* KTBL machine inputs (no labor)
*------------------------------*
Scalar
  Tractor_eur_per_h      "€/h Standardtraktor 120 kW (KTBL)"          / 41.84 /
  PTOChipper_eur_per_h   "€/h Holzhacker PTO 25 m3/h (KTBL)"          / 22.63 /
  Body_Tractor_eur_per_t "€/t Häckselaufbau 22 m3 (KTBL)"             / 0.82  /
  SemiTrailer_eur_per_t  "€/t Sattelzugauflieger 34 t (KTBL)"         / 0.89  /
  Bucket_eur_per_t       "€/t Leichtgutschaufel 1.5 m3 (KTBL)"        / 0.39  /
  FrontLoader_eur_per_h  "€/h Traktorfrontlader (KTBL)"               /  8.68 /
  Tractor_speed_kmh      "km/h (tractor road speed, KTBL sheet)"      / 40    /
  Chipper_m3_per_h       "m3/h (nameplate / KTBL)"                    / 25    /;

Scalar
  BulkDensity_t_per_m3   "t/m3 loose chips (KTBL/ALMA)"                / 0.30 /
  Handling_tph           "t/h sustained load+unload (KTBL sheet)"       / 20   /;

*------------------------------*
* Labor settings (toggles)
*------------------------------*
Scalar
  IncludeLabor           "1=include operator labor; 0=exclude"         / 1 /
  IncludeChipOp          "1=pay chipper operator in chipping"          / 1 /
  IncludeLoader          "1=pay loader operator in handling"           / 1 /
  IncludeDriver          "1=pay driver labor for transport"            / 1 /
  AddLaborToTruckTkm     "1=add driver labor to truck tkm; 0=skip"     / 1 / ;

* Wages (Germany 2025 minimum)
Scalar
  WageBase_eur_per_h     "EUR/h statutory minimum (2025-01-01)"        / 12.82 /
  OncostFrac             "employer on-costs fraction (social etc.)"    / 0.22  /
  Wage_eur_per_h         "EUR/h wage incl. on-costs" ;
Wage_eur_per_h = WageBase_eur_per_h * (1 + OncostFrac);

* Truck kinematics if splitting machine vs labor (can be in KTBL sheet)
Scalar
  Truck_speed_kmh        "km/h (regional haul; KTBL/loggers)"          / 70 /
  PayloadTruck_t         "t payload (semi)"                            / 25 / ;

*------------------------------*
* Derived capacities
*------------------------------*
Scalar
  PayloadTractor_t "t payload for tractor plus 22 m3 chip box" ;
PayloadTractor_t = 22 * BulkDensity_t_per_m3;

*------------------------------*
* Unit cost components
*------------------------------*
Scalar
  C_chip_eurt_mach   "EUR/t chipping (machine-only)"
  C_hand_eurt_mach   "EUR/t handling (machine-only)" ;
C_chip_eurt_mach = (Tractor_eur_per_h + PTOChipper_eur_per_h)
                 / max(1e-6, Chipper_m3_per_h * BulkDensity_t_per_m3);
C_hand_eurt_mach = Bucket_eur_per_t
                 + FrontLoader_eur_per_h / max(1e-6, Handling_tph);

Scalar
  Labor_chip_hpt  "h per t for chipping"
  Labor_hand_hpt  "h per t for load plus unload" ;
Labor_chip_hpt = 1 / max(1e-6, Chipper_m3_per_h * BulkDensity_t_per_m3);
Labor_hand_hpt = 1 / max(1e-6, Handling_tph);

Scalar
  C_chip_eurt_lab   "EUR/t chipping labor"
  C_hand_eurt_lab   "EUR/t handling labor" ;
C_chip_eurt_lab = IncludeLabor * IncludeChipOp * Wage_eur_per_h * Labor_chip_hpt;
C_hand_eurt_lab = IncludeLabor * IncludeLoader * Wage_eur_per_h * Labor_hand_hpt;

Scalar
  C_chip_eurt   "EUR/t chipping (machine plus labor)"
  C_handle_eurt "EUR/t handling (machine plus labor)" ;
C_chip_eurt   = C_chip_eurt_mach + C_chip_eurt_lab;
C_handle_eurt = C_hand_eurt_mach + C_hand_eurt_lab;

Parameter C_surcharge(m) "EUR/t per trip/body (KTBL)";
C_surcharge('tractor') = Body_Tractor_eur_per_t ;
C_surcharge('truck')   = SemiTrailer_eur_per_t  ;

Parameter C_tkm(m) "EUR per t-km by mode" ;
Scalar
  C_tkm_trac_mach  "EUR per t-km tractor machine"
  C_tkm_trac_lab   "EUR per t-km tractor driver labor"
  C_tkm_truck_mach "EUR per t-km truck machine (table/placeholder)"
  C_tkm_truck_lab  "EUR per t-km truck driver labor" ;

C_tkm_trac_mach = Tractor_eur_per_h
                  / max(1e-6, Tractor_speed_kmh * PayloadTractor_t);
C_tkm_trac_lab  = IncludeLabor * IncludeDriver * Wage_eur_per_h
                  / max(1e-6, Tractor_speed_kmh * PayloadTractor_t);

C_tkm_truck_mach = 0.12 ;
C_tkm_truck_lab  = IncludeLabor * IncludeDriver * AddLaborToTruckTkm
                  * Wage_eur_per_h / max(1e-6, Truck_speed_kmh * PayloadTruck_t);

C_tkm('tractor') = C_tkm_trac_mach + C_tkm_trac_lab;
C_tkm('truck')   = C_tkm_truck_mach + C_tkm_truck_lab;

*------------------*
* Economics (per-plant prices)
*------------------*
Parameter P_chip(j) "€/t DM paid at plant gate by plant"
/ j1 25
, j2 20 / ;

Parameter DemandUB(j) "t/yr max accepted at plant";
DemandUB(j) = +inf ;

* Scenarios for quick comparison (optional)
Set scen / base, highJ1, equal50 /;

Parameter Pchip_scen(j,scen) "€/t DM per plant per scenario";


display Pchip_scen, GM_total_scen;


*------------------*
* Variables
*------------------*
Positive Variables
    x(i,j,m)   "t/yr shipped from i to j by mode m" ;

Variables
    Revenue     "€/yr"
    VarCost     "€/yr"
    GrossMargin "€/yr objective" ;

*------------------*
* Equations
*------------------*
Equations
    SupplyLim(i)    "sum x <= Supply(i)"
    DemandLim(j)    "sum x <= DemandUB(j)"
    RevenueDef      "Revenue definition"
    CostDef         "Cost definition (machine+labor)"
    ObjDef          "GrossMargin = Revenue - VarCost";

SupplyLim(i)..   sum((j,m), x(i,j,m)) =l= Supply(i) ;
DemandLim(j)..   sum((i,m), x(i,j,m)) =l= DemandUB(j) ;

RevenueDef.. Revenue =e= sum((i,j,m), P_chip(j) * x(i,j,m));

CostDef..
    VarCost =e=
        (C_chip_eurt + C_handle_eurt) * sum((i,j,m), x(i,j,m))
      + sum((i,j,m), (Backhaul * dist(i,j) * C_tkm(m) + C_surcharge(m)) * x(i,j,m));

ObjDef..  GrossMargin =e= Revenue - VarCost ;

*------------------*
* Solve (Option B)
*------------------*
option limrow=0, limcol=0;
Display A_ha, alphaWood, Y_SR_DM, delta_edge, lambdaLoss, MC, Supply,
        C_chip_eurt, C_handle_eurt, C_tkm, C_surcharge, Wage_eur_per_h, P_chip;

Model Upstream_B "Option B: Maximize profit (with labor toggles)"
/ SupplyLim, DemandLim, RevenueDef, CostDef, ObjDef /;

solve Upstream_B using LP maximizing GrossMargin ;

*==============================================================*
* Post-solve analytics: location-aware gross margin            *
*==============================================================*
Parameter
  UC_lane(i,j,m)  "€/t unit cost per lane i->j,m"
  UR_j(j)         "€/t unit revenue at plant j"
  UM_lane(i,j,m)  "€/t unit margin per lane (UR - UC)"
  Xsol(i,j,m)     "t/yr shipped"
  Rev_lane(i,j,m) "€/yr revenue by lane"
  Cost_lane(i,j,m)"€/yr cost by lane"
  GM_lane(i,j,m)  "€/yr gross margin by lane"
  Rev_site(j)     "€/yr revenue at plant j"
  Cost_site(j)    "€/yr cost at plant j"
  GM_site(j)      "€/yr gross margin at plant j"
  GM_farm(i)      "€/yr gross margin by farm i"
  GM_mode(m)      "€/yr gross margin by mode m"
  GM_total        "€/yr total gross margin"
  BE_price(i,j,m) "€/t break-even price per lane"
  BE_radius(j,m)  "km one-way break-even distance (by mode at plant)";

UC_lane(i,j,m) = (C_chip_eurt + C_handle_eurt)
               + (Backhaul * dist(i,j) * C_tkm(m) + C_surcharge(m));
UR_j(j)        = P_chip(j);
UM_lane(i,j,m) = UR_j(j) - UC_lane(i,j,m);

Xsol(i,j,m)      = x.l(i,j,m);
Rev_lane(i,j,m)  = UR_j(j) * Xsol(i,j,m);
Cost_lane(i,j,m) = UC_lane(i,j,m) * Xsol(i,j,m);
GM_lane(i,j,m)   = Rev_lane(i,j,m) - Cost_lane(i,j,m);

Rev_site(j) = sum((i,m), Rev_lane(i,j,m));
Cost_site(j)= sum((i,m), Cost_lane(i,j,m));
GM_site(j)  = Rev_site(j) - Cost_site(j);

GM_farm(i)  = sum((j,m), GM_lane(i,j,m));
GM_mode(m)  = sum((i,j), GM_lane(i,j,m));
GM_total    = sum((i,j,m), GM_lane(i,j,m));

BE_price(i,j,m) = UC_lane(i,j,m);
BE_radius(j,m)  = max(0,
                      (UR_j(j) - (C_chip_eurt + C_handle_eurt) - C_surcharge(m))
                      / max(1e-6, Backhaul * C_tkm(m)) );

Display
  UR_j, UC_lane, UM_lane,
  Rev_lane, Cost_lane, GM_lane,
  Rev_site, Cost_site, GM_site, GM_farm, GM_mode, GM_total,
  BE_price, BE_radius;

put_utility 'log' / '--- Location-aware GM report generated (Option B, labor toggles).';

*=== MIRO/Excel outputs ===*
$onExternalOutput
Parameter
  Flow(i,j,m)       "t/yr shipped"
  FlowIJ(i,j)       "t/yr shipped (sum over modes)"
  SiteGM(j)         "€/yr GM per plant"
  TotalGM           "€/yr total GM"
  MIRO_dist(i,j)    "km distance (copy of dist)"
  UClane(i,j,m)     "€/t unit cost per lane (copy of UC_lane)"
  UMlane(i,j,m)     "€/t unit margin per lane (copy of UM_lane)"
  BErad(j,m)        "km break-even radius (one-way; copy of BE_radius)"
  Pprice(j)         "€/t chip price (copy of P_chip for charts)"
;
$offExternalOutput

Flow(i,j,m)   = x.l(i,j,m);
FlowIJ(i,j)   = sum(m, x.l(i,j,m));
SiteGM(j)     = sum((i,m), P_chip(j)*x.l(i,j,m)
                 - ((C_chip_eurt + C_handle_eurt)
                    + (Backhaul*dist(i,j)*C_tkm(m) + C_surcharge(m)))*x.l(i,j,m));
TotalGM       = sum(j, SiteGM(j));

MIRO_dist(i,j) = dist(i,j);
UClane(i,j,m)  = UC_lane(i,j,m);
UMlane(i,j,m)  = UM_lane(i,j,m);
BErad(j,m)     = BE_radius(j,m);
Pprice(j)      = P_chip(j);

execute_unload 'miro_out.gdx',
  i, j, m,
  Flow, FlowIJ, SiteGM, TotalGM,
  MIRO_dist, UClane, UMlane, BErad, Pprice ;

execute_unload 'excel_out.gdx',
   i, j, m,
   dist, UC_lane, UR_j, UM_lane, BE_price, BE_radius,
   Rev_lane, Cost_lane, GM_lane, GM_farm, GM_site, GM_mode, GM_total ;

$call gdxdump excel_out.gdx symb=UC_lane    > UC_lane.csv
$call gdxdump excel_out.gdx symb=UM_lane    > UM_lane.csv
$call gdxdump excel_out.gdx symb=BE_radius  > BE_radius.csv
$call gdxdump excel_out.gdx symb=Rev_lane   > Rev_lane.csv
$call gdxdump excel_out.gdx symb=Cost_lane  > Cost_lane.csv
$call gdxdump excel_out.gdx symb=GM_lane    > GM_lane.csv

*==============================*
* Price scenarios (optional)   *
*==============================*
Set scen / base, highJ1, equal50 /;

Parameter Pchip_scen(j,scen) "€/t DM per plant per scenario"
/ j1.base     25,  j2.base     20
, j1.highJ1   60,  j2.highJ1   45
, j1.equal50  50,  j2.equal50  50 / ;

* containers
Parameter GM_total_scen(scen)        "€/yr total GM by scenario";
Parameter Flow_scen(i,j,m,scen)      "t/yr shipped by lane per scenario";
Parameter UM_lane_scen(i,j,m,scen)   "€/t unit margin per lane per scenario";

loop(scen,
  * set prices for this scenario
  P_chip(j) = Pchip_scen(j,scen);

  * solve
  solve Upstream_B using LP maximizing GrossMargin ;

  * recompute analytics for this scenario (same formulas as above)
  Xsol(i,j,m)      = x.l(i,j,m);
  UR_j(j)          = P_chip(j);
  UC_lane(i,j,m)   = (C_chip_eurt + C_handle_eurt)
                   + (Backhaul * dist(i,j) * C_tkm(m) + C_surcharge(m));
  UM_lane(i,j,m)   = UR_j(j) - UC_lane(i,j,m);
  Rev_lane(i,j,m)  = UR_j(j) * Xsol(i,j,m);
  Cost_lane(i,j,m) = UC_lane(i,j,m) * Xsol(i,j,m);
  GM_lane(i,j,m)   = Rev_lane(i,j,m) - Cost_lane(i,j,m);
  GM_total         = sum((i,j,m), GM_lane(i,j,m));

  * store
  GM_total_scen(scen)      = GM_total;
  Flow_scen(i,j,m,scen)    = Xsol(i,j,m);
  UM_lane_scen(i,j,m,scen) = UM_lane(i,j,m);
);

display Pchip_scen, GM_total_scen;