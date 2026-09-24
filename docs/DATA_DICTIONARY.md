# Input data dictionary

Use UTF-8 CSV or XLSX with case-sensitive headers. Extra columns are retained but excluded from calculations.

| Field | Definition |
|---|---|
| chemical_id, chemical_name | Required stable identifier, and chemical name |
| group | Comparable scenario, period, or population; blank becomes default |
| MEC, PNEC | Environmental concentration and reviewed ecological benchmark; PNEC must be positive |
| Cbio, HB2GV | Internal exposure and applicable biomonitoring benchmark; HB2GV must be positive |
| MEC_unit, PNEC_unit, Cbio_unit, HB2GV_unit | Units required for each available concentration |
| matrix, benchmark_matrix | Sample/benchmark matrices; Human Risk requires an exact, nonempty match |
| basis, benchmark_basis | Measurement bases; Human Risk requires an exact, nonempty match |
| benchmark_accepted | yes/no; blank does not authorize benchmark use |
| DF, SO, TO | Detection frequency, spatial coverage, temporal coverage; 0–1, not percentages |
| PREV | Population coverage, 0–1 |
| occurrence_duplicate | yes excludes SO/TO/PREV; no/blank treats them as distinct descriptors |
| half_life_days | Environmental half-life in days for the freshwater scenario |
| BCF | Fish bioconcentration factor in L/kg, not logBCF or BAF |
| chronic, acute | Reviewed positive ecological toxicity concentrations; chronic takes precedence |
| chronic_unit, acute_unit | Units for the toxicity concentrations |
| hazard_accepted | yes enables the reviewed Screening hazard input |
| human_hazard | Reviewed 0–1 human hazard score; document its construction in source |
| TK | Reviewed 0–1 toxicokinetic score; takes precedence over half-life |
| human_half_life_days | Human half-life, used when TK is missing |
| source | References, provenance, selection rationale, and hazard anchors |

Concentrations are normalized to ug/L. Supported units include ng/L, ug/L, µg/L, mg/L, and ng/mL. Creatinine/lipid adjustments are not provided; ug/g is not interchangeable with ug/L.

## Evidence metadata

For each of core, occurrence, fate, exposure, and hazard, optional suffixes are `_quality` (reviewed reliability/relevance, 0–1), `_n` (nonnegative effective evidence count), and `_consistency` (reviewed consistency, 0–1).

These fields do not change Priority. Missing components are excluded and available weights renormalized. Completeness-only ECI does not establish evidence quality. Metadata coverage is separate. Risk uses core/occurrence/fate; Screening uses exposure/hazard/fate. Human fate represents TK. Simulation iterations are not evidence counts.
