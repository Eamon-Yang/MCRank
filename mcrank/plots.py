import numpy as np
from matplotlib.figure import Figure
from matplotlib import font_manager, rcParams
from pathlib import Path

rcParams['font.family'] = ['DejaVu Sans']
rcParams['axes.unicode_minus'] = False


KINDS = ['Ranking', 'Evidence', 'Profile heatmap', 'Rank uncertainty', 'Top-K', 'DAP']


def make_figure(results, kind='Ranking', group=None, mode=None):
    df = results[results.Priority.notna()].copy()
    if group is not None and not df.empty:
        df = df[df['group'] == group]
    if mode is not None and not df.empty:
        df = df[df['mode'] == mode]
    groups = list(df.groupby(['group', 'mode'], sort=False)) if not df.empty else []
    fig = Figure(figsize=(11, max(5, 4*len(groups))), constrained_layout=True)
    if not groups:
        fig.add_subplot().text(.5, .5, 'No eligible results', ha='center')
        return fig
    for n, ((g, m), frame) in enumerate(groups):
        ax = fig.add_subplot(len(groups), 1, n+1)
        d = frame.sort_values('Rank').head(30)
        labels = d.chemical_id.astype(str).tolist(); y = np.arange(len(d))
        if kind in ['Ranking', 'DAP']:
            field = 'Priority' if kind == 'Ranking' else 'DAP'
            ax.barh(y, d[field], color='#566172'); ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlim(0, 1)
            ax.set_xlabel(field)
        elif kind == 'Evidence':
            ax.scatter(d.Priority, d.ECI, c=d.DAP, cmap='viridis', s=65)
            for _, r in d.iterrows(): ax.annotate(r.chemical_id, (r.Priority, r.ECI), xytext=(4, 4), textcoords='offset points', fontsize=8)
            ax.axhline(.5, color='gray', ls='--', lw=.7); ax.axvline(.5, color='gray', ls='--', lw=.7)
            ax.set(xlim=(0, 1.05), ylim=(0, 1.05), xlabel='Priority (display divider 0.5)', ylabel='ECI (not probability)')
        elif kind == 'Profile heatmap':
            cols = ['Core', 'Exposure', 'Hazard', 'Occurrence', 'Fate_TK', 'ECI']
            cmap = __import__('matplotlib').colormaps['YlGnBu'].copy(); cmap.set_bad('#dddddd')
            im = ax.imshow(d[cols].to_numpy(float), aspect='auto', vmin=0, vmax=1, cmap=cmap)
            ax.set_xticks(range(len(cols)), cols); ax.set_yticks(y, labels); fig.colorbar(im, ax=ax, label='Score; gray = NA')
        elif kind == 'Rank uncertainty' and 'Rank_low' in d:
            ax.errorbar(d.Rank_median, y, xerr=[d.Rank_median-d.Rank_low, d.Rank_high-d.Rank_median], fmt='o', color='#566172', capsize=3)
            ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlabel('Rank median and 95% uncertainty interval')
        elif kind == 'Top-K' and 'TopK_probability' in d:
            ax.barh(y, d.TopK_probability, color='#737F90'); ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlim(0, 1); ax.set_xlabel('Top-K inclusion probability')
        else:
            ax.text(.5, .5, 'Run Monte Carlo to display this figure', ha='center')
        ax.set_title(f'{g} | {m} | {kind} (up to 30 records)')
    fig.suptitle('MCRank v1.0 — uncalibrated configurable defaults', fontsize=11)
    return fig
