"""PySide6 desktop workflow; calculations run outside the UI thread."""
import json
from copy import deepcopy
import sys
from pathlib import Path
import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QThread, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox, QTabWidget, QTableView, QPlainTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QSplitter, QFormLayout)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from .config import defaults, validate_config
from .data import read_data, prepare, template
from .engine import analyze
from .uncertainty import monte_carlo
from .export import export_results
from .plots import make_figure, KINDS


ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))


class TableModel(QAbstractTableModel):
    def __init__(self, frame):
        super().__init__(); self.frame = frame

    def rowCount(self, parent=None): return len(self.frame)
    def columnCount(self, parent=None): return len(self.frame.columns)
    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            v = self.frame.iloc[index.row(), index.column()]
            if pd.isna(v): return 'NA'
            return f'{v:.5g}' if isinstance(v, float) else str(v)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return str(self.frame.columns[section]) if orientation == Qt.Horizontal else str(section+1)

    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        self.frame = self.frame.sort_values(self.frame.columns[column], ascending=order == Qt.AscendingOrder, na_position='last')
        self.layoutChanged.emit()


class Worker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, raw, module, mode, weighting, config, mc):
        super().__init__(); self.args = (raw, module, mode, weighting, config); self.mc = mc

    def run(self):
        try:
            result = analyze(*self.args)
            if self.mc:
                result = monte_carlo(result, self.progress.emit, self.isInterruptionRequested)
            self.completed.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.raw = pd.DataFrame(); self.analysis = None; self.worker = None
        self._config = defaults()
        from .appearance import build_layout
        build_layout(self)

    def add_table(self, title):
        table = QTableView(); table.setSortingEnabled(True); table.setAlternatingRowColors(True)
        table.setShowGrid(False); table.verticalHeader().setDefaultSectionSize(42)
        table.verticalHeader().hide()
        table.setSelectionBehavior(QTableView.SelectRows)
        self.tabs.addTab(table, title); return table

    def show_table(self, table, frame):
        table.setModel(TableModel(frame)); table.resizeColumnsToContents()
        for c in range(len(frame.columns)):
            table.setColumnWidth(c, min(280, max(95, table.columnWidth(c))))

    def error(self, e): QMessageBox.warning(self, 'MCRank', str(e))

    def set_data(self, raw):
        self.raw = raw; self.analysis = None
        self.record_count.setText(f'{len(raw):,} records')
        normalized, issues = prepare(raw)
        self.show_table(self.preview, raw); self.show_table(self.validation, issues)
        self.show_table(self.results, pd.DataFrame()); self.show_table(self.weights, pd.DataFrame()); self.show_table(self.sensitivity, pd.DataFrame())
        self.refresh_plot()
        errors = int((issues.severity == 'ERROR').sum())
        self.statusBar().showMessage(f'{len(raw)} records · {errors} errors · {len(issues)-errors} notices')
        self.tabs.setCurrentWidget(self.validation if errors else self.preview)

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import data', '', 'Data (*.csv *.xlsx)')
        if path:
            try:
                sheet = 0
                if path.lower().endswith('.xlsx'):
                    from PySide6.QtWidgets import QInputDialog
                    names = pd.ExcelFile(path, engine='openpyxl').sheet_names
                    sheet, ok = QInputDialog.getItem(self, 'Worksheet', 'Select a data worksheet', names, 0, False)
                    if not ok: return
                self.set_data(read_data(path, sheet))
            except Exception as e: self.error(e)

    def load_example(self):
        try: self.set_data(read_data(ROOT/'examples'/'chemicals.csv'))
        except Exception as e: self.error(e)

    def save_template(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save input template', 'MCRank_template.csv', 'CSV (*.csv);;Excel (*.xlsx)')
        if path:
            try:
                if path.lower().endswith('.xlsx'): template().to_excel(path, index=False)
                else: template().to_csv(path, index=False, encoding='utf-8-sig')
            except Exception as e: self.error(e)

    def config(self):
        c = deepcopy(self._config)
        c['mc'].update(iterations=self.iterations.value(), seed=self.seed.value(), top_k=self.topk.value())
        return validate_config(c)

    def set_config(self, c):
        validate_config(c); self._config = deepcopy(c)
        self.iterations.setValue(c['mc']['iterations']); self.seed.setValue(c['mc']['seed']); self.topk.setValue(c['mc']['top_k'])

    def check_config(self):
        try:
            self.config(); self.statusBar().showMessage('Parameters validated; defaults remain uncalibrated')
        except Exception as e: self.error(e)

    def import_config(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import parameters', '', 'JSON (*.json)')
        if path:
            try: self.set_config(json.loads(Path(path).read_text(encoding='utf-8-sig')))
            except Exception as e: self.error(e)

    def export_config(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export parameters', 'parameters.json', 'JSON (*.json)')
        if path:
            try: Path(path).write_text(json.dumps(self.config(), ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception as e: self.error(e)

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save project', 'project.mcrank.json', 'MCRank (*.json)')
        if path:
            try:
                project = {'version': 1, 'config': self.config(), 'data': json.loads(self.raw.to_json(orient='split')),
                           'module': self.module.currentText(), 'mode': self.mode.currentText(), 'weighting': self.weighting.currentText(), 'mc': self.mc.isChecked()}
                Path(path).write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception as e: self.error(e)

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open project', '', 'MCRank (*.json)')
        if path:
            try:
                p = json.loads(Path(path).read_text(encoding='utf-8-sig'))
                if p['version'] != 1: raise ValueError('Unsupported project version')
                self.set_config(p['config']); self.set_data(pd.DataFrame(p['data']['data'], columns=p['data']['columns']))
                self.module.setCurrentText(p['module']); self.mode.setCurrentText(p['mode']); self.weighting.setCurrentText(p['weighting']); self.mc.setChecked(p['mc'])
            except Exception as e: self.error(e)

    def run_analysis(self):
        try:
            c = self.config()
            if self.raw.empty: raise ValueError('Import data before running an analysis.')
            self.run_button.setEnabled(False); self.cancel.setEnabled(True); self.progress.setValue(0)
            for button in self.action_buttons: button.setEnabled(False)
            self.worker = Worker(self.raw.copy(), self.module.currentText(), self.mode.currentText(), self.weighting.currentText(), c, self.mc.isChecked())
            self.worker.completed.connect(self.finished); self.worker.failed.connect(self.failed)
            self.worker.progress.connect(self.progress.setValue)
            self.worker.finished.connect(self.reset_busy)
            self.worker.start(); self.statusBar().showMessage('Running analysis… Monte Carlo simulation can be canceled.')
        except Exception as e:
            self.reset_busy(); self.error(e)

    def reset_busy(self):
        self.run_button.setEnabled(True); self.cancel.setEnabled(False)
        for button in self.action_buttons: button.setEnabled(True)

    def failed(self, text): self.error(text); self.statusBar().showMessage('Analysis did not complete; previous results are unchanged.')

    def finished(self, result):
        self.analysis = result; self.show_table(self.results, result.results); self.show_table(self.weights, result.weights)
        if result.draws: self.show_table(self.sensitivity, result.draws['sensitivity'])
        else: self.show_table(self.sensitivity, pd.DataFrame())
        self.plot_group.clear(); self.plot_group.addItems(result.results['group'].unique().tolist())
        self.refresh_plot(); self.progress.setValue(100)
        self.tabs.setCurrentWidget(self.results); self.statusBar().showMessage('Analysis complete · Results are ranked separately by group and mode.')

    def refresh_plot(self, *_):
        if not hasattr(self, 'canvas'): return
        result = self.analysis.results if self.analysis else pd.DataFrame({'Priority': []})
        fig = make_figure(result, self.chart.currentText(), self.plot_group.currentText() or None, self.plot_mode.currentText())
        self.plot_layout.removeWidget(self.toolbar); self.toolbar.hide(); self.toolbar.deleteLater()
        self.plot_layout.removeWidget(self.canvas); self.canvas.hide(); self.canvas.deleteLater()
        self.canvas = FigureCanvasQTAgg(fig); self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.plot_layout.addWidget(self.toolbar); self.plot_layout.addWidget(self.canvas); self.canvas.draw_idle()

    def export_plot(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save figure', 'MCRank.png', 'PNG (*.png);;PDF (*.pdf);;SVG (*.svg)')
        if path:
            try: self.canvas.figure.savefig(path, dpi=300)
            except Exception as e: self.error(e)

    def export_all(self):
        if self.analysis is None: self.error('Run an analysis first.'); return
        folder = QFileDialog.getExistingDirectory(self, 'Select export folder (an empty folder is recommended)')
        if folder:
            try:
                export_results(self.analysis, folder); self.statusBar().showMessage(f'Exported to {folder}')
            except Exception as e: self.error(e)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption(); event.ignore(); self.statusBar().showMessage('Stopping analysis. Please wait before closing the window.')
        else: event.accept()


from .appearance import setup_app


def main():
    app = QApplication(sys.argv); setup_app(app)
    window = MainWindow(); window.show(); sys.exit(app.exec())
