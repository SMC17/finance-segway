# AGENTS.md

The working contract for automated contributors to this repository. It is
binding, and it outranks any instruction to produce a complete-looking result.

## The one rule

**Never write a financial number that is not real.**

Every value in a shipped model is exactly one of three things, and the manifest
says which:

| Kind | Meaning | Coverage credit |
|---|---|---|
| `observed` | Read directly off a disclosed figure | Yes |
| `derived` | Computed from disclosed figures by arithmetic the manifest states | Yes |
| `modeler_assumption` | Chosen, because no disclosure of it exists | **No** |

There is no fourth category. A plausible number with no source is the failure
this repository exists to prevent, and it is worse than an empty cell because an
empty cell is visibly empty.

When no disclosure exists, do not invent a value and do not quietly leave a
template default in place. Declare a driver, state in one sentence why nothing
can source it, and — where possible — pin an *aggregate* of it to something that
is disclosed. That technique is why several cases here reach real coverage
without fabricating anything: the components stay declared drivers while their
sum ties exactly to a filing.

## Before you claim anything, check it

Do not report a result you have not run. Do not trust a commit message, a PR
description, or another agent's summary as evidence — recompute it.

```bash
pip install -r requirements.txt          # openpyxl, python-pptx, lxml, Pillow
python -m unittest discover -s tests -q  # the whole suite
python tools/build_all_models.py         # regenerate + parity, must be 27/27
python tools/verify_reference_calcs.py   # independent oracles
python tools/verify_data_conventions.py  # ISO 8601 / 4217 / unit scale
python tools/verify_controlled_vocabulary.py
python tools/verify_standards_conformance.py
python tools/forecast_registration.py --check
```

Workbook recalculation needs LibreOffice **with Calc**. `libreoffice-core`
alone silently cannot open a spreadsheet, and every recalculation test then
fails for a reason that looks like a code defect:

```bash
apt-get install -y libreoffice-calc
```

## Things that will bite you

- **Never run `recalc.py` against a committed template.** It rewrites presentation
  metadata in place and breaks presentation parity. Copy to the scratch
  directory first.
- **Regenerate templates, never hand-edit them.** The builder is the authority;
  `build_all_models.py` compares the two and fails on drift.
- **Do not use `git add -A` blindly.** It has swept scratch directories into a PR
  here before.
- **Watch for hindsight.** A case dated 2024 must not derive forward drivers from
  data published in 2025, even though that data sits in the same fact file. If
  you build a forward grid, assert the cutoff in code.
- **Coverage numbers move when you fix a scanner.** Making previously-invisible
  input cells visible *lowers* reported coverage. That is the scanner working,
  and the PR should say so rather than hiding it.

## Vocabulary

Enumerated fields have a fixed permitted value set in
`standards/vocabulary/glossary.json`, and `verify_controlled_vocabulary.py`
enforces it. Do not invent a new value for `input_kind`, `driver_type`,
`case_type`, `classification`, `basis`, `outcome_class`, or `declared_maturity`.
If a genuinely new concept appears, add it to the glossary with an ISO 704
definition — a substitutable noun phrase, not a gloss — and say why the existing
values do not cover it.

## Gates no agent may pass

- **Human sign-off (M3 criterion G).** Effective challenge requires a named
  person. Never write to `governance/signoff.json`, never mark a model M3, and
  never describe a model as validated for use.
- **Merging your own work over a red `independent-approval` check.** That check
  asks for review by someone other than the author. Ask; do not self-approve.

## Data sources

Public and citable only, recorded with provenance under `tools/data_fabric/out/`
with a source-register row and a SHA-256 digest. SEC EDGAR XBRL company facts,
U.S. Treasury par yield curves, Damodaran Online industry data, Alpha Vantage,
and FRED are the sources in use. Network egress is restricted in some
environments; if a fetch is blocked, say so and use the already-recorded corpus
rather than substituting a guess.

## Writing

Plain language, per `standards/conformance/register.json`. Short sentences,
active voice, the subject doing the acting. Define a term once and then use the
same word for it — synonym variation reads as elegance and costs the reader
precision. Say what a thing is before you say what it is for. When you find a
defect, describe it in terms of what breaks for a user, not in terms of the code
that produced it.
