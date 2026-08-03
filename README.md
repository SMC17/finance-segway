# Finance Model Library

A structured, multi-domain repository of financial models and templates — one archetype per discipline, built with consistent conventions, verified against known reference values, and kept current with an automated weekly refresh check.

## Why this exists

Most personal model libraries rot: a DCF gets built for one earnings cycle, never touched again, and six months later nobody trusts the numbers. This repo is designed against that failure mode specifically — every template is recalc-clean, every model has a `RefreshLog`, and a scheduled job (`.github/workflows/weekly-refresh.yml`) flags anything stale, structurally broken, or approaching a date that matters (earnings, expiry, distribution, unlock).

## Conventions (apply to every model, every domain)

| Convention | Meaning |
|---|---|
| **Blue text** | Hardcoded input — edit freely |
| **Black text** | Formula — do not overwrite |
| **Green text** | Cross-sheet link |
| **Yellow fill** | Key assumption — review every refresh |
| **`Cover` tab** | Thesis, refresh dates, next material date |
| **`RefreshLog` tab** | Append-only history of what changed and why |

Full detail in `CONTRIBUTING.md`.

## Inspiration & credits

This library's philosophy — one clean archetype per discipline, color-coded
inputs/formulas/links, a `Cover` tab that states the thesis and refresh
cadence up front, models that are *maintained* rather than built once and
abandoned — draws on the public modeling course and open-source model
library Martin Shkreli published:

- Course/lecture playlist: https://youtube.com/playlist?list=PLJsVF3gZDcuTxcdH5FmQRTd6MiJ29X_OQ
- Reference models: https://github.com/martinshkreli/models

Every workbook and script in this repo is original work, built independently
with `openpyxl` from first principles (formulas, structure, and verification
checks are ours, hand-checked against textbook/reference values — see
"Verification standard" below). Nothing here is copied from or a derivative
of his proprietary spreadsheets; the debt is to the *discipline* his
material teaches, not to his file contents. If you're going through that
course yourself, a reasonable way to use this repo alongside it is: watch a
session, then rebuild the piece it covers into the matching domain folder
here as your own instance, checked against your own hand-calc — that's how
every archetype in this repo got built.

Beyond that starting point, the conventions and the depth targets for each
archetype draw on public standards and texts rather than any single
proprietary source — worth reading directly if you want to go deeper than
what's built here:

