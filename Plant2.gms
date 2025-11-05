* Mode C (hybrid): roadside chip price + plant computes haul to gate (single plant)

Set p / PlantA /
    e / elec, heat / ;

* --- Technical and price inputs (edit as needed) ---
Parameter
   Qin_DM_h(p)            "t DM/h"
   Y_char(p)              "t char per t DM"
   E_net_kW(p,e)          "kW net export"
   Hop_year               "h/year"
   P_char                 "EUR/t"
   P_el                   "EUR/kWh"
   P_heat                 "EUR/kWh_th"
   n_ops(p)               "operators/shift"
   w_hour                 "EUR/h"
   OM_hour(p)             "EUR/h"
   P_buy                  "EUR/kWh"
   E_buy_kWh(p)           "kWh/h" ;

Qin_DM_h('PlantA')        = 0.299 ;
Y_char('PlantA')          = 0.25  ;
E_net_kW('PlantA','elec') = 130   ;
E_net_kW('PlantA','heat') = 200   ;
Hop_year                  = 8000  ;

P_char                    = 500   ;
P_el                      = 0.11  ;
P_heat                    = 0.06  ;

n_ops('PlantA')           = 1     ;
w_hour                    = 28    ;
OM_hour('PlantA')         = 30    ;
P_buy                     = 0.28  ;
E_buy_kWh('PlantA')       = 0     ;

* --- Mode C haul inputs and roadside price (key differences vs Mode A) ---
Scalar
   P_chipDM_roadside      "EUR/t DM at roadside (no long-haul)"
   d_feed_km              "one-way km roadside -> plant"
   r_truck_eur_per_km     "EUR per truck-km"
   payload_chip_tFM       "truck payload, t fresh chips"
   MC_chip                "chip moisture (fraction, e.g. 0.30)" ;

P_chipDM_roadside  = 65     ;
d_feed_km          = 40     ;
r_truck_eur_per_km = 2.0    ;
payload_chip_tFM   = 24     ;
MC_chip            = 0.30   ;

* --- Derived haul cost and delivered price (EUR/t DM) ---
Scalar
   c_haul_per_tFM   "EUR/t FM"
   c_haul_per_tDM   "EUR/t DM"
   P_chipDM_deliv   "EUR/t DM delivered to gate" ;

c_haul_per_tFM = (2*d_feed_km*r_truck_eur_per_km) / payload_chip_tFM ;
c_haul_per_tDM = c_haul_per_tFM / (1 - MC_chip) ;
P_chipDM_deliv = P_chipDM_roadside + c_haul_per_tDM ;

* --- Outputs (computed) ---
Parameter
   Qchar_h(p)      "t/h"
   Rchar(p)        "EUR/h"
   Rel(p)          "EUR/h"
   Rheat(p)        "EUR/h"
   Rev(p)          "EUR/h"
   Cfs(p)          "EUR/h"
   Clab(p)         "EUR/h"
   Com(p)          "EUR/h"
   Cbuy(p)         "EUR/h"
   GM(p)           "EUR/h"
   GM_per_tDM(p)   "EUR/t DM"
   GM_per_year(p)  "EUR/year" ;

Qchar_h(p)    = Y_char(p) * Qin_DM_h(p) ;
Rchar(p)      = P_char * Qchar_h(p) ;
Rel(p)        = P_el   * E_net_kW(p,'elec') ;
Rheat(p)      = P_heat * E_net_kW(p,'heat') ;
Rev(p)        = Rchar(p) + Rel(p) + Rheat(p) ;

Cfs(p)        = Qin_DM_h(p) * P_chipDM_deliv ;
Clab(p)       = n_ops(p) * w_hour ;
Com(p)        = OM_hour(p) ;
Cbuy(p)       = P_buy * E_buy_kWh(p) ;

GM(p)         = Rev(p) - (Cfs(p) + Clab(p) + Com(p) + Cbuy(p)) ;
GM_per_tDM(p) = GM(p) / Qin_DM_h(p) ;
GM_per_year(p)= GM(p) * Hop_year ;

Display
  P_chipDM_roadside, d_feed_km, r_truck_eur_per_km, payload_chip_tFM, MC_chip,
  c_haul_per_tFM, c_haul_per_tDM, P_chipDM_deliv ;

Display Rev, Cfs, Clab, Com, Cbuy, GM, GM_per_tDM, GM_per_year ;

* --- Break-even metrics ---
Scalar Pchar_BE "EUR/t", Pchip_roadside_BE "EUR/t DM roadside" ;

Pchar_BE = ( Cfs('PlantA') + Clab('PlantA') + Com('PlantA') + Cbuy('PlantA')
             - ( Rel('PlantA') + Rheat('PlantA') ) )
           / ( Y_char('PlantA') * Qin_DM_h('PlantA') ) ;

* roadside break-even = delivered BE minus haul component
Pchip_roadside_BE = ( Rchar('PlantA') + Rel('PlantA') + Rheat('PlantA')
                      - ( Clab('PlantA') + Com('PlantA') + Cbuy('PlantA') ) )
                    / Qin_DM_h('PlantA')  - c_haul_per_tDM ;

Display Pchar_BE, Pchip_roadside_BE ;

* --- CSV export (optional) ---
File f /plant_modeC_kpi.csv/ ; put f ;
put 'plant,mode,P_char,P_chipDM_roadside,P_chipDM_deliv,d_km,Rev,Cfs,Clab,Com,Cbuy,GM,GM_per_tDM,GM_per_year,Pchar_BE,Pchip_roadside_BE' / ;
put 'PlantA',',','ModeC',',', P_char:0:2, ',', P_chipDM_roadside:0:2, ',', P_chipDM_deliv:0:2, ',', d_feed_km:0:0, ',',
    Rev('PlantA'):0:2, ',', Cfs('PlantA'):0:2, ',', Clab('PlantA'):0:2, ',', Com('PlantA'):0:2, ',', Cbuy('PlantA'):0:2, ',',
    GM('PlantA'):0:2, ',', GM_per_tDM('PlantA'):0:2, ',', GM_per_year('PlantA'):0:0, ',', Pchar_BE:0:2, ',', Pchip_roadside_BE:0:2 / ;
putclose f ;
