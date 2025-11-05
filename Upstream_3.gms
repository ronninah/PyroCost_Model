*======================================================================*
*  Pyrolysis Upstream: Chipping + Handling + Transport (Farm -> Plant) *
*  KTBL-driven costs + LABOR adders (Option B only)                     *
*======================================================================*

$onText
This version:
- Keeps only Option B (profit maximization).
- Adds labor cost to chipping, handling, and transport with toggles.
- Leaves exports & post-solve analytics unchanged in shape.
$offText

*------------------*
* Sets & data      *
*------------------*
Sets
    i   "farms"       / i1*i3 /
    j   "plants"      / j1*j2 /
    m   "modes"       / tractor, truck / ;
Alias (i,ii);

Table dist(i,j)  "km"
           j1   j2
i1         20   60
i2         45   30
i3         80   25 ;

Parameter Supply(i) "as-received t/yr";
Supply('i1') = 1200 ;
Supply('i2') =  900 ;
Supply('i3') =  700 ;

Scalar Backhaul "1=one-way, 2=round-trip" / 2 / ;

*------------------------------*
* KTBL machine inputs          *
* (machine-only; no labor)     *
*------------------------------*
Scalar
  Tractor_eur_per_h      "€/h Standardtraktor 120 kW (KTBL)"          / 41.84 /
  PTOChipper_eur_per_h   "€/h Holzhacker PTO 25 m3/h (KTBL)"          / 22.63 /
  Body_Tractor_eur_per_t "€/t Häckselaufbau 22 m3 (KTBL)"             / 0.82  /
  SemiTrailer_eur_per_t  "€/t Sattelzugauflieger 34 t (KTBL)"         / 0.89  /
  Bucket_eur_per_t       "€/t Leichtgutschaufel 1.5 m3 (KTBL)"        / 0.39  /
  FrontLoader_eur_per_h  "€/h Traktorfrontlader (KTBL)"               / 8.68  /
  Tractor_speed_kmh      "km/h (tractor road speed)"                  / 40    /
  Chipper_m3_per_h       "m3/h (nameplate)"                           / 25    /;

Scalar
  BulkDensity_t_per_m3   "t/m3 loose chips"                            / 0.30 /
  Handling_tph           "t/h sustained load+unload"                    / 20   /;

*------------------------------*
* Labor settings (toggles)     *
*------------------------------*
Scalar
  IncludeLabor           "1=include operator labor; 0=exclude"         / 1 /
  IncludeChipOp          "1=pay chipper operator in chipping"          / 1 /
  IncludeLoader          "1=pay loader operator in handling"           / 1 /
  IncludeDriver          "1=pay driver labor for transport"            / 1 /
  AddLaborToTruckTkm     "1=add driver labor to truck tkm; 0=skip"     / 1 / ;

* Wages (Germany 2025 minimum)
Scalar
  WageBase_eur_per_h     "EUR/h statutory minimum (from 2025-01-01)"   / 12.82 /
  OncostFrac             "employer on-costs fraction (social etc.)"    / 0.22  /
  Wage_eur_per_h         "EUR/h wage incl. on-costs" ;
Wage_eur_per_h = WageBase_eur_per_h * (1 + OncostFrac);

* Transport assumptions for truck if splitting machine vs labor
Scalar
  Truck_speed_kmh        "km/h (typical regional haul)"                / 70 /
  PayloadTruck_t         "t payload (semi)"                            / 25 / ;

*------------------------------*
* Derived capacities           *
*------------------------------*
Scalar
  PayloadTractor_t "t payload for tractor plus 22 m3 chip box" ;
PayloadTractor_t = 22 * BulkDensity_t_per_m3;

*------------------------------*
* Unit cost components         *
*------------------------------*
* Machine-only parts
Scalar
  C_chip_eurt_mach   "EUR/t chipping (machine-only)"
  C_hand_eurt_mach   "EUR/t handling (machine-only)" ;
