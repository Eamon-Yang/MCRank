"""Strict wide-format input with explicit units and comparability groups."""
from pathlib import Path
import numpy as np
import pandas as pd

CONCENTRATIONS = ['MEC', 'PNEC', 'Cbio', 'HB2GV', 'acute', 'chronic']
NUMERIC = CONCENTRATIONS + ['DF', 'SO', 'TO', 'PREV', 'half_life_days', 'BCF',
                          'human_half_life_days', 'human_hazard', 'TK']
DOMAINS = ['core', 'occurrence', 'fate', 'exposure', 'hazard']
EVIDENCE = [f'{d}_{s}' for d in DOMAINS for s in ['quality', 'n', 'consistency']]
TEXT = ['chemical_id', 'chemical_name', 'group', 'matrix', 'benchmark_matrix',
        'basis', 'benchmark_basis', 'benchmark_accepted', 'hazard_accepted', 'source',
        'occurrence_duplicate'] + [f'{x}_unit' for x in CONCENTRATIONS]
FACTORS = {'ng/L': .001, 'ug/L': 1., 'µg/L': 1., 'μg/L': 1., 'mg/L': 1000., 'ng/mL': 1.}


def read_data(path, sheet=0):
    p = Path(path)
    if p.suffix.lower() == '.csv':
        return pd.read_csv(p, encoding='utf-8-sig', keep_default_na=False, dtype=str)
    if p.suffix.lower() == '.xlsx':
        return pd.read_excel(p, sheet_name=sheet, keep_default_na=False, dtype=str)
    raise ValueError('Only CSV and XLSX are supported')


def prepare(raw):
    df = raw.copy().reset_index(drop=True)
    issues = []
    def issue(row, level, field, message):
        issues.append({'row': row + 2 if row >= 0 else '', 'severity': level, 'field': field, 'message': message})
    if df.empty:
        issue(-1, 'ERROR', 'data', 'No chemical records')
    if df.columns.duplicated().any():
        issue(-1, 'ERROR', 'columns', 'Duplicate column names')
        df = df.loc[:, ~df.columns.duplicated()]
    for col in df.columns:
        if col not in NUMERIC + EVIDENCE + TEXT:
            issue(-1, 'WARNING', col, 'Not used by v1.0; retained as metadata only')
    for col in TEXT:
        if col not in df:
            df[col] = ''
        df[col] = df[col].fillna('').astype(str).str.strip()
    for col in NUMERIC + EVIDENCE:
        if col not in df:
            df[col] = np.nan
        original = df[col].astype(str).str.strip()
        missing = df[col].isna() | original.str.lower().isin(['', 'na', 'nan', 'none', 'n/a'])
        values = pd.to_numeric(original.where(~missing), errors='coerce')
        for i in df.index[(~missing) & (~np.isfinite(values))]:
            issue(i, 'ERROR', col, 'Expected finite numeric value; censored values require explicit preprocessing')
        df[col] = values
        for i in df.index[values < 0]:
            issue(i, 'ERROR', col, 'Negative values are invalid')
        if col in ['DF', 'SO', 'TO', 'PREV', 'human_hazard', 'TK'] or col.endswith(('_quality', '_consistency')):
            for i in df.index[values > 1]:
                issue(i, 'ERROR', col, 'Expected proportion/score in [0,1], not percent')
        if col in ['PNEC', 'HB2GV', 'acute', 'chronic']:
            for i in df.index[values == 0]:
                issue(i, 'ERROR', col, 'Effect benchmark must be > 0')
    for i, r in df.iterrows():
        if not r.chemical_id:
            issue(i, 'ERROR', 'chemical_id', 'Required unique identifier')
        if not r['group']:
            df.at[i, 'group'] = 'default'
        for flag in ['benchmark_accepted', 'hazard_accepted', 'occurrence_duplicate']:
            if r[flag] not in ['', 'yes', 'no']:
                issue(i, 'ERROR', flag, 'Use yes / no / blank')
        if r.benchmark_accepted == '':
            issue(i, 'WARNING', 'benchmark_accepted', 'Blank means benchmark is NOT accepted for Risk')
        for col in CONCENTRATIONS:
            if pd.notna(r[col]):
                unit = r[f'{col}_unit']
                if unit not in FACTORS:
                    issue(i, 'ERROR', f'{col}_unit', 'Use ng/L, ug/L, mg/L or ng/mL (mass/volume only)')
                else:
                    df.at[i, col] *= FACTORS[unit]
                    df.at[i, f'{col}_unit'] = 'ug/L'
        if r.occurrence_duplicate == 'yes':
            # Prevalence / spatial / temporal descriptors declared to repeat DF are excluded.
            df.loc[i, ['SO', 'TO', 'PREV']] = np.nan
            issue(i, 'WARNING', 'occurrence_duplicate', 'IDC excluded SO/TO/PREV; DF retained')
    dup = df.duplicated(['chemical_id', 'group'], keep=False)
    for i in df.index[dup]:
        issue(i, 'ERROR', 'chemical_id', 'Duplicate chemical within comparison group')
    return df, pd.DataFrame(issues, columns=['row', 'severity', 'field', 'message'])


def template():
    return pd.DataFrame(columns=TEXT + NUMERIC + EVIDENCE)
