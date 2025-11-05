*=========== Plant-first payable price & radius (j1) ===========*

Set p / j1 /, e / elec, heat /, m / tractor, truck / ;

*--- Plant brochure & economics ---
Parameter
   Qin_DM_h(p)       "t DM/h"
   Y_char(p)         "t char per t DM"
   E_net_kW(p,e)     "kW"
   Hop_year          "h/year"
   P_char            "EUR/t"
   P_el              "EUR/kWh"
   P_heat            "EUR/kWh_th"
   n_ops(p)          "operators per shift"
   w_hour            "EUR/h"
   OM_hour(p)        "EUR/h"
   P_buy             "EUR/kWh"
   E_buy_kWh(p)      "kWh/h"
   MarginTarget      "EUR/h target gross margin (0 = breakeven)" ;

Qin_DM_h('j1')        = 0.299 ;
Y_char('j1')          = 0.25  ;
E_net_kW('j1','elec') = 130   ;
E_net_kW('j1','heat') = 200   ;
Hop_year              = 8000  ;

P_char                = 600   ;
P_el                  = 0.11  ;
P_heat                = 0.06  ;

n_ops('j1')           = 1     ;
w_hour                = 28    ;
OM_hour('j1')         = 30    ;
P_buy                 = 0.28  ;
E_buy_kWh('j1')       = 0     ;
MarginTarget          = 0     ;

Scalar MC_asrec "moisture content of delivered chips (fraction)" / 0.35 / ;

*--- Revenues & non-feedstock costs (hourly) ---
Parameter
   Qchar_h(p)  "t/h"
   Rchar(p)    "EUR/h"
   Rel(p)      "EUR/h"
   Rheat(p)    "EUR/h"
   Rev(p)      "EUR/h"
   Clab(p)     "EUR/h"
   Com(p)      "EUR/h"
   Cbuy(p)     "EUR/h" ;

Qchar_h(p) = Y_char(p) * Qin_DM_h(p) ;
Rchar(p)   = P_char * Qchar_h(p) ;
Rel(p)     = P_el   * E_net_kW(p,'elec') ;
Rheat(p)   = P_heat * E_net_kW(p,'heat') ;
Rev(p)     = Rchar(p) + Rel(p) + Rheat(p) ;

Clab(p) = n_ops(p) * w_hour ;
Com(p)  = OM_hour(p) ;
Cbuy(p) = P_buy * E_buy_kWh(p) ;

*--- Max payable chip price at plant gate (EUR/t DM) ---
Parameter P_chip_payable(p) "EUR/t DM, breakeven w.r.t. MarginTarget" ;
P_chip_payable(p) = ( Rev(p) - (Clab(p) + Com(p) + Cbuy(p)) - MarginTarget ) / Qin_DM_h(p) ;

*=========== KTBL-style cost building blocks (same structure as upstream) ===========
Scalar
  Tractor_eur_per_h      "€/h" / 41.84 /
  PTOChipper_eur_per_h   "€/h" / 22.63 /
  Body_Tractor_eur_per_t "€/t" / 0.82  /
  SemiTrailer_eur_per_t  "€/t" / 0.89  /
  Bucket_eur_per_t       "€/t" / 0.39  /
  FrontLoader_eur_per_h  "€/h" / 8.68  /
  Tractor_speed_kmh      "km/h" / 40 /
  Chipper_m3_per_h       "m3/h" / 25 /
  BulkDensity_t_per_m3   "t/m3" / 0.30 /
  Handling_tph           "t/h"  / 20  /
  Truck_speed_kmh        "km/h" / 70 /
  PayloadTruck_t         "t"    / 25 /
  Backhaul               "1=one-way,2=round-trip" / 2 / ;

Scalar PayloadTractor_t "t payload for 22 m3 chip box" ;
PayloadTractor_t = 22 * BulkDensity_t_per_m3 ;

* Labor toggles and wage (as in upstream)
Scalar IncludeLabor / 1 /, IncludeChipOp / 1 /, IncludeLoader / 1 /, IncludeDriver / 1 /, AddLaborToTruckTkm / 1 / ;
Scalar WageBase_eur_per_h / 12.82 /, OncostFrac / 0.22 /, Wage_eur_per_h ;
Wage_eur_per_h = WageBase_eur_per_h * (1 + OncostFrac) ;

