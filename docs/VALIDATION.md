# Software verification

The computational engine, data validation, uncertainty calculations, and export logic retain the existing v1.0 implementation.

During development, the 30-test regression suite passed on the Windows build machine. After removing the Parameters and Run log pages, the two GUI regression tests passed again, including example analysis and project save/open. The final executable then passed the release self-test, including all six navigation pages, Eco/Human calculations, 30-iteration Monte Carlo, and XLSX/PNG export.

The executable was also tested after deleting the old project-specific dependencies from the C drive, with the old Python dependency path excluded. It completed the same self-test successfully.

To check a source installation:

```powershell
python -m pytest tests -q
python run.py --self-test verification/selftest
```

To check a packaged Windows distribution:

```powershell
.\MCRank.exe --self-test verification/selftest
```

Successful self-tests write selftest.json, screenshots, and example exports. Keep these generated files outside version control.

These checks establish software behavior on the tested machine. They do not establish scientific calibration, predictive validity, convergence of every Monte Carlo analysis, or compatibility with all operating systems. A 30-iteration self-test is intentionally short and is not a research-grade uncertainty analysis.