C_chip_eurt_mach = (Tractor_eur_per_h + PTOChipper_eur_per_h)
                 / max(1e-6, Chipper_m3_per_h * BulkDensity_t_per_m3);
C_hand_eurt_mach = Bucket_eur_per_t
                 + FrontLoader_eur_per_h / max(1e-6, Handling_tph);

* Labor intensities (hours per ton)
Scalar
  Labor_chip_hpt  "h per t for chipping"
  Labor_hand_hpt  "h per t for load plus unload" ;
Labor_chip_hpt = 1 / max(1e-6, Chipper_m3_per_h * BulkDensity_t_per_m3);
Labor_hand_hpt = 1 / max(1e-6, Handling_tph);

* Labor adders (EUR per t)
Scalar
  C_chip_eurt_lab   "EUR/t chipping labor"
  C_hand_eurt_lab   "EUR/t handling labor" ;
C_chip_eurt_lab = IncludeLabor * IncludeChipOp * Wage_eur_per_h * Labor_chip_hpt;
C_hand_eurt_lab = IncludeLabor * IncludeLoader * Wage_eur_per_h * Labor_hand_hpt;

* Total chipping/handling (used in model)
Scalar
  C_chip_eurt   "EUR/t chipping (machine plus labor)"
  C_handle_eurt "EUR/t handling (machine plus labor)" ;
C_chip_eurt   = C_chip_eurt_mach + C_chip_eurt_lab;
C_handle_eurt = C_hand_eurt_mach + C_hand_eurt_lab;

* Distance-independent surcharges
Parameter C_surcharge(m) "EUR/t per trip/body" ;
C_surcharge('tractor') = Body_Tractor_eur_per_t ;
C_surcharge('truck')   = SemiTrailer_eur_per_t  ;

* Transport EUR per t-km: machine and labor parts
Parameter C_tkm(m) "EUR per t-km by mode" ;
Scalar
  C_tkm_trac_mach  "EUR per t-km tractor machine"
  C_tkm_trac_lab   "EUR per t-km tractor driver labor"
  C_tkm_truck_mach "EUR per t-km truck machine (placeholder)"
  C_tkm_truck_lab  "EUR per t-km truck driver labor" ;

C_tkm_trac_mach = Tractor_eur_per_h
                  / max(1e-6, Tractor_speed_kmh * PayloadTractor_t);
C_tkm_trac_lab  = IncludeLabor * IncludeDriver * Wage_eur_per_h
                  / max(1e-6, Tractor_speed_kmh * PayloadTractor_t);

* Replace the placeholder when you have truck head EUR/h machine-only
C_tkm_truck_mach = 0.12 ;
C_tkm_truck_lab  = IncludeLabor * IncludeDriver * AddLaborToTruckTkm
                  * Wage_eur_per_h / max(1e-6, Truck_speed_kmh * PayloadTruck_t);

C_tkm('tractor') = C_tkm_trac_mach + C_tkm_trac_lab;
C_tkm('truck')   = C_tkm_truck_mach + C_tkm_truck_lab; 

*------------------*
* Economics        *
*------------------*
Parameter P_chip(j) "€/t price at plant (positive) or gate fee (negative)";
P_chip('j1') = 25 ;
P_chip('j2') = 20 ;

Parameter DemandUB(j) "t/yr max accepted at plant";
DemandUB(j) = +inf ;

*------------------*
* Variables        *
*------------------*
Positive Variables
    x(i,j,m)   "t/yr shipped from i to j by mode m" ;

Variables
    Revenue     "€/yr"
    VarCost     "€/yr"
    GrossMargin "€/yr objective" ;

*------------------*
* Equations        *
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
* Solve (Option B) *
*------------------*
option limrow=0, limcol=0;
Display C_chip_eurt, C_handle_eurt, C_tkm, C_surcharge, Wage_eur_per_h;

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
