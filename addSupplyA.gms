if(UseSupplyEq = 1,
   Upstream_A.Include( 'SupplyBal' );
else
   Upstream_A.Include( 'SupplyLim' );
);
