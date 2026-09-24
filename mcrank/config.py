"""Explicit, uncalibrated v1.0 implementation defaults."""
import copy
import json
import math

DEFAULTS = {
    'schema_version': 1, 'scenario': 'Freshwater surface water',
    'calibration_status': 'UNCALIBRATED v1.0 defaults',
    'k_R': 2.0, 'k_P': 2.0, 'k_B': 2.0, 'k_H': 2.0, 'k_E': 2.0,
    'lambda': 0.35, 'g0': 0.1, 'gamma': 1.0,
    'p_anchor_days': 40.0, 'bcf_anchor': 2000.0,
    'eco_exposure_anchor_ug_l': 1.0, 'human_exposure_anchor_ug_l': 1.0,
    'acute_anchor_ug_l': 1000.0, 'chronic_anchor_ug_l': 10.0,
    'human_tk_anchor_days': 30.0, 'screening_exposure_weight': 0.5,
    'eci_weights': {'C': 0.3, 'Q': 0.3, 'N': 0.2, 'S': 0.2},
    'eci_domain_weights': {'core': 0.6, 'occurrence': 0.2, 'fate': 0.2,
                           'exposure': 0.3, 'hazard': 0.3},
    'evidence_n0': 10.0, 'optional_role_weight': 1.0, 'supporting_role_weight': 2.0,
    'custom_weights': {
        'occurrence_eco': {'DF': 1, 'SO': 1, 'TO': 1},
        'occurrence_human': {'DF': 1, 'PREV': 1},
        'exposure_eco': {'C': 1, 'DF': 1, 'SO': 1, 'TO': 1},
        'exposure_human': {'C': 1, 'DF': 1, 'PREV': 1},
        'fate_eco': {'P': 1, 'B': 1}, 'fate_human': {'TK': 1},
        'modifier': {'O': 1, 'F': 1}},
    'mc': {'iterations': 1000, 'seed': 2026, 'top_k': 3,
           'weight_kappa': 50.0, 'vary_weights': True, 'parameter_fraction': 0.1,
           'convergence_tolerance': 0.03, 'data_uncertainty': {}}
}


def defaults():
    return copy.deepcopy(DEFAULTS)


def validate_config(c):
    if set(c) != set(DEFAULTS):
        raise ValueError('Configuration keys must match the v1.0 template.')
    for k, v in DEFAULTS.items():
        if isinstance(v, (float, int)):
            if not isinstance(c[k], (float, int)) or not math.isfinite(c[k]):
                raise ValueError(f'{k}: finite number required')
            if c[k] <= 0 and k not in ('lambda', 'g0'):
                raise ValueError(f'{k}: must be positive')
    if not 0 <= c['lambda'] <= 0.8 or not 0 <= c['g0'] <= 0.5:
        raise ValueError('v1.0 gate limits: lambda 0–0.8, g0 0–0.5')
    if not 0 < c['screening_exposure_weight'] < 1:
        raise ValueError('Screening exposure weight must lie strictly between 0 and 1')
    for section in ('eci_weights', 'eci_domain_weights', 'custom_weights'):
        groups = c[section] if section == 'custom_weights' else {section: c[section]}
        expected = DEFAULTS[section] if section == 'custom_weights' else {section: DEFAULTS[section]}
        if set(groups) != set(expected):
            raise ValueError(f'{section}: unsupported groups (IDC enforced)')
        for name, weights in groups.items():
            if set(weights) != set(expected[name]):
                raise ValueError(f'{name}: unsupported indicators; dependency control forbids extra inputs')
            if any(not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
                raise ValueError(f'{name}: nonnegative weights with positive sum required')
    m = c['mc']
    if set(m) != set(DEFAULTS['mc']):
        raise ValueError('MC keys must match template')
    for key in ('iterations', 'seed', 'top_k'):
        if type(m[key]) is not int or m[key] < (0 if key == 'seed' else 1):
            raise ValueError(f'MC {key}: valid integer required')
    if m['iterations'] > 100000:
        raise ValueError('Maximum 100000 iterations')
    for key in ('weight_kappa', 'convergence_tolerance'):
        if not math.isfinite(m[key]) or m[key] <= 0:
            raise ValueError(f'MC {key}: positive finite value required')
    if not 0 <= m['parameter_fraction'] < 1:
        raise ValueError('MC parameter_fraction must be in [0,1)')
    return c


def load_config(path):
    with open(path, encoding='utf-8-sig') as f:
        return validate_config(json.load(f))
