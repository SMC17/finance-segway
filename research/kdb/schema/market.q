/ Minimal example schema for the kdb research rail.
/ These tables are illustrative. Real schemas will evolve with data needs.

/ Daily equity bars (adjusted)
daily:([] date:`date$(); sym:`symbol$(); open:`float$(); high:`float$(); low:`float$(); close:`float$(); volume:`long$(); adjclose:`float$())

/ Simple factor / residual returns
factorret:([] date:`date$(); sym:`symbol$(); factor:`symbol$(); ret:`float$())

/ Regime summary export shape (Contract 1)
regime_summary:([] as_of_date:`date$(); universe:`symbol$(); metric:`symbol$(); value:`float$(); methodology:`symbol$())
