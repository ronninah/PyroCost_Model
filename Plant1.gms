Set p / j1 /
    e / elec, heat / ;

Set i / i1*i3 /, jn / j1*j2 /;

Parameter
   Qin_DM_h(p)       "t DM/h"
   Y_char(p)         "t char per t DM"
   E_net_kW(p,e)     "kW"
   Hop_year          "h/year"
   P_char            "EUR/t"
   P_el              "EUR/kWh"
   P_heat            "EUR/kWh_th"
   P_chipDM_deliv(p) "EUR/t DM"
   n_ops(p)          "operators per shift"
   w_hour            "EUR/h"
   OM_hour(p)        "EUR/h"
   P_buy             "EUR/kWh"
   E_buy_kWh(p)      "kWh/h" ;

Qin_DM_h('j1')        = 0.299 ;
Y_char('j1')          = 0.25  ;
E_net_kW('j1','elec') = 130   ;
E_net_kW('j1','heat') = 200   ;
Hop_year              = 8000  ;

P_char                = 600   ;
P_el                  = 0.11  ;
P_heat                = 0.06  ;
P_chipDM_deliv('j1')  = 25    ;

n_ops('j1')           = 1     ;
w_hour                = 28    ;
OM_hour('j1')         = 30    ;
P_buy                 = 0.28  ;
E_buy_kWh('j1')       = 0     ;

Scalar MC_asrec "Moisture content of as-received chips" / 0.35 / ;

Parameter
    FlowIJ(i,jn) "t/yr as-received shipped (from upstream)"
    Pprice(jn)   "€/t chip price at plant (from upstream)" ;

$if exist "miro_out.gdx" $onMultiR
$if exist "miro_out.gdx" $gdxin miro_out.gdx
$if exist "miro_out.gdx" $load FlowIJ Pprice
$if exist "miro_out.gdx" $gdxin
$if exist "miro_out.gdx" $offMulti

Scalar Supply_asrec_j1 "t/yr as-received to j1"
       Sup_DM_yr       "t DM/yr from upstream to j1"
       Sup_DM_h        "t DM/h equivalent from upstream" ;

Supply_asrec_j1 = sum(i, FlowIJ(i,'j1')) ;
Sup_DM_yr       = Supply_asrec_j1 * (1 - MC_asrec) ;
Sup_DM_h        = Sup_DM_yr / Hop_year ;

Scalar Cap_DM_h      "t DM/h brochure capacity"
       Cap_DM_yr     "t DM/year brochure capacity"
       Cap_asrec_yr  "t/yr as-received brochure capacity"
       Diff_DM_h     "t DM/h: capacity minus upstream"
       Diff_asrec_yr "t/yr as-received: capacity minus upstream"
       Util_DM       "DM-based utilization (0..1)" ;

Cap_DM_h      = Qin_DM_h('j1') ;
Cap_DM_yr     = Cap_DM_h * Hop_year ;
Cap_asrec_yr  = Cap_DM_yr / (1 - MC_asrec) ;
Diff_DM_h     = Cap_DM_h - Sup_DM_h ;
Diff_asrec_yr = Cap_asrec_yr - Supply_asrec_j1 ;
Util_DM       = 0 ;
Util_DM$(Cap_DM_h>0) = min(1, Sup_DM_h/Cap_DM_h) ;

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

Cfs(p)        = Qin_DM_h(p) * P_chipDM_deliv(p) ;
Clab(p)       = n_ops(p) * w_hour ;
Com(p)        = OM_hour(p) ;
Cbuy(p)       = P_buy * E_buy_kWh(p) ;

GM(p)         = Rev(p) - (Cfs(p) + Clab(p) + Com(p) + Cbuy(p)) ;
GM_per_tDM(p) = GM(p) / Qin_DM_h(p) ;
GM_per_year(p)= GM(p) * Hop_year ;

Display Rev, Cfs, Clab, Com, Cbuy, GM, GM_per_tDM, GM_per_year ;

Scalar Pchar_BE "EUR/t"
       Pchip_BE "EUR/t DM" ;

Pchar_BE = ( Cfs('j1') + Clab('j1') + Com('j1') + Cbuy('j1')
             - ( Rel('j1') + Rheat('j1') ) )
           / ( Y_char('j1') * Qin_DM_h('j1') ) ;

Pchip_BE = ( Rchar('j1') + Rel('j1') + Rheat('j1')
             - ( Clab('j1') + Com('j1') + Cbuy('j1') ) )
           / Qin_DM_h('j1') ;

Display Pchar_BE, Pchip_BE ;

File f1 /plant_modeA_kpi_j1.csv/ ; put f1 ;
put 'plant,P_char,E_net_kW,H_use_kW,P_chipDM_deliv,Rev,Cfs,Clab,Com,Cbuy,GM,GM_per_tDM,GM_per_year'/;
put 'j1',',', P_char:0:2, ',', E_net_kW('j1','elec'):0:0, ',', E_net_kW('j1','heat'):0:0, ',',
    P_chipDM_deliv('j1'):0:2, ',', Rev('j1'):0:2, ',', Cfs('j1'):0:2, ',', Clab('j1'):0:2, ',',
    Com('j1'):0:2, ',', Cbuy('j1'):0:2, ',', GM('j1'):0:2, ',', GM_per_tDM('j1'):0:2, ',',
    GM_per_year('j1'):0:0 / ;
putclose f1 ;

File f2 /plant_modeA_breakeven_j1.csv/ ; put f2 ;
put 'Pchar_BE_EURt,Pchip_BE_EURtDM'/;
put Pchar_BE:0:2 ',' Pchip_BE:0:2 /;
putclose f2 ;

File f3 /supply_vs_capacity_j1.csv/ ; put f3 ;
put 'Cap_DM_h,Cap_DM_yr,Cap_asrec_yr,Sup_asrec_yr,Sup_DM_yr,Sup_DM_h,Diff_DM_h,Diff_asrec_yr,Util_DM'/;
put Cap_DM_h:0:6 ',' Cap_DM_yr:0:2 ',' Cap_asrec_yr:0:2 ',' Supply_asrec_j1:0:2 ','
    Sup_DM_yr:0:2 ',' Sup_DM_h:0:6 ',' Diff_DM_h:0:6 ',' Diff_asrec_yr:0:2 ',' Util_DM:0:4 /;
putclose f3 ;
