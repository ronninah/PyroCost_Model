*======================================================================*
*  Pyrolysis Upstream: Chipping + Handling + Transport (Farm -> Plant) *
*  KTBL-driven cost derivations + Four modeling options (A..D)         *
*  OptionMode: 1=A MinCost, 2=B Profit, 3=C Profit+Penalty, 4=D Contract*
*======================================================================*

$onText
Option A — Cost minimization with required tonnages
  A(eq): sum_jm x = Supply(i)  (ship all supply)
  A(le): sum_jm x <= Supply(i) (ship up to supply) AND DemandMin(j) >= LB

Option B — Profit maximization (set P_chip(j) > 0)

Option C — Profit maximization with penalty for Unused(i)

Option D — Profit maximization with DemandCommit(j) >= Contract(j)

All options produce a location-aware report:
- UC_lane(i,j,m), UM_lane(i,j,m), GM_site(j), GM_farm(i), GM_mode(m)
- BE_price(i,j,m), BE_radius(j,m)
$offText

*-----------------------------*
* Choose modeling option here *
*-----------------------------*
Scalar OptionMode "1=A | 2=B | 3=C | 4=D" / 2 /;

* For Option A only: choose equality (ship all) vs inequality (ship up to)
Scalar UseSupplyEq "1: ship all supply (A-eq); 0: allow <= (A-le)" / 1 /;

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
* KTBL-derived unit costs      *
*------------------------------*
Scalar
  Tractor_eur_per_h      "€/h Standardtraktor 120 kW (KTBL)"          / 41.84 /
  PTOChipper_eur_per_h   "€/h Holzhacker PTO 25 m3/h (KTBL)"          / 22.63 /
  Body_Tractor_eur_per_t "€/t Häckselaufbau 22 m3 (KTBL)"             / 0.82  /
  SemiTrailer_eur_per_t  "€/t Sattelzugauflieger 34 t (KTBL)"         / 0.89  /
  Bucket_eur_per_t       "€/t Leichtgutschaufel 1.5 m3 (KTBL)"        / 0.39  /
  FrontLoader_eur_per_h  "€/h Traktorfrontlader (KTBL)"               / 8.68  /
  Tractor_speed_kmh      "km/h (KTBL: 40 km/h)"                       / 40    /
  Chipper_m3_per_h       "m3/h (nameplate)"                           / 25    /;

Scalar
  BulkDensity_t_per_m3   "t/m3 loose chips"                            / 0.30 /
  Handling_tph           "t/h sustained load+unload"                    / 20   /;

Scalar
  C_chip_eurt   "€/t chipping"
  C_handle_eurt "€/t handling (load+unload)"
  PayloadTractor_t "t payload for tractor+22m3 chip box";

Parameter
  C_tkm(m)       "€/t-km by mode"
  C_surcharge(m) "€/t distance-independent per trip/body";

C_chip_eurt = (Tractor_eur_per_h + PTOChipper_eur_per_h)
            / max(1e-6, Chipper_m3_per_h * BulkDensity_t_per_m3);

C_handle_eurt = Bucket_eur_per_t + FrontLoader_eur_per_h / max(1e-6, Handling_tph);

C_surcharge('tractor') = Body_Tractor_eur_per_t ;
C_surcharge('truck')   = SemiTrailer_eur_per_t  ;

PayloadTractor_t = 22 * BulkDensity_t_per_m3;
C_tkm('tractor') = Tractor_eur_per_h
                 / max(1e-6, Tractor_speed_kmh * PayloadTractor_t);

* Truck €/t·km: placeholder until KTBL “Zugmaschine (truck head)” €/h is added
C_tkm('truck')   = 0.12 ;

*------------------*
* Economics        *
*------------------*
Parameter P_chip(j) "€/t price at plant (positive) or gate fee (negative)";
P_chip('j1') = 25 ;
P_chip('j2') = 20 ;

Parameter DemandUB(j) "t/yr max accepted at plant";
DemandUB(j) = +inf ;

Parameter DemandLB(j) "t/yr min accepted at plant (Option A only)";
DemandLB(j) = 0 ;

Scalar Penalty_unused "€/t penalty for leaving supply (Option C)" / 6 /;

Parameter Contract(j) "t/yr minimum contracted at plant (Option D)";
Contract(j) = 0 ;

*------------------*
* Variables        *
*------------------*
Positive Variables
    x(i,j,m)   "t/yr shipped from i to j by mode m" ;

Variables
    Revenue     "€/yr"
    VarCost     "€/yr"
    GrossMargin "€/yr objective" ;

Positive Variable Unused(i) "t/yr unshipped supply (Option C)";

*------------------*
* Equations        *
*------------------*
Equations
    SupplyLim(i)    "sum x <= Supply(i) (B/C/D and A-le)"
    SupplyBal(i)    "sum x  = Supply(i) (A-eq)"
    SupplySplit(i)  "sum x + Unused = Supply(i) (Option C)"
    DemandLim(j)    "sum x <= DemandUB(j)"
    DemandMin(j)    "sum x >= DemandLB(j) (Option A)"
    DemandCommit(j) "sum x >= Contract(j) (Option D)"
    RevenueDef      "Revenue definition"
    CostDef         "Base cost definition"
    CostDefC        "Cost definition with penalty (Option C)"
    ObjDef          "GrossMargin = Revenue - VarCost";

