"""Explicit Monte Carlo assumptions, independent draws and reproducible ranking."""
import copy
import numpy as np
import pandas as pd
from .engine import analyze
from .data import NUMERIC


def monte_carlo(analysis, progress=None, cancelled=None):
    meta, data = analysis.metadata, analysis.normalized
    cfg = meta['config']; mc = cfg['mc']; b = mc['iterations']
    rng = np.random.default_rng(mc['seed'])
    specs = mc['data_uncertainty']
    for field, spec in specs.items():
        if field not in NUMERIC:
            raise ValueError(f'Uncertainty: unsupported field {field}')
        if spec.get('distribution') not in ['lognormal', 'beta', 'triangular']:
            raise ValueError(f'{field}: choose lognormal, beta or triangular')
        dist = spec['distribution']
        if dist == 'lognormal' and (not np.isfinite(spec.get('cv', np.nan)) or spec['cv'] <= 0):
            raise ValueError(f'{field}: positive CV required')
        if dist == 'beta' and (not np.isfinite(spec.get('concentration', np.nan)) or spec['concentration'] <= 0):
            raise ValueError(f'{field}: positive beta concentration required')
        if dist == 'triangular' and not (0 <= spec.get('low_factor', -1) < 1 < spec.get('high_factor', -1)):
            raise ValueError(f'{field}: require 0 <= low_factor < 1 < high_factor')
        if field in ['DF', 'SO', 'TO', 'PREV', 'TK', 'human_hazard'] and dist != 'beta':
            raise ValueError(f'{field}: bounded score requires beta uncertainty')
        if dist == 'beta' and field not in ['DF', 'SO', 'TO', 'PREV', 'TK', 'human_hazard']:
            raise ValueError(f'{field}: beta only allowed for bounded scores')
    nominal = analysis.results
    scores = np.full((b, len(data)), np.nan)
    ranks = np.full_like(scores, np.nan)
    parameter_samples = []
    fixed = {key: dict(zip(g.indicator, g.weight)) for key, g in analysis.weights.groupby('key')}
    for j in range(b):
        if cancelled and cancelled():
            raise InterruptedError('Monte Carlo cancelled; nominal results retained')
        c = copy.deepcopy(cfg)
        for k in ['k_R', 'k_P', 'k_B', 'k_H', 'k_E', 'lambda', 'g0', 'gamma']:
            v, fraction = cfg[k], mc['parameter_fraction']
            c[k] = float(rng.triangular(v*(1-fraction), v, v*(1+fraction))) if fraction and v else v
        c['lambda'] = min(.8, c['lambda']); c['g0'] = min(.5, c['g0'])
        parameter_samples.append({k: c[k] for k in ['k_R', 'k_H', 'lambda', 'g0', 'gamma']})
        weights = copy.deepcopy(fixed)
        if mc['vary_weights']:
            for key, w in weights.items():
                active = [k for k, v in w.items() if v > 0]
                values = np.array([w[k] for k in active]); values /= values.sum()
                sampled = rng.dirichlet(mc['weight_kappa'] * values)
                for k, v in zip(active, sampled):
                    w[k] = float(v)
        sampled = data.copy()
        for field, spec in specs.items():
            x = data[field].to_numpy(float).copy()
            valid = np.isfinite(x) & (x > 0)
            if spec['distribution'] == 'lognormal':
                sigma = np.sqrt(np.log1p(spec['cv'] ** 2))
                # Point input is the median; CV controls log-space width.
                x[valid] = rng.lognormal(np.log(x[valid]), sigma)
            elif spec['distribution'] == 'beta':
                valid &= x < 1
                k = spec['concentration']
                x[valid] = rng.beta(x[valid]*k, (1-x[valid])*k)
            else:
                x[valid] = rng.triangular(x[valid]*spec['low_factor'], x[valid], x[valid]*spec['high_factor'])
            sampled[field] = x
        sim = analyze(sampled, meta['module'], meta['mode'], meta['weighting'], c,
                      normalized=True, weight_overrides=weights, evidence=False).results
        scores[j] = sim.Priority
        ranks[j] = sim.Rank
        if progress and (j % max(1, b//100) == 0 or j == b-1):
            progress(int(100*(j+1)/b))
    out = nominal.copy()
    valid = np.isfinite(scores).any(axis=0)
    for array, prefix in [(scores, 'Priority'), (ranks, 'Rank')]:
        for q, name in [(2.5, 'low'), (50, 'median'), (97.5, 'high')]:
            out[f'{prefix}_{name}'] = np.nan
            out.loc[valid, f'{prefix}_{name}'] = np.nanpercentile(array[:, valid], q, axis=0)
    top = (ranks <= mc['top_k']).astype(float)
    out['TopK_probability'] = np.where(valid, top.mean(axis=0), np.nan)
    out['TopK_MCSE'] = np.sqrt(out.TopK_probability*(1-out.TopK_probability)/b)
    sizes = out.groupby(['group', 'mode']).Priority.transform('count')
    out['PRI'] = np.where(sizes > 1, 1-(out.Rank_high-out.Rank_low)/(sizes-1), np.where(valid, 1., np.nan))
    half = b//2
    delta = np.max(np.abs(top[:half, valid].mean(axis=0)-top[half:, valid].mean(axis=0))) if half and valid.any() else np.nan
    sensitivity = []
    pframe = pd.DataFrame(parameter_samples)
    for i in np.flatnonzero(valid):
        for field in pframe:
            a = pframe[field].rank(); y = pd.Series(scores[:, i]).rank()
            rho = a.corr(y) if a.std() > 0 and y.std() > 0 else np.nan
            sensitivity.append({'chemical_id': out.loc[i, 'chemical_id'], 'group': out.loc[i, 'group'], 'parameter': field, 'spearman': rho})
    analysis.results = out
    analysis.draws = {'scores': scores, 'ranks': ranks, 'sensitivity': pd.DataFrame(sensitivity)}
    analysis.metadata['monte_carlo'] = {
        'iterations': b, 'seed': mc['seed'], 'top_k': mc['top_k'],
        'assumption': 'Independent data draws across fields and chemicals; shared parameter/weight draws. Missing values stay missing; no ECI-derived noise.',
        'data_uncertainty': specs, 'weights': 'Dirichlet around nominal; CRITIC not refitted per draw',
        'topk_split_half_max_difference': float(delta) if np.isfinite(delta) else None,
        'convergence_diagnostic': 'within tolerance' if delta <= mc['convergence_tolerance'] else 'not demonstrated; increase iterations',
        'convergence_scope': 'Split-half Top-K stability only; not a proof of full distribution convergence',
        'tie_policy': 'Competition ranks; all tied chemicals at K count as Top-K (can exceed K)',
        'sensitivity': 'Marginal Spearman parameter-score association, not causal attribution'}
    return analysis
