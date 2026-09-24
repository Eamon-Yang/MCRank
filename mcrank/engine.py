"""RALT / harmonic screening / RGPF with hierarchical evidence and IDC."""
from dataclasses import dataclass
import json
import numpy as np
import pandas as pd
from .config import defaults, validate_config
from .data import prepare


def ralt(x, anchor=1., slope=2., inverse=False):
    x = np.asarray(x, dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        z = slope * (np.log10(x) - np.log10(anchor)) * (-1 if inverse else 1)
    score = 1 / (1 + np.exp(-np.clip(z, -700, 700)))
    return np.where(x == 0, 1. if inverse else 0., score)


def aggregate(values, weights, geometric=False):
    v = np.asarray(values, float)
    w = np.asarray(weights, float)
    mask = np.isfinite(v) & (w > 0)
    if not mask.any():
        return np.nan
    v, w = v[mask], w[mask] / w[mask].sum()
    if geometric:
        return 0. if (v == 0).any() else float(np.exp(np.dot(w, np.log(v))))
    return float(np.dot(v, w))


def critic(frame):
    """Pairwise complete correlation; no imputation. Constant/all-NA -> no information."""
    sd = frame.std(ddof=0).fillna(0)
    corr = frame.corr(min_periods=3).fillna(0).clip(-1, 1)
    for j in range(len(corr)):
        corr.iloc[j, j] = 1.
    information = sd * (1 - corr).sum()
    active = frame.notna().any()
    if information.sum() <= 1e-14:
        information = active.astype(float)
    if information.sum() <= 0:
        information[:] = 1.
    return information / information.sum()


@dataclass
class Analysis:
    results: pd.DataFrame
    weights: pd.DataFrame
    issues: pd.DataFrame
    normalized: pd.DataFrame
    metadata: dict
    draws: object = None


def analyze(raw, module='Eco', mode='Auto', weighting='Equal', config=None,
            normalized=False, weight_overrides=None, evidence=True):
    c = validate_config(config or defaults())
    if module not in ['Eco', 'Human'] or mode not in ['Auto', 'Risk', 'Screening'] or weighting not in ['Equal', 'CRITIC', 'Custom']:
        raise ValueError('Invalid analysis option')
    df, issues = (raw.copy().reset_index(drop=True), pd.DataFrame()) if normalized else prepare(raw)
    if not issues.empty and (issues.severity == 'ERROR').any():
        raise ValueError(issues[issues.severity == 'ERROR'].to_string(index=False))
    eco = module == 'Eco'
    concentration, benchmark = ('MEC', 'PNEC') if eco else ('Cbio', 'HB2GV')
    suffix = 'eco' if eco else 'human'
    occurrence = ['DF', 'SO', 'TO'] if eco else ['DF', 'PREV']
    s = pd.DataFrame(index=df.index)
    for field in occurrence:
        s[field] = df[field]
    s['C'] = ralt(df[concentration], c[f'{suffix}_exposure_anchor_ug_l'], c['k_E'])
    s['P'] = ralt(df.half_life_days, c['p_anchor_days'], c['k_P'])
    s['B'] = ralt(df.BCF, c['bcf_anchor'], c['k_B'])
    s['TK'] = df.TK.where(df.TK.notna(), pd.Series(ralt(df.human_half_life_days, c['human_tk_anchor_days'], c['k_P']), index=df.index))
    if eco:
        h = pd.Series(ralt(df.chronic, c['chronic_anchor_ug_l'], c['k_H'], True), index=df.index)
        h = h.where(df.chronic.notna(), pd.Series(ralt(df.acute, c['acute_anchor_ug_l'], c['k_H'], True), index=df.index))
    else:
        h = df.human_hazard.copy()
    h = h.where(df.hazard_accepted == 'yes')
    risk_ok = df[concentration].notna() & df[benchmark].notna() & (df.benchmark_accepted == 'yes')
    if not eco:
        compatible = (df.matrix != '') & (df.matrix == df.benchmark_matrix) & (df.basis != '') & (df.basis == df.benchmark_basis)
        risk_ok &= compatible
    selected = pd.Series('Insufficient', index=df.index)
    # Exposure availability is finalized after weight aggregation below.
    screen_ok = s[['C'] + occurrence].notna().any(axis=1) & h.notna()
    if mode in ('Auto', 'Screening'):
        selected[screen_ok] = 'Screening'
    if mode in ('Auto', 'Risk'):
        selected[risk_ok] = 'Risk'
    group = df['group'].copy()
    if not eco:
        group += ' | ' + df.matrix.replace('', 'unspecified') + ' | ' + df.basis.replace('', 'unspecified')
    weights_log, rows = [], []
    for (grp, md), indices in pd.DataFrame({'g': group, 'm': selected}).groupby(['g', 'm'], sort=False).groups.items():
        f = s.loc[indices].copy()
        weights = {}
        def domain(name, columns):
            key = f'{grp}::{md}::{name}'
            if weight_overrides and key in weight_overrides:
                w = pd.Series(weight_overrides[key]).reindex(columns)
            elif weighting == 'CRITIC':
                w = critic(f[columns])
            elif weighting == 'Custom':
                w = pd.Series(c['custom_weights'][name]).reindex(columns)
                w /= w.sum()
            else:
                w = pd.Series(1 / len(columns), index=columns)
            weights[name] = w
            for field in columns:
                weights_log.append({'key': key, 'group': grp, 'mode': md, 'domain': name, 'indicator': field, 'weight': w[field]})
            return f[columns].apply(lambda r: aggregate(r.values, w.values), axis=1)
        f['F'] = domain('fate_' + suffix, ['P', 'B'] if eco else ['TK'])
        if md == 'Risk':
            f['O'] = domain('occurrence_' + suffix, occurrence)
            f['M'] = domain('modifier', ['O', 'F'])
        elif md == 'Screening':
            f['E'] = domain('exposure_' + suffix, ['C'] + occurrence)
            f['M'] = f.F
        for i in indices:
            r, z = df.loc[i], f.loc[i]
            quotient = np.nan
            if md == 'Risk':
                quotient = r[concentration] / r[benchmark]
                core = float(ralt(quotient, slope=c['k_R']))
                dependencies = f'{concentration}+{benchmark}->Core; {"+".join(occurrence)}->O; '+('half_life_days+BCF->F' if eco else 'TK OR human_half_life_days->F')
            elif md == 'Screening':
                e, hazard, a = z.E, h[i], c['screening_exposure_weight']
                core = (0. if e == 0 or hazard == 0 else e * hazard / (a * hazard + (1-a) * e)) if pd.notna(e) else np.nan
                dependencies = f'{concentration}+{"+".join(occurrence)}->E; hazard->H; E+H->Core; F->Modifier only'
            else:
                core, dependencies = np.nan, 'Missing mandatory compatible/accepted core inputs'
            modifier = z.get('M', np.nan)
            # Missing all modifiers yields the known core, explicitly flagged; no NA input is set to zero.
            score = core if pd.isna(modifier) else core + c['lambda'] * (c['g0'] + (1-c['g0']) * core ** c['gamma']) * modifier * (1-core)
            actual_mode = md if pd.notna(score) else 'Insufficient'
            out = {'input_row': i, 'chemical_id': r.chemical_id, 'chemical_name': r.chemical_name,
                   'module': module, 'group': grp, 'mode': actual_mode, 'score_type': 'RPS' if actual_mode == 'Risk' else ('SPS' if actual_mode == 'Screening' else ''),
                   'quotient': quotient, 'Core': core, 'Exposure': z.get('E', np.nan), 'Hazard': h[i] if md == 'Screening' else np.nan,
                   'Occurrence': z.get('O', np.nan), 'Persistence': z.P if eco else np.nan,
                   'Bioaccumulation': z.B if eco else np.nan, 'Fate_TK': z.F, 'Modifier': modifier, 'Priority': score,
                   'status': 'Insufficient core data' if actual_mode == 'Insufficient' else ('Core only: modifier unavailable' if pd.isna(modifier) else 'OK'),
                   'IDC': dependencies}
            if evidence and actual_mode != 'Insufficient':
                dom_fields = {'fate': ['half_life_days', 'BCF'] if eco else ['TK']}
                if not eco and pd.isna(r.TK):
                    dom_fields['fate'] = ['human_half_life_days']
                if md == 'Risk':
                    dom_fields.update(core=[concentration, benchmark], occurrence=occurrence)
                else:
                    dom_fields.update(exposure=[concentration] + occurrence,
                                      hazard=[('chronic' if pd.notna(r.chronic) else 'acute') if eco else 'human_hazard'])
                ev, dw = [], []
                for name, fields in dom_fields.items():
                    role_w = [c['optional_role_weight'] if x == 'TO' else c['supporting_role_weight'] for x in fields]
                    completeness = aggregate([float(pd.notna(r[x])) for x in fields], role_w)
                    q, n, consistency = [r[f'{name}_{t}'] for t in ['quality', 'n', 'consistency']]
                    quantity = 1 - np.exp(-n/c['evidence_n0']) if pd.notna(n) else np.nan
                    ec = aggregate([completeness, q, quantity, consistency], [c['eci_weights'][x] for x in ['C', 'Q', 'N', 'S']], True)
                    out[f'Completeness_{name}'] = completeness
                    out[f'ECI_{name}'] = ec
                    out[f'Evidence_metadata_coverage_{name}'] = sum(pd.notna(x) for x in [q, n, consistency]) / 3
                    ev.append(ec); dw.append(c['eci_domain_weights'][name])
                out['ECI'] = aggregate(ev, dw, True)
                out['DAP'] = score * (1-out['ECI'])
                if all(pd.isna(r[x]) for x in r.index if x.endswith(('_quality', '_n', '_consistency'))):
                    out['status'] += '; ECI completeness-only, evidence metadata absent'
            rows.append(out)
    result = pd.DataFrame(rows).sort_values('input_row').reset_index(drop=True)
    result['Rank'] = result.groupby(['group', 'mode']).Priority.rank(ascending=False, method='min')
    return Analysis(result, pd.DataFrame(weights_log), issues, df,
                    {'software': 'MCRank 1.0.0', 'module': module, 'mode': mode, 'weighting': weighting,
                     'config': c, 'ranking': 'Separate comparison group and mode; competition ranks for ties',
                     'uncalibrated': True, 'input_rows': len(df)})
