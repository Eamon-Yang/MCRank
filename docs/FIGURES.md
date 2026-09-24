# README figure provenance

All images are actual outputs of the current six-page English Windows application. They are not mockups. They use the bundled 12-record synthetic dataset; they do not show measured neonicotinoid data or results from the separate Neonicotinoids repository.

| Image | Source and settings |
|---|---|
| workspace.png | Desktop data preview after loading examples/chemicals.csv |
| uncertainty-workspace.png | Eco module, Auto mode, Equal weights, Rank uncertainty chart, Risk subgroup |
| example-ranking.png | Eco self-test export; Risk and Screening shown separately |
| example-evidence.png | Eco self-test export; ECI versus Priority, with DAP color mapping |

The release self-test used 30 iterations, seed 2026, Top-K=3, and otherwise the v1.0 default configuration. Data values were held fixed; default weight and method-parameter perturbations were enabled. The associated split-half Top-K check did not demonstrate convergence. These illustrations show software functionality, not validated scientific rankings.

Run `python run.py --self-test verification/selftest` from a source installation to generate corresponding screenshots and exports. Graph appearance can vary slightly across dependency versions and display settings. Use more iterations and appropriate study-specific uncertainties for a substantive analysis.
