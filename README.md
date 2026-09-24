# MCRank v1.0

A desktop application for multidimensional chemical risk prioritization. Includes ecological and human-health Risk/Screening analysis, evidence indices, dependency controls, Monte Carlo uncertainty, and figure/table export.

## Start

Double-click **MCRank.exe** in the main folder. Keep `_internal` beside it. The packaged application needs no Python installation or internet connection.

1. Select **Load example**, or **Import data** for CSV/XLSX.
2. Review **Data validation**.
3. Choose the analysis module, mode, and weighting method.
4. Select **Run analysis**. Enable **Monte Carlo simulation** for rank intervals, Top-K probabilities, and sensitivity results.
5. Select **Export results**, or use **Export figure** on the Visualization page for PNG/PDF/SVG.

**Open project** and **Save project** preserve data and settings. Recalculate after opening a project or changing inputs. Custom weights and uncertainty distributions are configured under Parameters. The iterations, seed, and Top-K controls override their JSON counterparts.

## Data and interpretation

Use **Input template** to save a blank template. Examples are synthetic. Fields are case-sensitive; chemical identifiers must be unique within each comparison group. Blank, NA, and N/A values remain missing; observed zeros are retained. Handle censored observations such as `<LOD` according to your study protocol before import.

Concentrations have separate unit columns and are normalized to ug/L. ng/L, ug/L, µg/L, mg/L, and ng/mL are supported. Creatinine and lipid corrections are not automatically converted. Human Risk requires matching, nonempty sample and benchmark matrices and bases.

Benchmarks require `benchmark_accepted=yes`; Screening hazard inputs require `hazard_accepted=yes`. Review scientific applicability before use. See docs/DATA_DICTIONARY.md and docs/METHODS.md.

Default scientific parameters remain **uncalibrated** and configurable. Software tests do not establish predictive validity on real chemical datasets. Risk and Screening are ranked separately within groups. ECI is an evidence index, not a probability. DAP is a separate data-acquisition priority. Monte Carlo intervals describe uncertainty under configured assumptions; they are not confidence intervals.

## Outputs

Exports include results.csv/xlsx, weights.csv, normalized_input.csv, run_metadata.json, and figures. Monte Carlo also exports simulation arrays and sensitivity.csv. Use a new folder per run: existing same-named output files are overwritten.

## Source

The Source folder contains code, tests, examples, configuration, and packaging files. From Source:

```powershell
python -m pip install -r requirements.txt
python run.py
```

Testing and packaging:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python -m PyInstaller MCRank.spec --noconfirm
```

Batch mode:

```powershell
python -m mcrank --input examples/chemicals.csv --output results/eco --module Eco --mode Auto --weighting Equal --mc
```

The interface uses eight workspace pages, a neutral palette, and Segoe UI with stronger weights for headings and primary actions. There is no user-guide page.
