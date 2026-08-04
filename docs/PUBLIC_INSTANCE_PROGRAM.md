# Public Instance and Outcome-Monitoring Program

The repository will not reach production maturity through blank templates alone. This program defines how public instances are created, maintained, and used as longitudinal tests.

## Instance classes

Each flagship domain should have at least two deliberately different instances:

- **Reference case:** clean data, conventional structure, useful for demonstrating normal mechanics.
- **Adversarial case:** stressed, cyclical, nonlinear, incomplete, or structurally unusual.

A third **update case** is encouraged when the domain is event-driven.

## Required directory structure

```text
<domain>/
  instances/
    <instance_slug>/
      model.xlsx
      model_card.md
      validation.md
      thesis.md
      outcome_log.md
      sources/
        source_register.csv
        snapshots/
```

## Source discipline

Every material input must record:

- source name
- document or dataset title
- publication date
- as-of date
- retrieval date
- unit and currency
- transformation
- workbook destination
- license or redistribution restriction
- checksum or archived snapshot location

A live URL without an as-of date is not sufficient evidence.

## Refresh protocol

A material refresh is triggered by:

- earnings or financial statements
- financing or capital-structure change
- rating action
- asset sale or acquisition
- regulatory or tax change
- market move beyond a model-defined threshold
- covenant test
- project milestone
- realized loss or recovery update
- strategy rebalance or backtest window change

Each refresh adds an append-only log entry with:

- trigger
- prior version
- source changes
- assumption changes
- formula or methodology changes
- output changes
- reviewer
- decision impact

## Outcome monitoring

An instance should preserve the prediction or decision output that existed before the outcome was known.

Examples:

- forecast revenue, margin, and cash conversion versus actual
- covenant headroom versus reported performance
- recovery estimate versus restructuring outcome
- option implied move versus realized move
- duration-based P&L estimate versus realized rate move
- project completion and ramp assumptions versus actual
- reserve estimate versus subsequent loss development
- backtest performance versus live or forward performance

The purpose is not to prove perfect forecasts. It is to learn where the model is biased, brittle, or being used outside its intended domain.

## Escalation thresholds

Each instance defines thresholds for:

- data staleness
- forecast error
- unexplained P&L
- covenant or coverage deterioration
- model residuals
- benchmark divergence
- changed methodology
- changed use

Threshold breaches must create a review item and may freeze the model’s maturity status until resolved.

## Public-data constraint

Only public, legally usable data should be committed. Where raw documents cannot be redistributed, commit:

- citation metadata
- checksum
- extraction instructions
- transformed non-copyrightable facts where permitted

Do not commit proprietary templates, paywalled data exports, confidential deal data, or another firm’s internal model.

## Promotion evidence

An instance counts toward M4 only when it has:

- completed model card
- completed validation
- source register
- at least three material RefreshLog entries
- at least one documented outcome comparison
- green current CI
- named owner
- dated release

A copied template with blue cells filled is not a maintained instance.
