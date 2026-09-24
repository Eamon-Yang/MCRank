import copy
import numpy as np
import pandas as pd
import pytest
from mcrank.config import defaults, validate_config
from mcrank.data import prepare
from mcrank.engine import analyze, aggregate, ralt, critic
from mcrank.uncertainty import monte_carlo
from mcrank.export import export_results


def records():
    return pd.DataFrame([
        dict(chemical_id='A', MEC=2, PNEC=1, MEC_unit='ug/L', PNEC_unit='ug/L', benchmark_accepted='yes', DF=.5, half_life_days=40, BCF=2000),
        dict(chemical_id='B', MEC=1, MEC_unit='ug/L', chronic=10, chronic_unit='ug/L', hazard_accepted='yes', DF=.5, half_life_days=40),
        dict(chemical_id='C', MEC=0, PNEC=1, MEC_unit='ug/L', PNEC_unit='ug/L', benchmark_accepted='yes'),
        dict(chemical_id='D', BCF=2000)])


def test_ralt_anchors_monotonic():
    assert float(ralt(1)) == .5
    assert float(ralt(40,40)) == .5
    assert float(ralt(0)) < 1e-200
    assert np.all(np.diff(ralt([.01,.1,1,10,100])) > 0)
    assert np.all(np.diff(ralt([.01,.1,1],inverse=True)) < 0)


def test_missing_is_not_zero():
    assert aggregate([np.nan,.8],[.5,.5]) == .8
    assert aggregate([0,.8],[.5,.5]) == .4
    assert np.isnan(aggregate([np.nan],[1]))
    assert aggregate([0,.8],[1,1],True) == 0


def test_modes_and_no_mixed_ranking():
    r = analyze(records()).results
    assert r['mode'].tolist() == ['Risk','Screening','Risk','Insufficient']
    assert r.Rank.tolist()[:3] == [1,1,2]
    assert pd.isna(r.Priority.iloc[3])
    assert r.Priority.iloc[2] < 1e-200
    assert r.Fate_TK.iloc[1] == .5


def test_risk_formula_by_hand():
    r = analyze(records()).results.iloc[0]
    k = 1/(1+np.exp(-2*np.log10(2)))
    expected = k + .35*(.1+.9*k)*.5*(1-k)
    assert r.Priority == pytest.approx(expected)


def test_screening_no_occurrence_modifier():
    r = analyze(records()).results.iloc[1]
    assert r.Exposure == .5 and r.Hazard == .5 and r.Core == .5
    assert r.Modifier == .5 and pd.isna(r.Occurrence)
    assert r.Priority == pytest.approx(.5+.35*.55*.5*.5)


def test_unit_conversion():
    d = records(); d.loc[0,['MEC','MEC_unit']] = [2000,'ng/L']
    assert analyze(d).results.quotient.iloc[0] == 2


@pytest.mark.parametrize('field,value',[('PNEC',0),('MEC',-1),('DF',10),('MEC','<0.1'),('MEC','inf')])
def test_invalid_data_blocked(field,value):
    d = records().astype(object); d.loc[0,field] = value
    with pytest.raises(ValueError): analyze(d)


def test_duplicate_id():
    d = records(); d.loc[1,'chemical_id'] = 'A'
    with pytest.raises(ValueError): analyze(d)


def test_dependency_config_and_declared_duplicate():
    c = defaults(); c['custom_weights']['modifier']['MEC']=1
    with pytest.raises(ValueError): validate_config(c)
    d = records(); d['SO']=.9; d['occurrence_duplicate']='yes'
    assert analyze(d).results.Occurrence.iloc[0] == .5


def test_human_compatibility_and_screening():
    d = pd.DataFrame([dict(chemical_id='H', Cbio=2, HB2GV=1, Cbio_unit='ug/L', HB2GV_unit='ug/L', benchmark_accepted='yes', matrix='serum', benchmark_matrix='serum', basis='wet', benchmark_basis='wet', human_hazard=.7, hazard_accepted='yes', TK=.5)])
    assert analyze(d,'Human').results['mode'].iloc[0] == 'Risk'
    d.loc[0,'benchmark_matrix']='urine'
    assert analyze(d,'Human').results['mode'].iloc[0] == 'Screening'
    assert analyze(d,'Human','Risk').results['mode'].iloc[0] == 'Insufficient'