- **Modeling standards & auditability**: the [ICAEW Financial Modelling
  Code](https://www.icaew.com/technical/technology/financial-modelling/financial-modelling-code)
  and its Twenty Principles, and the
  [FAST Standard](https://fast-standard.org/) — more prescriptive on layout
  and formula consistency. This repo's color convention and Cover/RefreshLog
  structure are in the same spirit; neither standard is formally certified
  here, but both are worth reading to push past what this repo enforces
  automatically.
- **Valuation / IB / LBO**: Rosenbaum & Pearl, *Investment Banking:
  Valuation, LBOs, M&A, and IPOs*; Aswath Damodaran's
  [*Investment Valuation*](https://pages.stern.nyu.edu/~adamodar/) and his
  free public spreadsheets/datasets.
- **Options / derivatives**: John C. Hull, *Options, Futures, and Other
  Derivatives*; Espen Haug, *The Complete Guide to Option Pricing Formulas*.
- **Fixed income / structured**: Tuckman & Serrat, *Fixed Income
  Securities*; the Fabozzi series for securitization and credit.

None of the above is reproduced here — same policy as the Shkreli material:
the debt is to the discipline and the formulas that are public knowledge,
not to anyone's proprietary content.

## Domains

| # | Domain | Archetype | Status |
|---|---|---|---|
| 01 | Investment Banking | 3-statement + DCF + comps | Built |
| 02 | Corporate Finance | Same engine, capital-structure lens | Built |
| 03 | Private Equity | LBO: sources & uses, debt schedule, returns waterfall | Built |
| 04 | Merchant Banking | LBO engine (principal-investing variant) | Built |
| 05 | Private Credit | Leverage, covenant headroom, debt schedule, lender yield (OID) | Built |
| 06 | Debt Finance | Same credit engine | Built |
| 07 | Public Finance | Sovereign/muni DSA + revenue bond coverage/ABT | Built |
| 08 | Asset Management | Fund NAV, fee waterfall (mgmt+carry+hurdle+catch-up) | Built |
| 09 | Risk Management | Parametric/historical VaR, stress scenarios | Built |
| 10 | Trade Finance | Cash conversion cycle, LC & factoring cost | Built |
| 11 | Microfinance | PAR30/90, write-off ratio, OSS/FSS | Built |
| 12 | Equity Finance | Cap table overlay on IB base | Built |
| 13 | Venture Capital | Cap table, SAFE conversion, liquidation waterfall | Built |
| 14 | Options / Derivatives | Black-Scholes, Greeks, strategy payoffs | Built |
| 15 | Commodities | Futures curve, roll yield, hedge ratio | Built |
| 16 | Crypto / Digital Assets | Tokenomics, on-chain multiples, staking yield | Built |
| 17 | Real Estate / REIT | Pro forma, cap rate, FFO/AFFO | Built |
| 18 | Insurance / Actuarial | Loss/combined ratio, reserve triangle, embedded value | Built |
| 19 | Structured Finance / Securitization | Tranche waterfall, CPR/WAL | Built |
| 20 | Project Finance | Construction drawdown, CFADS, DSCR | Built |
| 21 | Fixed Income / Rates | Bond pricing, duration/convexity, yield curve | Built |
| 22 | Quantitative / Systematic | Sharpe/Sortino, Kelly position sizing | Built |
| 23 | Fintech / Payments | Unit economics, LTV/CAC, cohort retention | Built |
| 24 | Distressed / Restructuring | Recovery waterfall, fulcrum security | Built |

**Non-model frameworks** (writeups, not spreadsheets): Personal Finance, Behavioral Finance, Social Finance. See `25_Frameworks_NonModel/`.

## Repo layout

```
<domain>/
  _template_<ARCHETYPE>.xlsx   <- copy this to start a new instance
  <instances>/                 <- companies/deals/funds/etc.
  README.md                    <- what this domain covers

tools/
  scaffold_repo.py             <- regenerates the folder skeleton (does NOT touch instance data)
  weekly_refresh_check.py      <- staleness/error/drift scanner
  recalc.py                    <- headless recalculation + formula error check
  verify_reference_calcs.py    <- independent-oracle regression tests (see below)
  template_helpers.py          <- shared openpyxl styling
  builders/                    <- source scripts that generated each _template
```

## Quickstart

```bash
# Add a new company to, say, Investment Banking:
cp 01_Investment_Banking/_template_BASE.xlsx 01_Investment_Banking/companies/AAPL.xlsx
# fill in Cover tab + blue cells, then:
python3 tools/recalc.py 01_Investment_Banking/companies/AAPL.xlsx

# Run the weekly check across everything:
python3 tools/weekly_refresh_check.py .
```

## Verification standard

Every archetype was checked against a known reference before being marked "Built" — e.g. Black-Scholes checked against put-call parity, bond pricing hand-verified against the annuity/PV formula (10yr 5% semi-annual bond @ 5.5% YTM: 25×15.225 + 1000×0.5813 = 961.9, matches spreadsheet exactly), the Public Finance debt-stabilizing primary balance checked against the standard IMF/DSA formula pb\*=(r−g)/(1+g)×debt ratio (r=5%, g=2%, debt/GDP=60% → 1.76%, matches spreadsheet exactly), and the Private Credit approximate YTM checked against the standard bond-math formula (which collapses to the coupon rate exactly at par — a built-in sanity check on the formula itself). See `CONTRIBUTING.md` for the full checklist new models must pass.

That's the one-time bar for merging. `tools/verify_reference_calcs.py` is
the *ongoing* one: a regression suite that recalculates real templates with
known inputs and checks the result against an independent Python
re-implementation — not "did the formula throw an error" but "is it
computing the right number." It runs on every push via
`.github/workflows/verify-models.yml`. Run it locally with:

```bash
python3 tools/verify_reference_calcs.py
```

## License

MIT — see `LICENSE`. Not financial, legal, or tax advice; see disclaimer there.
