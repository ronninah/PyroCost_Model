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

P_char                = 550   ;
P_el                  = 0.11  ;
P_heat                = 0.06  ;

n_ops('j1')           = 1     ;
w_hour                = 28    ;
OM_hour('j1')         = 30    ;
P_buy                 = 0.28  ;
E_buy_kWh('j1')       = 0     ;
MarginTarget          = 0     ;

Scalar MC_asrec "moisture content of delivered chips (fraction)" / 0.25 / ;

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


* ===== Curve 1: Delivered cost (as-received) vs distance, plus payable line
Set r / r0*r200 /;
Alias (r, rr);
Set mplot(m) / tractor, truck /;

Scalar rstep / 1 /;

Parameter km(r)           "distance grid (km)"
          Cost_asrec(r,m) "EUR/t as-received delivered cost by mode"
          Pay_asrec(r)    "EUR/t as-received payable (flat line)"
          Diff(r,m)       "abs gap between cost and payable"
          IsBE(r,m)       "1 on nearest intersection point per mode";

km(r)        = (ord(r)-1)*rstep;
Pay_asrec(r) = P_chip_payable_asrec('j1');

Cost_asrec(r,m) =
      ( (C_chip_eurt + C_handle_eurt + C_surcharge(m)) * (1 - MC_asrec) )
    + ( Backhaul * C_tkm(m) * km(r) * (1 - MC_asrec) );

Diff(r,m) = abs(Cost_asrec(r,m) - Pay_asrec(r));
IsBE(r,m) = 0;
IsBE(r,m)$( Diff(r,m) = smin(rr, Diff(rr,m)) ) = 1;

File fdist /distance_payable_curve_j1.csv/ ; put fdist ;
put 'km,mode,cost_asrec_eurpt,payable_asrec_eurpt,is_be' /;
loop(r,
  loop(mplot,
    put km(r):0:0 ',' mplot.tl:0 ',' Cost_asrec(r,mplot):0:2 ','
        Pay_asrec(r):0:2 ',' IsBE(r,mplot):0:0 /;
  );
);
putclose fdist ;

* ===== Curve 2: Payable chip price vs biochar price (and BE radius)
Set bp / bp1*bp11 /;
Scalar dP / 50 /;

Parameter Pchar_grid(bp)    "EUR/t biochar grid"
          Pchip_pay_DM(bp)  "EUR/t DM payable"
          Pchip_pay_asrec(bp) "EUR/t as-received payable"
          R_el_h            "EUR/h from electricity"
          R_ht_h            "EUR/h from heat"
          QinDM_h           "t DM/h"
          BE_rad_grid(bp,m) "km one-way BE radius by mode";

R_el_h   = P_el   * E_net_kW('j1','elec');
R_ht_h   = P_heat * E_net_kW('j1','heat');
QinDM_h  = Qin_DM_h('j1');

Pchar_grid(bp) = P_char + (ord(bp)-ceil(card(bp)/2))*dP;

Pchip_pay_DM(bp) =
  ( (Pchar_grid(bp)*Y_char('j1')*QinDM_h) + R_el_h + R_ht_h - (Clab('j1') + Com('j1') + Cbuy('j1')) )
  / max(1e-9, QinDM_h);

Pchip_pay_asrec(bp) = Pchip_pay_DM(bp) * (1 - MC_asrec);

BE_rad_grid(bp,m) = max(0,
   ( Pchip_pay_DM(bp) - (C_chip_eurt + C_handle_eurt + C_surcharge(m)) )
   / max(1e-9, Backhaul*C_tkm(m))
);

File fpchar /payable_vs_biochar_j1.csv/ ; put fpchar ;
put 'Pchar_eurpt,Pchip_pay_DM_eurptDM,Pchip_pay_asrec_eurpt,BE_radius_tractor_km,BE_radius_truck_km' /;
loop(bp,
  put Pchar_grid(bp):0:2 ',' Pchip_pay_DM(bp):0:2 ',' Pchip_pay_asrec(bp):0:2 ','
      BE_rad_grid(bp,'tractor'):0:2 ',' BE_rad_grid(bp,'truck'):0:2 /;
);
putclose fpchar ;

