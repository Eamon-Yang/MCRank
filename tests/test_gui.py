import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer
from mcrank.gui import MainWindow, Worker
from mcrank.config import defaults


def test_gui_example_and_background_run():
    app=QApplication.instance() or QApplication([])
    window=MainWindow(); window.show(); window.load_example()
    assert len(window.raw) >= 10
    worker=Worker(window.raw,'Eco','Auto','Equal',defaults(),False)
    loop=QEventLoop(); results=[]; errors=[]
    worker.completed.connect(results.append); worker.failed.connect(errors.append)
    worker.finished.connect(loop.quit); QTimer.singleShot(30000,loop.quit)
    worker.start(); loop.exec(); worker.wait(5000)
    assert not errors and results
    window.finished(results[0]); app.processEvents()
    assert window.results.model().rowCount() == len(window.raw)
    window.chart.setCurrentText('Evidence'); app.processEvents()
    window.close()


def test_gui_project_roundtrip(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    app=QApplication.instance() or QApplication([])
    w=MainWindow(); w.load_example(); w.module.setCurrentText('Human'); w.topk.setValue(5)
    target=str(tmp_path/'project.json')
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(target,''))
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(target,''))
    w.save_project(); w.module.setCurrentText('Eco'); w.topk.setValue(1); w.open_project()
    assert w.module.currentText()=='Human' and w.topk.value()==5 and len(w.raw)==12
    w.close()
