* ===== Minimal, ASCII-only, standalone model =====

$onExternalInput
Scalar P_BIOCHAR   /500/     ;
Scalar d_active    /50/      ;
Scalar Q_char      /100/     ;
Scalar Q_ship      /100/     ;
Scalar c_tkm       /0.12/    ;
Scalar surcharge   /5/       ;
Scalar v_up        /50/      ;
Scalar fixed_plant /10000/   ;
Scalar v_plant     /30/      ;
Scalar Rev_elec    /0/       ;
Scalar labor_on    /1/       ;
Scalar v_labor     /8/       ; 
$offExternalInput
* Variables and equation
Variables z ;
Equations obj ;

* Components as scalars (recomputed before each solve)
Scalar labor_cost, C_transport, C_upstream, C_plant, Revenue ;

* Objective definition
obj.. z =e= Revenue - (C_transport + C_upstream + C_plant) ;

Model BiocharProfit / obj / ;

* First solve with defaults
labor_cost = labor_on * v_labor * Q_char ;
C_transport = c_tkm * d_active * Q_ship + surcharge * Q_ship ;
C_upstream  = v_up * Q_char + labor_cost ;
C_plant     = fixed_plant + v_plant * Q_char ;
Revenue     = P_BIOCHAR * Q_char + Rev_elec ;
Solve BiocharProfit using LP maximizing z ;

* --------- Sensitivity surface: price x distance (solverless) ----------
Set p / p200, p250, p300, p350, p400, p450, p500, p550, p600, p650, p700, p750, p800 /
    d / d0, d10, d20, d30, d40, d50, d60, d70, d80, d90, d100, d110, d120, d130, d140
         , d150, d160, d170, d180, d190, d200 /;

Parameter Pgrid(p), Dgrid(d);
Pgrid("p200") = 200 ; Pgrid("p250") = 250 ; Pgrid("p300") = 300 ;
Pgrid("p350") = 350 ; Pgrid("p400") = 400 ; Pgrid("p450") = 450 ;
Pgrid("p500") = 500 ; Pgrid("p550") = 550 ; Pgrid("p600") = 600 ;
Pgrid("p650") = 650 ; Pgrid("p700") = 700 ; Pgrid("p750") = 750 ; Pgrid("p800") = 800 ;

Dgrid("d0") = 0 ; Dgrid("d10") = 10 ; Dgrid("d20") = 20 ; Dgrid("d30") = 30 ; Dgrid("d40") = 40 ;
Dgrid("d50") = 50 ; Dgrid("d60") = 60 ; Dgrid("d70") = 70 ; Dgrid("d80") = 80 ; Dgrid("d90") = 90 ;
Dgrid("d100") = 100 ; Dgrid("d110") = 110 ; Dgrid("d120") = 120 ; Dgrid("d130") = 130 ; Dgrid("d140") = 140 ;
Dgrid("d150") = 150 ; Dgrid("d160") = 160 ; Dgrid("d170") = 170 ; Dgrid("d180") = 180 ; Dgrid("d190") = 190 ; Dgrid("d200") = 200 ;

* Profit map (price x distance)
Parameter PROFITMAP(p,d);
Scalar labor_cost, C_transport, C_upstream, C_plant, Revenue, Profit;

Loop(p,
  P_BIOCHAR = Pgrid(p);
  Loop(d,
    d_active   = Dgrid(d);

    labor_cost = labor_on * v_labor * Q_char ;
    C_transport = c_tkm * d_active * Q_ship + surcharge * Q_ship ;
    C_upstream  = v_up * Q_char + labor_cost ;
    C_plant     = fixed_plant + v_plant * Q_char ;
    Revenue     = P_BIOCHAR * Q_char + Rev_elec ;

    Profit = Revenue - (C_transport + C_upstream + C_plant);
    PROFITMAP(p,d) = Profit ;
  );
);

* Write surface CSV
File fSurf /profit_surface.csv/ ; put fSurf ;
put 'price_eur_per_t,dist_km,profit_eur' / ;
Loop(p, Loop(d,
  put Pgrid(p):0:0 ',' Dgrid(d):0:0 ',' PROFITMAP(p,d):0:2 / ;
)); putclose fSurf ;



* --------- 1D curves (no ord, reuse p and d) ----------
Set metric / x, y / ;
Parameter CurveDist(d,metric), CurvePrice(p,metric) ;

* Profit vs distance at current P_BIOCHAR
Loop(d,
  d_active   = Dgrid(d) ;
  labor_cost = labor_on * v_labor * Q_char ;
  C_transport = c_tkm * d_active * Q_ship + surcharge * Q_ship ;
  C_upstream  = v_up * Q_char + labor_cost ;
  C_plant     = fixed_plant + v_plant * Q_char ;
  Revenue     = P_BIOCHAR * Q_char + Rev_elec ;
  Profit = Revenue - (C_transport + C_upstream + C_plant) ;
  CurveDist(d,"x") = Dgrid(d) ;
  CurveDist(d,"y") = Profit ;
) ;

File fCD /curve_distance.csv/ ; put fCD ;
put 'dist_km,profit_eur' / ;
Loop(d, put CurveDist(d,"x"):0:0 ',' CurveDist(d,"y"):0:2 / ; ) ;
putclose fCD ;

* Profit vs price at fixed distance = 50 km
d_active = Dgrid("d50") ;
Loop(p,
  P_BIOCHAR = Pgrid(p) ;
  labor_cost = labor_on * v_labor * Q_char ;
  C_transport = c_tkm * d_active * Q_ship + surcharge * Q_ship ;
  C_upstream  = v_up * Q_char + labor_cost ;
  C_plant     = fixed_plant + v_plant * Q_char ;
  Revenue     = P_BIOCHAR * Q_char + Rev_elec ;
  Profit = Revenue - (C_transport + C_upstream + C_plant) ;
  CurvePrice(p,"x") = Pgrid(p) ;
  CurvePrice(p,"y") = Profit ;
) ;

File fCP /curve_price.csv/ ; put fCP ;
put 'price_eur_per_t,profit_eur' / ;
Loop(p, put CurvePrice(p,"x"):0:0 ',' CurvePrice(p,"y"):0:2 / ; ) ;
putclose fCP ;

$onExternalOutput
Parameter PROFITMAP(p,d), CurveDist(d,metric), CurvePrice(p,metric);
$offExternalOutput

execute_unload 'results.gdx', PROFITMAP, CurveDist, CurvePrice ;