* Chipping & handling unit costs (EUR/t)
Scalar
  C_chip_eurt_mach "EUR/t"
  C_hand_eurt_mach "EUR/t"
  Labor_chip_hpt   "h/t"
  Labor_hand_hpt   "h/t"
  C_chip_eurt      "EUR/t"
  C_handle_eurt    "EUR/t" ;

C_chip_eurt_mach = (Tractor_eur_per_h + PTOChipper_eur_per_h) / (Chipper_m3_per_h * BulkDensity_t_per_m3) ;
C_hand_eurt_mach = Bucket_eur_per_t + FrontLoader_eur_per_h / Handling_tph ;
Labor_chip_hpt   = 1 / (Chipper_m3_per_h * BulkDensity_t_per_m3) ;
Labor_hand_hpt   = 1 / Handling_tph ;
C_chip_eurt      = C_chip_eurt_mach + IncludeLabor*IncludeChipOp*Wage_eur_per_h*Labor_chip_hpt ;
C_handle_eurt    = C_hand_eurt_mach + IncludeLabor*IncludeLoader*Wage_eur_per_h*Labor_hand_hpt ;

Parameter C_surcharge(m) "EUR/t per trip/body" ;
C_surcharge('tractor') = Body_Tractor_eur_per_t ;
C_surcharge('truck')   = SemiTrailer_eur_per_t  ;

Parameter C_tkm(m) "EUR per t-km by mode" ;
Scalar C_tkm_truck_mach / 0.12 / ;
C_tkm('tractor') = Tractor_eur_per_h/(Tractor_speed_kmh*PayloadTractor_t)
                 + IncludeLabor*IncludeDriver*Wage_eur_per_h/(Tractor_speed_kmh*PayloadTractor_t) ;
C_tkm('truck')   = C_tkm_truck_mach
                 + IncludeLabor*IncludeDriver*AddLaborToTruckTkm*Wage_eur_per_h/(Truck_speed_kmh*PayloadTruck_t) ;

*--- Break-even one-way radius by mode (km) for plant j1 ---
Parameter BE_radius(p,m) "km one-way" ;
BE_radius(p,m) = max(0,
   ( P_chip_payable(p) - (C_chip_eurt + C_handle_eurt + C_surcharge(m)) )
   / ( Backhaul * C_tkm(m) )
) ;

*--- Helpful annual KPIs at capacity ---
Parameter
  PayableBudget_yr(p) "EUR/yr payable to feedstock at capacity"
  CharOutput_yr(p)    "t/yr"
  Qin_asrec_yr(p)     "t/yr as-received needed at capacity" ;

PayableBudget_yr(p) = P_chip_payable(p) * Qin_DM_h(p) * Hop_year ;
CharOutput_yr(p)    = Y_char(p) * Qin_DM_h(p) * Hop_year ;
Qin_asrec_yr(p)     = Qin_DM_h(p) * Hop_year / (1 - MC_asrec) ;

Parameter P_chip_payable_asrec(p) "EUR/t as-received at MC_asrec";
P_chip_payable_asrec(p) = P_chip_payable(p) * (1 - MC_asrec);


Display P_chip_payable, P_chip_payable_asrec, BE_radius, PayableBudget_yr, CharOutput_yr, Qin_asrec_yr ;

*--- CSV output ---
File fo /plant_first_payable_radius_j1.csv/ ; put fo ;
put 'plant,P_chip_payable_EUR_per_tDM,P_chip_payable_EUR_per_t_asrec,BE_radius_tractor_km,BE_radius_truck_km,PayableBudget_yr_EUR,CharOutput_yr_t,Qin_asrec_yr_t' / ;
put 'j1',',', P_chip_payable('j1'):0:2, ',', P_chip_payable_asrec('j1'):0:2, ',', 
    BE_radius('j1','tractor'):0:2, ',', BE_radius('j1','truck'):0:2, ',',
    PayableBudget_yr('j1'):0:0, ',', CharOutput_yr('j1'):0:2, ',', Qin_asrec_yr('j1'):0:2 / ;
putclose fo ;