/ Empty table contracts for source-addressed public observations.

daily:([] date:`date$(); sym:`symbol$(); open:`float$(); high:`float$(); low:`float$(); close:`float$(); volume:`long$(); adjclose:`float$(); source_id:`symbol$())

factorret:([] date:`date$(); sym:`symbol$(); factor:`symbol$(); ret:`float$(); source_id:`symbol$())

regime_summary:([] as_of_date:`date$(); universe:`symbol$(); metric:`symbol$(); value:`float$(); methodology:`symbol$(); source_url:`symbol$(); source_as_of:`date$(); source_checksum:`symbol$(); license_note:`symbol$())