*==============================================================*
*  DOWNSTREAM & CARBON MARKET EXTENSION (PLANT-FIRST MODEL)    *
*  Adds:                                                       *
*    - Carbon price P_CO2 (€/t CO2-eq)                         *
*    - CO2 balance per year from biochar                       *
*    - Carbon credit revenue per year                          *
*    - Payable chip price incl. carbon (DM & as-received)      *
*    - CSV for Streamlit / plotting                            *
*--------------------------------------------------------------*
*  Assumptions / defaults:                                     *
*  - CO2eq_per_tchar = 2.6 t CO2-eq per t biochar              *
*    ≈ 70% C in biochar * 44/12 (CO2/C). To be replaced later  *
*    by proper LCA results.                                    *
*  - P_CO2 = 80 €/t CO2-eq (within recent EU ETS range).       *
*==============================================================*

Scalar
   P_CO2            "Carbon price (EUR/t CO2-eq) - EDIT LATER OR OVERRIDE IN STREAMLIT" / 80 /
   CO2eq_per_tchar  "Net CO2-eq per t biochar (t CO2-eq / t char; sign can be +/-)"    / 2.6 / ;

*--- Annual CO2 balance and carbon revenue --------------------*
Parameter
   CO2_balance_yr(p)   "Biochar-related CO2-eq balance (t CO2-eq/yr) at plant"
   CO2_rev_yr(p)       "Carbon credit revenue (EUR/yr) from biochar"
   P_chip_payable_DM_wC(p)      "Payable chip price incl. carbon (EUR/t DM)"
   P_chip_payable_asrec_wC(p)   "Payable chip price incl. carbon (EUR/t as-received)" ;

* CharOutput_yr(p) already defined above as: Y_char(p)*Qin_DM_h(p)*Hop_year
CO2_balance_yr(p) = CharOutput_yr(p) * CO2eq_per_tchar;
CO2_rev_yr(p)     = CO2_balance_yr(p) * P_CO2;

* Increment on payable chip price (EUR/t DM) coming from carbon:
*   delta_P_chip_DM = Y_char(p) * CO2eq_per_tchar * P_CO2
P_chip_payable_DM_wC(p) = P_chip_payable(p)
                        + Y_char(p) * CO2eq_per_tchar * P_CO2 ;

* Convert to as-received basis using MC_asrec from above
P_chip_payable_asrec_wC(p) = P_chip_payable_DM_wC(p) * (1 - MC_asrec);

*--- Optional: total annual "extended" gross margin  ----------*
* If you want: GM_ext_yr = GM_base_yr + CO2_rev_yr
* GM_base_yr is implicit in your previous calculations via Rev and PayableBudget_yr.
* Here we only expose the carbon part cleanly.

Parameter
   CarbonPremium_DM(p)     "Carbon premium on chip price (EUR/t DM)"
   CarbonPremium_char(p)   "Carbon premium on biochar price (EUR/t char)" ;

CarbonPremium_DM(p)   = Y_char(p) * CO2eq_per_tchar * P_CO2;
CarbonPremium_char(p) = CO2eq_per_tchar * P_CO2;

*--- CSV: summary of base vs. with-carbon scenario ------------*
* One line per plant p (you currently have only one).
* This CSV is handy for Streamlit to show tables / comparisons.

File fC /plant_first_payable_with_carbon.csv/ ;
put fC ;
put 'plant,'
    'P_CO2_EUR_per_tCO2,'
    'CO2eq_per_tchar_tCO2pt,'
    'P_chip_DM_base_EURptDM,'
    'P_chip_asrec_base_EURpt,'
    'P_chip_DM_withC_EURptDM,'
    'P_chip_asrec_withC_EURpt,'
    'CharOutput_yr_t,'
    'CO2_balance_yr_tCO2,'
    'CO2_rev_yr_EUR'
    / ;

loop(p,
  put p.tl:0 ','                             
      P_CO2:0:2 ','
      CO2eq_per_tchar:0:2 ','
      P_chip_payable(p):0:2 ','
      P_chip_payable_asrec(p):0:2 ','
      P_chip_payable_DM_wC(p):0:2 ','
      P_chip_payable_asrec_wC(p):0:2 ','
      CharOutput_yr(p):0:2 ','
      CO2_balance_yr(p):0:2 ','
      CO2_rev_yr(p):0:0 / ;
);
putclose fC ;

*==============================================================*
* END OF DOWNSTREAM & CARBON EXTENSION                         *
*==============================================================*