def test_eci_does_not_change_priority():
    d = records(); first = analyze(d).results
    for domain in ['core','occurrence','fate','exposure','hazard']:
        d[domain+'_quality']=.2; d[domain+'_n']=2; d[domain+'_consistency']=.3
    last = analyze(d).results
    np.testing.assert_allclose(first.Priority,last.Priority,equal_nan=True)
    assert last.ECI.iloc[0] < first.ECI.iloc[0]
    assert last.DAP.iloc[0] == pytest.approx(last.Priority.iloc[0]*(1-last.ECI.iloc[0]))


@pytest.mark.parametrize('weighting',['Equal','CRITIC','Custom'])
def test_weights_finite_and_bounded(weighting):
    a=analyze(records(),weighting=weighting)
    assert np.isfinite(a.weights.weight).all()
    assert a.results.Priority.dropna().between(0,1).all()
    for _,g in a.weights.groupby('key'): assert g.weight.sum()==pytest.approx(1)


def test_critic_constant_missing():
    w=critic(pd.DataFrame({'a':[1,1,1], 'b':[np.nan]*3}))
    assert w.a == 1 and w.b == 0


def test_mc_reproducible_and_no_invented_data_noise():
    c=defaults(); c['mc'].update(iterations=12, vary_weights=False, parameter_fraction=0)
    a=monte_carlo(analyze(records(),config=c)); b=monte_carlo(analyze(records(),config=c))
    np.testing.assert_allclose(a.draws['scores'],b.draws['scores'],equal_nan=True)
    np.testing.assert_allclose(a.results.Priority_median,a.results.Priority,equal_nan=True)
    assert a.results.PRI.dropna().eq(1).all()
    assert a.results.TopK_probability.iloc[1] == 1
    assert pd.isna(a.results.TopK_probability.iloc[3])


def test_exports(tmp_path):
    a=analyze(records()); export_results(a,tmp_path)
    assert (tmp_path/'results.xlsx').stat().st_size > 1000
    assert (tmp_path/'Ranking.png').stat().st_size > 1000
    assert len(pd.read_excel(tmp_path/'results.xlsx')) == 4


def test_accepted_benchmark_required():
    d=records(); d.loc[0,'benchmark_accepted']=''
    assert analyze(d).results['mode'].iloc[0]=='Insufficient'


def test_chronic_precedence_not_acute_mix():
    d=records(); d.loc[1,'acute']=.001; d.loc[1,'acute_unit']='ug/L'
    assert analyze(d).results.Hazard.iloc[1] == .5


def test_parameter_bounds():
    c=defaults(); c['lambda']=1
    with pytest.raises(ValueError): validate_config(c)


def test_random_mc_data_noise_reproducible_and_nonzero():
    d=records().iloc[[0]].copy()
    second=d.copy(); second['chemical_id']='A2'; second['MEC']=1.95
    d=pd.concat([d,second],ignore_index=True)
    c=defaults(); c['mc'].update(iterations=40,top_k=1)
    c['mc']['data_uncertainty']={'MEC':{'distribution':'lognormal','cv':.5}}
    a=monte_carlo(analyze(d,config=c)); b=monte_carlo(analyze(d,config=c))
    np.testing.assert_allclose(a.draws['scores'],b.draws['scores'])
    assert np.std(a.draws['scores'][:,0]) > .01
    assert 0 < a.results.TopK_probability.iloc[0] < 1
    assert a.results.TopK_probability.sum() == pytest.approx(1)


def test_tied_topk_and_cancel():
    d=records().iloc[[0]].copy(); other=d.copy(); other['chemical_id']='TIE'
    d=pd.concat([d,other],ignore_index=True)
    c=defaults(); c['mc'].update(iterations=4,top_k=1,vary_weights=False,parameter_fraction=0)
    a=monte_carlo(analyze(d,config=c))
    assert a.results.TopK_probability.tolist()==[1,1]
    with pytest.raises(InterruptedError): monte_carlo(analyze(d,config=c),cancelled=lambda:True)


def test_input_order_does_not_change_equal_scores():
    a=analyze(records()).results.set_index('chemical_id')
    b=analyze(records().iloc[::-1]).results.set_index('chemical_id').reindex(a.index)
    np.testing.assert_allclose(a.Priority,b.Priority,equal_nan=True)


def test_evidence_config_key_order_does_not_change_eci():
    c=defaults(); c['eci_weights']=dict(reversed(list(c['eci_weights'].items())))
    np.testing.assert_allclose(analyze(records(),config=c).results.ECI,analyze(records()).results.ECI,equal_nan=True)
