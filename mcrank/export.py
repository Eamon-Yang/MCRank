import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .plots import make_figure, KINDS


def safe_table(df):
    out = df.copy()
    for col in out.select_dtypes(include=['object', 'str']).columns:
        out[col] = out[col].map(lambda v: "'"+v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v)
    return out


def export_results(analysis, folder, figures=True):
    p = Path(folder); p.mkdir(parents=True, exist_ok=True)
    safe_table(analysis.results).to_csv(p/'results.csv', index=False, encoding='utf-8-sig', na_rep='NA')
    safe_table(analysis.weights).to_csv(p/'weights.csv', index=False, encoding='utf-8-sig')
    safe_table(analysis.normalized).to_csv(p/'normalized_input.csv', index=False, encoding='utf-8-sig', na_rep='NA')
    with pd.ExcelWriter(p/'results.xlsx', engine='openpyxl') as writer:
        for name, table in [('Results', analysis.results), ('Weights', analysis.weights), ('Validation', analysis.issues), ('Normalized input', analysis.normalized)]:
            safe_table(table).to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]; ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
        if analysis.draws:
            analysis.draws['sensitivity'].to_excel(writer, sheet_name='Sensitivity', index=False)
    meta = dict(analysis.metadata)
    meta['normalized_input_sha256'] = hashlib.sha256(analysis.normalized.to_csv(index=False).encode()).hexdigest()
    (p/'run_metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    if analysis.draws:
        np.savez_compressed(p/'monte_carlo_draws.npz', scores=analysis.draws['scores'], ranks=analysis.draws['ranks'])
        analysis.draws['sensitivity'].to_csv(p/'sensitivity.csv', index=False, encoding='utf-8-sig', na_rep='NA')
    if figures:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        for kind in KINDS:
            fig = make_figure(analysis.results, kind); FigureCanvasAgg(fig)
            fig.savefig(p/(kind.replace(' ', '_')+'.png'), dpi=220)
    return p
