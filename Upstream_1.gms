$ontext
UPSTREAM (farm -> plant) CHIPPING + HANDLING + TRANSPORT
- Sets: farms i, plants j, modes m.
- Objective: maximize GrossMargin = Revenue - VariableCost.
- Costs:
  * Chipping €/t from tractor + PTO chipper €/h divided by t/h throughput.
  * Handling €/t from loader+bucket (you can tune).
  * Transport = backhaul * distance * €/t-km by mode + a per-ton surcharge for body/trailer.
$offtext

*------------------*
* Sets & data      *
*------------------*
Sets
    i   "farms"           / i1*i3 /
    j   "plant sites"     / j1*j2 /
    m   "modes"           / tractor, truck / ;

Alias (i,ii);

Table dist(i,j) "km"
           j1   j2
    i1     20   60
    i2     45   30
    i3     80   25 ;

Parameter Supply(i) "as-received t/yr";
Supply('i1') = 1200 ;
Supply('i2') =  900 ;
Supply('i3') =  700 ;

Scalar Backhaul "1=one-way, 2=round-trip" / 2 / ;

*------------------*
* KTBL-based inputs
*------------------*

* --- Chipping (tractor + PTO chipper) ---
Scalar Tractor_cost_per_h   "€/h Standardtraktor 120 kW"           / 41.84 /;
Scalar PTOChipper_cost_per_h "€/h Holzhacker PTO 25 m3/h"          / 22.63 /;
Scalar Chipper_m3_per_h     "m3/h PTO chipper"                     / 25    /;
Scalar Chip_bulk_density    "t/m3 (loose chips; adjust)"           / 0.30  /;

Scalar Chipper_t_per_h      "t/h";
Chipper_t_per_h = Chipper_m3_per_h * Chip_bulk_density ;

Scalar C_chip_eurt          "€/t chipping cost";
C_chip_eurt = (Tractor_cost_per_h + PTOChipper_cost_per_h) / max(1e-6, Chipper_t_per_h) ;

* --- Handling (front loader + light-goods bucket) ---
Scalar Loader_cost_per_h    "€/h Traktorfrontlader 3000 daN"       / 8.68  /;
Scalar Bucket_cost_per_t    "€/t Leichtgutschaufel 1.5 m3 (KTBL)"  / 0.12  /;
Scalar Handling_prod_tph    "t/h achievable loading rate"          / 20    /;

Scalar C_handle_eurt "€/t handling (load+unload)";
C_handle_eurt = Bucket_cost_per_t + Loader_cost_per_h / max(1e-6, Handling_prod_tph) ;

* --- Transport (mode-specific) ---
Parameter C_tkm(m)      "€/t-km";
Parameter C_surcharge(m)"€/t per trip/body";

* choose values (illustrative; replace with your derived ones)
C_tkm('tractor')      = 0.18 ;  C_surcharge('tractor') = 0.50 ;
C_tkm('truck')        = 0.12 ;  C_surcharge('truck')   = 0.80 ;

*------------------*
* Economics        *
*------------------*
Scalar P_chip "€/t revenue (or gate fee if negative)" / 0 / ;

* Optionally cap receipts at each site (e.g., annual demand upper bound)
Parameter DemandUB(j) "t/yr max accepted at plant site";
DemandUB(j) = +inf ;

*------------------*
* Variables        *
*------------------*
Positive Variables
    x(i,j,m)      "flow t/yr from farm i to plant j by mode m" ;

Variable
    Revenue       "€/yr"
    VarCost       "€/yr"
    GrossMargin   "€/yr objective" ;

*------------------*
* Equations        *
*------------------*
Equations
    SupplyLim(i)
    DemandLim(j)
    RevenueDef
    CostDef
    ObjDef ;

SupplyLim(i)..   sum((j,m), x(i,j,m)) =l= Supply(i) ;

DemandLim(j)..   sum((i,m), x(i,j,m)) =l= DemandUB(j) ;

RevenueDef..     Revenue =e= P_chip * sum((i,j,m), x(i,j,m)) ;

CostDef..
    VarCost =e=
        (C_chip_eurt + C_handle_eurt) * sum((i,j,m), x(i,j,m))
      + sum((i,j,m), (Backhaul * dist(i,j) * C_tkm(m) + C_surcharge(m)) * x(i,j,m)) ;

ObjDef..         GrossMargin =e= Revenue - VarCost ;

Model Upstream / all / ;

* maximize gross margin (if P_chip=0 this will choose zero flow unless you fix a minimum)
Solve Upstream using LP maximizing GrossMargin ;

Display C_chip_eurt, C_handle_eurt, C_tkm, C_surcharge, GrossMargin.l, x.l ;
