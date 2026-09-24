"""Noninteractive diagnostics for source and frozen Windows distributions."""
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from .gui import MainWindow, ROOT, setup_app
from .config import defaults
from .data import read_data
from .engine import analyze
from .uncertainty import monte_carlo
from .export import export_results


def run(folder):
    p=Path(folder); p.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([])
    setup_app(app)
    window=MainWindow(); window.show(); window.load_example(); app.processEvents()
    assert window.tabs.count() == 6
    assert window.navigation.count() == 6
    for index in range(6):
        window.navigation.setCurrentRow(index)
        assert window.tabs.currentIndex() == index
    window.tabs.setCurrentIndex(0)
    assert window.navigation.currentRow() == 0
    app.processEvents(); window.grab().save(str(p/'Preview_GUI.png'))
    raw=read_data(ROOT/'examples'/'chemicals.xlsx')
    c=defaults(); c['mc']['iterations']=30
    for module in ['Eco','Human']:
        result=monte_carlo(analyze(raw,module,config=c))
        export_results(result,p/module)
        window.finished(result); app.processEvents()
        window.tabs.setCurrentIndex(4); window.chart.setCurrentText('Rank uncertainty'); app.processEvents()
        window.grab().save(str(p/f'{module}_GUI.png'))
    window.close(); app.processEvents()
    (p/'selftest.json').write_text(json.dumps({'status':'passed','modules':['Eco','Human'],'iterations':30,'gui':True,'xlsx_png_export':True}),encoding='utf-8')
