# Build on Windows with: python -m PyInstaller MCRank.spec --noconfirm
from pathlib import Path
import os
root = Path(SPECPATH)
a = Analysis([str(root/'run.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root/'mcrank/assets'), 'mcrank/assets'), (str(root/'examples'), 'examples'), (str(root/'config'),'config'),
                        *[(str(p), 'docs') for p in (root/'docs').glob('*.md')], (str(root/'README.md'),'.')],
    hiddenimports=['openpyxl', 'matplotlib.backends.backend_qtagg'],
    hookspath=[], hooksconfig={'matplotlib': {'backends': ['QtAgg', 'Agg']}},
    runtime_hooks=[], excludes=['tkinter', 'PyQt5', 'PyQt6', 'IPython', 'pytest', 'scipy',
                               'numba', 'llvmlite', 'lxml', 'sympy', 'torch', 'tensorflow'], noarchive=False)
pyz = PYZ(a.pure)
# Qt 6.11 imports Windows' ICU API. Do not bundle an unrelated ICU from a
# GIS/Poppler directory on PATH: its versioned exports are incompatible.
if os.name == 'nt':
    a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() not in
                  {'icuuc.dll', 'icuin.dll', 'icudt78.dll'}]
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='MCRank', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=os.environ.get('MCRANK_CONSOLE') == '1')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='MCRank')
