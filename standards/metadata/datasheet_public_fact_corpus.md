# Datasheet: recorded public-fact corpus

Following *Datasheets for Datasets* (Gebru et al.). The dataset is everything
under `tools/data_fabric/out/`: the structured public facts every model in this
repository is allowed to draw on.

Machine-readable companion: `standards/metadata/catalog.jsonld`, dataset id
`data-fabric`.

| | |
|---|---|
| Version | 1.0 |
| As of | 2026-09-07 |
| Licence | MIT (this repository). Underlying facts are public records; see Distribution. |
| Maintainer | SMC17 / finance-segway |

## Motivation

**Why was the dataset created?**
Because a financial model is only as good as the provenance of its inputs, and
provenance decays the moment a number is typed by hand. Every model here is
required to source its values from public disclosure. That requirement is
enforceable only if the disclosures are themselves recorded, dated, and hashed
somewhere a checker can read. This corpus is that somewhere.

**What problem does it solve?**
It removes the modeller's memory from the loop. Before it existed, a value like
"Microsoft FY2024 long-term debt" reached a workbook through a person who had
read a filing. Now it reaches the workbook through a file that names the filing,
records when it was fetched, and carries a digest, so a reviewer can check the
chain without trusting anyone's recollection.

**Who funded it?** Unfunded. Built inside this repository.

## Composition

**What do the instances represent?**
Three kinds of public fact, kept separate because they have different
publishers, different update rhythms, and different reliability:

| Source | Files | What each holds |
|---|---:|---|
| SEC EDGAR XBRL company facts | 103 annual series | Tagged financial-statement concepts per issuer, by fiscal period |
| Damodaran Online industry data | 14 | Industry betas, margins, multiples, country risk premiums |
| U.S. Treasury | 4 | Daily par yield curve and bill rates |
| Alpha Vantage, SEC SIC, ETF profiles | remainder | Fund holdings, sector classifications, quotes, transcripts |

581 JSON files, about 16 MB, plus 117 source-register CSVs.

**How many instances?**
41,322 XBRL observations across 43 distinct `us-gaap` concepts and 103 issuers.

**Is any of it a sample?**
Yes, and the sampling is not random. Issuer coverage was chosen to match the
index universes the repository models — chiefly NASDAQ-100 constituents — so it
is biased toward large, US-listed, technology-weighted companies. Nothing here
supports a claim about small caps, non-US issuers, or private companies.

**What data does each instance consist of?**
For XBRL: concept name, resolved tag, unit, and a list of observations each with
period-end date, value, filing date, form type, fiscal year, and fiscal period.
For Treasury and Damodaran: the publisher's own column headers, preserved
verbatim rather than renamed.

**Is there a label or target?** No. This is source data, not a training set.

**Is any information missing?**
Yes, and the gaps drive real modelling decisions:
- No issuer tags annual recurring revenue, net revenue retention, or churn.
  Those metrics have no XBRL element. This is why the software model builds its
  forward-revenue engine on remaining performance obligations instead.
- Depreciation and amortisation is absent for some issuers, including Microsoft,
  so EBITDA cannot always be derived and EBIT is used with the substitution
  stated.
- Market prices, market capitalisation, and enterprise value are absent, so
  comparable-company multiples cannot be computed from this corpus at all.

**Are there errors, noise, or redundancies?**
Yes, three known classes, all inherited from upstream and none silently
corrected:
1. **String sentinels in numeric columns.** 612 occurrences of `NA`, `n/a`, and
   `N/A`, chiefly in the Damodaran country-premium table. A string where a
   number belongs breaks type validation.
2. **Spreadsheet artefacts.** The Damodaran country table carries a column
   literally named `Has to be sorted in ascending order`, and a column named
   `Africa` whose values are region names such as `Eastern Europe & Russia`.
   These are authoring notes and mislabelled headers from the source workbook.
3. **Duplicate snapshots.** Each fetch writes both a stable filename and a
   timestamped one, so most datasets appear twice by design.

