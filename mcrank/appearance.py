"""English desktop presentation with a restrained neutral palette."""
import json
import pandas as pd
from PySide6.QtCore import Qt, QLocale, QSize
from PySide6.QtGui import QFont, QFontDatabase, QIcon, QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import (QApplication, QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox, QTabWidget, QPlainTextEdit,
    QProgressBar, QFormLayout, QListWidget, QListWidgetItem, QScrollArea)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from .config import defaults
from .plots import make_figure, KINDS

PAGES = [
    ('Data preview', 'Inspect your imported chemical data before analysis.'),
    ('Data validation', 'Review missing values, units, and data quality checks.'),
    ('Ranking & evidence', 'Explore priority rankings and the evidence supporting them.'),
    ('Weights & dependencies', 'Review indicator weights and dependency controls.'),
    ('Visualization', 'Explore results and export publication-ready figures.'),
    ('Sensitivity', 'Inspect how uncertain inputs affect priority scores.'),
]

STYLE = """
QWidget { font-family: 'Segoe UI', 'Microsoft YaHei'; font-size: 13px; color: #24282D; }
QMainWindow, QWidget#Workspace { background: #F4F5F8; }
QFrame#Sidebar { background: #FFFFFF; border-right: 1px solid #E5E7EB; }
QWidget#Settings { background: #FFFFFF; }
QFrame#Card { background: #FFFFFF; border: 1px solid #E6E8ED; border-radius: 12px; }
QLabel { background: transparent; }
QLabel#Brand { font-size: 25px; font-weight: 700; color: #202428; }
QLabel#PageTitle { font-size: 27px; font-weight: 600; }
QLabel#SectionTitle { font-size: 15px; font-weight: 600; }
QLabel#Muted { color: #6C737E; font-size: 12px; }
QLabel#Eyebrow { color: #7C8490; font-size: 10px; font-weight: 600; }
QLabel#Badge { background: #ECEEF2; color: #535B67; padding: 6px 12px; border-radius: 10px; font-size: 11px; }
QPushButton { background: #FFFFFF; border: 1px solid #DEE1E7; border-radius: 7px; padding: 8px 12px; min-height: 18px; }
QPushButton:hover { background: #F0F1F5; border-color: #C7CCD4; }
QPushButton:pressed { background: #E5E7EC; }
QPushButton:focus { border: 1px solid #626C7B; }
QPushButton:disabled { color: #A9AFB8; background: #F5F6F8; border-color: #ECEEF1; }
QPushButton#Primary { background: #484C5D; color: #FFFFFF; border: 1px solid #484C5D; font-weight: 600; padding: 10px 14px; }
QPushButton#Primary:hover { background: #363B4B; }
QPushButton#Primary:disabled { background: #9BA0AC; border-color: #9BA0AC; }
QComboBox, QSpinBox { background: #FAFBFC; border: 1px solid #DFE3E9; border-radius: 6px; padding: 7px 8px; min-height: 18px; }
QComboBox:focus, QSpinBox:focus { border-color: #7A8494; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url(__ASSETS__/down.svg); width: 12px; height: 12px; }
QSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 20px; border: none; }
QSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border: none; }
QSpinBox::up-arrow { image: url(__ASSETS__/up.svg); width: 10px; height: 10px; }
QSpinBox::down-arrow { image: url(__ASSETS__/down.svg); width: 10px; height: 10px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #E7E9EF; selection-color: #24282D; padding: 4px; }
QCheckBox { spacing: 9px; padding: 4px 0; }
QCheckBox::indicator { width: 16px; height: 16px; }
QListWidget#Navigation { border: none; background: transparent; outline: none; }
QListWidget#Navigation::item { padding: 12px 9px; margin: 2px 0; border-radius: 7px; color: #5C646F; }
QListWidget#Navigation::item:selected { background: #E9EBF0; color: #24282D; font-weight: 600; }
QListWidget#Navigation::item:hover:!selected { background: #F5F6F8; }
QTabWidget::pane { border: none; background: white; }
QTableView { background: #FFFFFF; alternate-background-color: #FAFBFC; border: none; selection-background-color: #E8EBF2; selection-color: #222830; gridline-color: #EFF0F3; }
QTableView::item { padding: 8px; border-bottom: 1px solid #F0F1F4; }
QHeaderView::section { background: #F7F8FA; color: #606977; padding: 10px 8px; border: none; border-bottom: 1px solid #E5E8EE; font-size: 11px; font-weight: 600; }
QTableCornerButton::section { background: #F7F8FA; border: none; }
QPlainTextEdit { background: #FAFBFC; border: 1px solid #E4E7EC; border-radius: 7px; padding: 10px; selection-background-color: #DDE2EC; }
QProgressBar { background: #ECEEF2; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }
QProgressBar::chunk { background: #687384; border-radius: 3px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #F6F7F9; width: 10px; margin: 0; }
QScrollBar:horizontal { background: #F6F7F9; height: 10px; margin: 0; }
QScrollBar::handle { background: #CDD2DB; border-radius: 4px; min-width: 24px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QStatusBar { background: #F4F5F8; color: #727B88; font-size: 11px; padding: 4px 12px; }
QStatusBar::item { border: none; }
QToolBar { background: white; border: none; spacing: 4px; }
QToolButton { border: none; border-radius: 4px; padding: 5px; }
QToolButton:hover { background: #ECEEF3; }
QToolTip { background: #303640; color: white; border: none; padding: 6px; }
"""


