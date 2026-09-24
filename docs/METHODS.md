# Implemented methods and assumptions

The redesign retains the existing v1.0 calculation engine. Default method parameters remain uncalibrated. Example data are synthetic.

## Core and priority

`RALT(x;a,k)=1/[1+exp(-k log10(x/a))]`; zero maps to zero by continuity. Hazard concentration uses the opposite direction. No dataset min–max normalization is used.

Risk: `Q=MEC/PNEC` or `Cbio/HB2GV`, then `Core=RALT(Q;1,k_R)`. The modifier combines available Occurrence and Fate/TK domains. Occurrence uses DF/SO/TO for Eco and DF/PREV for Human.

Screening: Exposure combines transformed concentration with occurrence inputs. Eco Hazard uses accepted chronic evidence first, otherwise acute, with separate anchors. Human Hazard uses the reviewed 0–1 input. `Core=EH/[w_E H+(1-w_E)E]`. True zero in either required component yields zero; missing values cannot be substituted. Its modifier includes Fate/TK only.

Fate combines Persistence and Bioaccumulation. Environmental half-life and BCF use anchors of 40 days and 2,000 L/kg. Human TK uses its direct score first, otherwise half-life with a 30-day anchor. BCF is not directly replaced by logKow, BAF, BMF, or TMF.

`Gate(K)=g0+(1-g0)K^gamma`; `Priority=K+lambda Gate(K) Modifier (1-K)`, with K=Core. Constraints ensure `0<=Core<=Priority<=1`. If all modifier inputs are missing, Priority=Core and Modifier remains NA. Insufficient core data do not receive a score.

## Weights and dependencies

Available positive weights are renormalized within domains. Equal, CRITIC, and Custom are supported. Custom weights use a fixed indicator registry. CRITIC uses `C_j=sd_j sum_k(1-r_jk)` and normalized information weights; it does not rewrite core formulas. Correlations require three paired observations. Undefined correlations are treated as zero; constant/all-missing columns carry no information. Zero total information falls back to equal weights among columns with data. Small-sample weights are not established scientific importance.

Auto tries accepted applicable Risk, then Screening, otherwise Insufficient. Forced modes do not silently switch. Competition ranks (1,1,3 for ties) are calculated within group and mode. Human groups distinguish matrix and basis.

Dependency control excludes occurrence from the Screening modifier, prevents separate re-addition of risk quotient components, and selects one of TK/half-life and chronic/acute. Declared duplicate occurrence excludes SO/TO/PREV. Undocumented causal overlap is not automatically inferred.

## Evidence

Domain completeness C is observed role weight divided by expected role weight (TO defaults to 1; other roles to 2). Q and S are reviewed user inputs; `N=1-exp(-n/n0)`. Domain ECI is their available-weight geometric mean. True zero with positive weight produces zero; missing components are excluded. C is always calculated.

Overall ECI combines core/occurrence/fate for Risk and exposure/hazard/fate for Screening; Human fate denotes TK. Metadata coverage is reported separately. Completeness-only ECI does not prove reliability. `DAP=Priority(1-ECI)`. ECI, DAP, and PRI do not feed back into Priority. ECI is not a probability.

## Defaults

| Parameter | Default |
|---|---|
| k_R, k_P, k_B, k_H, k_E | 2 |
| lambda, g0, gamma | 0.35, 0.1, 1 |
| Screening w_E | 0.5 |
| Environmental half-life / BCF anchors | 40 days / 2,000 L/kg |
| Acute / chronic hazard anchors | 1,000 / 10 ug/L |
| Eco / Human exposure anchors | 1 / 1 ug/L |
| Human half-life anchor | 30 days |
| ECI C/Q/N/S weights | .3/.3/.2/.2 |
| ECI core/occurrence/fate/exposure/hazard weights | .6/.2/.2/.3/.3 |
| Evidence n0 | 10 |
| MC iterations / seed / Top-K | 1000 / 2026 / 3 |
| Dirichlet kappa / parameter fraction | 50 / 0.1 |

Scientific defaults are uncalibrated mapping and sensitivity assumptions, not universal safety limits or claimed regulatory thresholds. Applicable domain weights are renormalized.

## Uncertainty

Iterations share method parameters and group/domain weights. Configured data errors are sampled independently. Dirichlet perturbations center on nominal weights; zeros remain zero and CRITIC is not refitted. Method parameters use bounded triangular distributions centered on nominal values.

Data uncertainty is enabled only through mc.data_uncertainty. Field rules apply across chemicals: lognormal uses input as median and specified CV; beta uses input as mean and specified concentration; triangular uses input times low/high factors and input as mode. Zero and NA retain their states. No imputation, correlation matrix, or per-chemical error model is implemented.

Priority and within-group/mode ranks are recalculated each iteration. Outputs include 2.5/50/97.5 percentiles, P(rank<=K), Monte Carlo SE `sqrt(p(1-p)/B)`, and `PRI=1-(rank97.5-rank2.5)/(N-1)` (1 when N=1). Ties can include more than K chemicals.

The convergence check compares Top-K probabilities between simulation halves (default maximum-difference tolerance 0.03); it does not prove tail-quantile convergence. Sensitivity is marginal Spearman correlation of selected parameters with Priority, not Sobol indices or causal contributions.