`tools/verify_data_conventions.py` reports classes 1 and 3. Class 2 is recorded
here and left in place: renaming a publisher's column would make the file no
longer a faithful record of what they published.

**Is it self-contained?** Yes. Every file needed is committed. No network access
is required to use it, which matters because network egress is restricted in
some environments this repository runs in.

**Does it contain confidential, offensive, or personal data?**
No. Everything is drawn from published filings, published rate tables, and
published academic data. It contains no personal data beyond the names of
companies and their SEC identifiers.

## Collection process

**How was the data acquired?**
Directly observable from the publisher, by HTTP fetch, recorded verbatim:
- SEC EDGAR company-facts API, via `tools/data_fabric/edgar_company_facts.py`
- home.treasury.gov CSV export, via `tools/data_fabric/treasury_public_facts.py`
- Damodaran Online workbooks, via `tools/data_fabric/damodaran_public_facts.py`
- Alpha Vantage MCP endpoints, recorded through
  `tools/data_fabric/alpha_vantage_facts.py`, which is a recorder rather than a
  fetcher because those endpoints are reachable only as tool calls

**Over what timeframe?**
Fetches run from 2026-08-06 onward; each file records its own `retrieved_utc`.
The facts themselves span roughly two decades of filings, per issuer.

**Was anyone paid, and was there ethical review?**
No, and no review board was involved; the data is public record.

## Preprocessing, cleaning, labelling

**What was done?**
Deliberately little. Values are converted to a consistent JSON shape and
deduplicated to one observation per fiscal period-end, with the longest-duration
and latest-filed value winning so that restatements supersede originals. Column
headers are preserved as the publisher wrote them.

**Was the raw data saved?**
Yes. Every fetch writes a timestamped copy alongside the stable filename, so the
original is recoverable.

**Is the software available?** Yes, in `tools/data_fabric/`.

**One deliberate non-normalisation.** Alpha Vantage's cash-flow figures for
business-development companies disagree with SEC EDGAR's for the same issuer and
period — for Ares Capital FY2025, +$1,142M against −$54M — because vendors
classify portfolio purchases differently. Those facts are recorded under the
vendor's own field name rather than mapped onto the EDGAR concept, so the
disagreement stays visible instead of being averaged away.

## Uses

**What has it been used for?**
Sourcing inputs to the 27 domain models, grounding driver ranges, and providing
the frozen baselines for registered out-of-sample forecasts.

**What should it not be used for?**
- Anything requiring market prices. They are not here.
- Any claim about issuers outside the sampled universe.
- Training a model that will be deployed. The corpus is small, biased toward
  large-cap US technology, and assembled for auditability rather than coverage.
- Investment decisions. Nothing in this repository is validated for that.

**Is there anything about its composition that could cause harm?**
The universe bias is the main risk. A ratio that looks like an industry norm
here may simply be a NASDAQ-100 norm. Any driver grounded in this corpus should
name the universe it came from, and the case manifests do.

## Distribution

**How is it distributed?** In this Git repository, under the MIT licence.

**Do third-party terms apply?**
The underlying facts are public records and are not owned by this project. SEC
filings are public domain. Treasury rate tables are public domain. Damodaran
Online data is published for public use by its author, who should be cited.
Alpha Vantage content is redistributed here only as recorded observations used
to build models, not as a data product.

## Maintenance

**Who maintains it and how is it refreshed?**
The repository owner. Issuer facts change once per filing, so the intended
cadence is quarterly; `tools/quarterly_refresh.py` reports what is due.

**Will older versions be kept?**
Yes. Timestamped snapshots are never deleted, and every case that depends on a
snapshot records its SHA-256, so a changed snapshot breaks the case's integrity
check rather than silently altering its results.

**How can others contribute?**
By adding a connector under `tools/data_fabric/` that records provenance in the
same shape: a stable file, a timestamped file, and a source-register row naming
publisher, URL, retrieval time, and digest. `AGENTS.md` states the rules.