def label(text, name=None):
    item = QLabel(text)
    if name: item.setObjectName(name)
    return item


def line_icon(index):
    pixmap = QPixmap(20, 20); pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor('#656D7A'), 1.3))
    if index in (0, 1, 7):
        painter.drawRoundedRect(3, 3, 14, 14, 2, 2)
        for y in (7, 10, 13): painter.drawLine(6, y, 14, y)
    elif index in (2, 4, 5):
        painter.drawLine(3, 17, 17, 17)
        for x, y in ((5, 10), (10, 5), (15, 8)): painter.drawLine(x, 15, x, y)
    else:
        for y, x in ((5, 7), (10, 13), (15, 9)):
            painter.drawLine(3, y, 17, y); painter.drawEllipse(x-2, y-2, 4, 4)
    painter.end()
    return QIcon(pixmap)


def build_layout(w):
    w.setWindowTitle('MCRank | Chemical Risk Prioritization')
    w.resize(1480, 900); w.setMinimumSize(1180, 720)
    root = QWidget(); w.setCentralWidget(root)
    shell = QHBoxLayout(root); shell.setContentsMargins(0, 0, 0, 0); shell.setSpacing(0)
    sidebar = QFrame(); sidebar.setObjectName('Sidebar'); sidebar.setFixedWidth(238)
    side = QVBoxLayout(sidebar); side.setContentsMargins(18, 28, 18, 20); side.setSpacing(8)
    side.addWidget(label('MCRank', 'Brand'))
    side.addWidget(label('Chemical risk prioritization', 'Muted')); side.addSpacing(30)
    side.addWidget(label('WORKSPACE', 'Eyebrow'))
    w.navigation = QListWidget(); w.navigation.setObjectName('Navigation'); w.navigation.setIconSize(QSize(18, 18))
    w.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    for i, (title, _) in enumerate(PAGES):
        QListWidgetItem(line_icon(i), title, w.navigation)
    side.addWidget(w.navigation, 1)
    side.addWidget(label('MCRank  /  v1.0', 'Muted'))
    side.addWidget(label('English edition', 'Muted')); shell.addWidget(sidebar)
    workspace = QWidget(); workspace.setObjectName('Workspace'); shell.addWidget(workspace, 1)
    outer = QVBoxLayout(workspace); outer.setContentsMargins(26, 22, 26, 12); outer.setSpacing(20)
    top = QHBoxLayout(); top.addWidget(label('RESEARCH WORKSPACE', 'Eyebrow')); top.addStretch()
    top.addWidget(label('English', 'Badge')); outer.addLayout(top)
    heading = QVBoxLayout(); heading.setSpacing(5)
    w.page_title = label(PAGES[0][0], 'PageTitle'); heading.addWidget(w.page_title)
    w.page_description = label(PAGES[0][1], 'Muted'); w.page_description.setWordWrap(True); heading.addWidget(w.page_description)
    outer.addLayout(heading)
    actions = QHBoxLayout(); actions.setSpacing(8); w.action_buttons = []
    for text, fn in [('Import data', w.import_data), ('Load example', w.load_example), ('Input template', w.save_template),
                     ('Open project', w.open_project), ('Save project', w.save_project), ('Export results', w.export_all)]:
        button = QPushButton(text); button.clicked.connect(fn)
        if text == 'Import data': button.setObjectName('Primary')
        actions.addWidget(button); w.action_buttons.append(button)
    outer.addLayout(actions)
    body = QHBoxLayout(); body.setSpacing(18); outer.addLayout(body, 1)
    settings_card = QFrame(); settings_card.setObjectName('Card'); settings_card.setFixedWidth(260)
    settings_layout = QVBoxLayout(settings_card); settings_layout.setContentsMargins(4, 4, 4, 4); settings_layout.setSpacing(0)
    scroll = QScrollArea(); scroll.setWidgetResizable(True); settings_layout.addWidget(scroll)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    settings = QWidget(); settings.setObjectName('Settings'); scroll.setWidget(settings)
    form = QVBoxLayout(settings); form.setContentsMargins(18, 20, 18, 20); form.setSpacing(10)
    form.addWidget(label('Analysis setup', 'SectionTitle')); form.addSpacing(5)
    for attr, title, items in [('module', 'Analysis module', ['Eco', 'Human']), ('mode', 'Mode', ['Auto', 'Risk', 'Screening']),
                               ('weighting', 'Weighting', ['Equal', 'CRITIC', 'Custom'])]:
        form.addWidget(label(title, 'Muted')); control = QComboBox(); control.addItems(items)
        setattr(w, attr, control); form.addWidget(control)
    form.addSpacing(10); form.addWidget(label('Uncertainty', 'SectionTitle'))
    w.mc = QCheckBox('Monte Carlo simulation'); form.addWidget(w.mc)
    for attr, title, value, maximum in [('iterations', 'Iterations', 1000, 100000), ('seed', 'Random seed', 2026, 2147483647), ('topk', 'Top-K', 3, 100000)]:
        row = QHBoxLayout(); row.addWidget(label(title, 'Muted'))
        control = QSpinBox(); control.setRange(0 if attr == 'seed' else 1, maximum); control.setValue(value)
        control.setFixedWidth(112); setattr(w, attr, control); row.addWidget(control); form.addLayout(row)
    form.addStretch()
    footer = QVBoxLayout(); footer.setContentsMargins(14, 12, 14, 14); footer.setSpacing(10)
    settings_layout.addLayout(footer)
    w.run_button = QPushButton('Run analysis'); w.run_button.setObjectName('Primary'); w.run_button.clicked.connect(w.run_analysis); footer.addWidget(w.run_button)
    w.cancel = QPushButton('Cancel analysis'); w.cancel.setEnabled(False); w.cancel.clicked.connect(lambda: w.worker.requestInterruption() if w.worker else None); footer.addWidget(w.cancel)
    w.progress = QProgressBar(); w.progress.setTextVisible(False); w.progress.setRange(0, 100); w.progress.setValue(0); footer.addWidget(w.progress)
    note = label('Rerun the analysis after changing data or settings.', 'Muted'); note.setWordWrap(True); footer.addWidget(note)
    body.addWidget(settings_card)
    content = QFrame(); content.setObjectName('Card'); content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(14, 16, 14, 12); content_layout.setSpacing(12)
    content_header = QHBoxLayout(); w.content_title = label('Dataset', 'SectionTitle'); content_header.addWidget(w.content_title)
    content_header.addStretch(); w.record_count = label('No data loaded', 'Badge'); content_header.addWidget(w.record_count); content_layout.addLayout(content_header)
    w.tabs = QTabWidget(); w.tabs.tabBar().hide(); content_layout.addWidget(w.tabs, 1); body.addWidget(content, 1)
    w.preview = w.add_table('Data preview'); w.validation = w.add_table('Data validation')
    w.results = w.add_table('Ranking and evidence'); w.weights = w.add_table('Weights and dependencies')
    plot_page = QWidget(); w.plot_layout = QVBoxLayout(plot_page); w.plot_layout.setContentsMargins(0, 0, 0, 0)
    controls = QHBoxLayout(); w.plot_layout.addLayout(controls)
    w.chart = QComboBox(); w.chart.addItems(KINDS); w.chart.currentTextChanged.connect(w.refresh_plot); controls.addWidget(w.chart)
    w.plot_group = QComboBox(); w.plot_group.setToolTip('Result group'); w.plot_group.currentTextChanged.connect(w.refresh_plot); controls.addWidget(w.plot_group)
    w.plot_mode = QComboBox(); w.plot_mode.addItems(['Risk', 'Screening']); w.plot_mode.currentTextChanged.connect(w.refresh_plot); controls.addWidget(w.plot_mode)
    save = QPushButton('Export figure'); save.setToolTip('Save as PNG, PDF, or SVG'); save.clicked.connect(w.export_plot); controls.addWidget(save)
    w.canvas = FigureCanvasQTAgg(make_figure(pd.DataFrame({'Priority': []})))
    w.toolbar = NavigationToolbar2QT(w.canvas, w); w.plot_layout.addWidget(w.toolbar); w.plot_layout.addWidget(w.canvas)
    w.tabs.addTab(plot_page, 'Visualization'); w.sensitivity = w.add_table('Sensitivity')
    def sync(index):
        w.navigation.setCurrentRow(index)
        w.page_title.setText(PAGES[index][0]); w.page_description.setText(PAGES[index][1])
        w.content_title.setText(['Dataset', 'Validation report', 'Priority rankings', 'Indicator weights', 'Figures', 'Sensitivity results'][index])
    w.navigation.currentRowChanged.connect(w.tabs.setCurrentIndex); w.tabs.currentChanged.connect(sync); sync(0)
    w.statusBar().showMessage('Ready  ·  Import data or load an example to begin.')


def setup_app(app):
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app.setAttribute(Qt.AA_DontUseNativeDialogs, True)
    app.setStyle('Fusion')
    # Explicit font registration also supports offscreen validation on Windows.
    from pathlib import Path
    for filename in ('segoeui.ttf', 'seguisb.ttf', 'segoeuib.ttf', 'msyh.ttc'):
        path = Path('C:/Windows/Fonts') / filename
        if path.exists(): QFontDatabase.addApplicationFont(str(path))
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(STYLE.replace('__ASSETS__', (Path(__file__).parent / 'assets').as_posix()))