SupplyLim(i)..   sum((j,m), x(i,j,m)) =l= Supply(i) ;
SupplyBal(i)..   sum((j,m), x(i,j,m)) =e= Supply(i) ;
SupplySplit(i).. sum((j,m), x(i,j,m)) + Unused(i) =e= Supply(i) ;
DemandLim(j)..   sum((i,m), x(i,j,m)) =l= DemandUB(j) ;
DemandMin(j)..   sum((i,m), x(i,j,m)) =g= DemandLB(j) ;
DemandCommit(j)..sum((i,m), x(i,j,m)) =g= Contract(j) ;

RevenueDef.. Revenue =e= sum((i,j,m), P_chip(j) * x(i,j,m));

CostDef..
    VarCost =e=
        (C_chip_eurt + C_handle_eurt) * sum((i,j,m), x(i,j,m))
      + sum((i,j,m), (Backhaul * dist(i,j) * C_tkm(m) + C_surcharge(m)) * x(i,j,m));

CostDefC..
    VarCost =e=
        (C_chip_eurt + C_handle_eurt) * sum((i,j,m), x(i,j,m))
      + sum((i,j,m), (Backhaul * dist(i,j) * C_tkm(m) + C_surcharge(m)) * x(i,j,m))
      + Penalty_unused * sum(i, Unused(i));

ObjDef..  GrossMargin =e= Revenue - VarCost ;

*------------------*
* Model variants   *
*------------------*
Model Upstream_A_eq "Option A(eq): MinCost, ship all supply"
/ SupplyBal, DemandMin, CostDef /;

Model Upstream_A_le "Option A(le): MinCost, ship up to supply"
/ SupplyLim, DemandMin, CostDef /;

Model Upstream_B "Option B: Maximize profit"
/ SupplyLim, DemandLim, RevenueDef, CostDef, ObjDef /;

Model Upstream_C "Option C: Maximize profit with unused penalty"
/ SupplySplit, DemandLim, RevenueDef, CostDefC, ObjDef /;

Model Upstream_D "Option D: Maximize profit with demand commitment"
/ SupplyLim, DemandLim, DemandCommit, RevenueDef, CostDef, ObjDef /;

*------------------*
* Solve by option  *
*------------------*
option limrow=0, limcol=0;
Display C_chip_eurt, C_handle_eurt, C_tkm, C_surcharge;

Scalar solvedMode /0/;

if(OptionMode = 1,
   if(UseSupplyEq = 1,
      solve Upstream_A_eq using LP minimizing VarCost ;
   else
      solve Upstream_A_le using LP minimizing VarCost ;
   );
   solvedMode = 1 ;
);

if(OptionMode = 2,
   solve Upstream_B using LP maximizing GrossMargin ;
   solvedMode = 2 ;
);

if(OptionMode = 3,
   solve Upstream_C using LP maximizing GrossMargin ;
   solvedMode = 3 ;
);

if(OptionMode = 4,
   solve Upstream_D using LP maximizing GrossMargin ;
   solvedMode = 4 ;
);

abort$(solvedMode=0) "Set OptionMode to 1(A) 2(B) 3(C) or 4(D).";

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

Scalar OptionUsed; OptionUsed = OptionMode;
put_utility 'log' / '--- Location-aware GM report generated. OptionMode = ' OptionUsed:0:0 ;



*=== MIRO: declare outputs (IDC) — graph-ready ===*
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

* Fill outputs
Flow(i,j,m)   = x.l(i,j,m);
FlowIJ(i,j)   = sum(m, x.l(i,j,m));
SiteGM(j)     = sum((i,m), P_chip(j)*x.l(i,j,m)
                 - ((C_chip_eurt + C_handle_eurt)
                    + (Backhaul*dist(i,j)*C_tkm(m) + C_surcharge(m)))*x.l(i,j,m));
TotalGM       = sum(j, SiteGM(j));

* Copies for charts (avoid re-declaring existing symbols)
MIRO_dist(i,j) = dist(i,j);
UClane(i,j,m)  = UC_lane(i,j,m);
UMlane(i,j,m)  = UM_lane(i,j,m);
BErad(j,m)     = BE_radius(j,m);
Pprice(j)      = P_chip(j);

* Export for MIRO
execute_unload 'miro_out.gdx',
  i, j, m,
  Flow, FlowIJ, SiteGM, TotalGM,
  MIRO_dist, UClane, UMlane, BErad, Pprice
;



execute_unload 'excel_out.gdx',
   i, j, m,
   dist, UC_lane, UR_j, UM_lane, BE_price, BE_radius, 
   Rev_lane, Cost_lane, GM_lane, GM_farm, GM_site, GM_mode, GM_total;
   


$call gdxdump excel_out.gdx symb=UC_lane > UC_lane.csv
$call gdxdump excel_out.gdx symb=UM_lane > UM_lane.csv
$call gdxdump excel_out.gdx symb=BE_radius > BE_radius.csv
$call gdxdump excel_out.gdx symb=Rev_lane > Rev_lane.csv
$call gdxdump excel_out.gdx symb=Cost_lane > Cost_lane.csv
$call gdxdump excel_out.gdx symb=GM_lane > GM_lane.csv