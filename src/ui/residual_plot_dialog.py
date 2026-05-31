from __future__ import annotations

import os
import re
from pathlib import Path

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QLogValueAxis, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from src.wsl_manager import clean_output, run_wsl_command, win_to_wsl_path

_EXCLUDE_SERIES = {
    "executionTime", "epsAvg", "epsMin", "epsMax",
    "contLocal", "clockTime", "contGlobal", "contCumulative",
    "Separator", "Time",
}
_EXCLUDE_SUFFIXES = ("Iters", "FinalRes")


_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    "#bcbd22", "#17becf",
]


def _parse_residual_file(filepath: str) -> tuple[list[float], list[float]]:
    iterations: list[float] = []
    values: list[float] = []
    skipped = 0
    with open(filepath, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//") or line.startswith(";"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                it = float(parts[0].rstrip("sS"))
                val = float(parts[-1])
            except ValueError:
                skipped += 1
                continue
            if val <= 0:
                skipped += 1
                continue
            iterations.append(it)
            values.append(val)
    import sys
    if skipped:
        print(f"[ResidualPlot] {os.path.basename(filepath)}: {len(iterations)} points, {skipped} skipped", file=sys.stderr)
    return iterations, values


class ResidualPlotDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("残差グラフ")
        self.setMinimumSize(800, 600)
        self._case_dir: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("OpenFOAM log ファイル:"))
        self._file_edit = QLineEdit()
        self._file_edit.setPlaceholderText("OpenFOAM ケース内の log ファイルを選択...")
        file_layout.addWidget(self._file_edit)
        browse_btn = QPushButton("参照...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        btn_layout = QHBoxLayout()
        self._generate_btn = QPushButton("グラフ生成")
        self._generate_btn.clicked.connect(self._generate)
        btn_layout.addWidget(self._generate_btn)

        self._status_label = QLabel("")
        btn_layout.addWidget(self._status_label, 1)
        layout.addLayout(btn_layout)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._chart = QChart()
        self._chart.setTitle("残差履歴 (Residual History)")
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().setAlignment(Qt.AlignRight)

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self._chart_view, 1)

    def _browse_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "OpenFOAM log ファイルを選択",
            "", "ログファイル (log);;すべてのファイル (*)",
        )
        if file_path:
            self._file_edit.setText(file_path)

    def _generate(self) -> None:
        log_path = self._file_edit.text().strip().strip("\"'")
        if not log_path or not os.path.isfile(log_path):
            QMessageBox.warning(self, "エラー", "有効なlogファイルを選択してください。")
            return

        case_dir = os.path.dirname(os.path.abspath(log_path))
        log_name = os.path.basename(log_path)
        self._case_dir = case_dir
        wsl_path = win_to_wsl_path(case_dir)

        self._generate_btn.setEnabled(False)
        self._progress.show()
        self._status_label.setText("foamLog 実行中...")

        rc, stdout, stderr = run_wsl_command(
            wsl_path=wsl_path,
            command=f"foamLog {log_name}",
        )

        if rc != 0:
            self._generate_btn.setEnabled(True)
            self._progress.hide()
            msg = clean_output(stderr or stdout or f"foamLog 終了コード: {rc}")
            QMessageBox.warning(
                self, "foamLog エラー",
                f"foamLog の実行に失敗しました。\n"
                f"OpenFOAM環境が正しく設定されているか確認してください。\n\n{msg[:500]}",
            )
            self._status_label.setText("foamLog 失敗")
            return

        logs_dir = os.path.join(case_dir, "logs")
        if not os.path.isdir(logs_dir):
            self._generate_btn.setEnabled(True)
            self._progress.hide()
            QMessageBox.warning(
                self, "エラー",
                "logs/ ディレクトリが見つかりません。foamLog がファイルを生成しなかった可能性があります。",
            )
            self._status_label.setText("logs/ が見つかりません")
            return

        residual_files = sorted(Path(logs_dir).glob("*_0"))
        if not residual_files:
            self._generate_btn.setEnabled(True)
            self._progress.hide()
            QMessageBox.information(
                self, "情報",
                "logs/ 内に *_0 ファイルが見つかりませんでした。",
            )
            self._status_label.setText("残差ファイルなし")
            return

        import sys
        print(f"[ResidualPlot] {len(residual_files)} files in logs/: {[f.name for f in residual_files]}", file=sys.stderr)
        self._status_label.setText(f"logs/ から {len(residual_files)} ファイル読み込み中...")

        self._chart.removeAllSeries()
        for ax in self._chart.axes():
            self._chart.removeAxis(ax)

        x_axis = QValueAxis()
        x_axis.setTitleText("反復数")
        x_axis.setLabelFormat("%.2e")
        self._chart.addAxis(x_axis, Qt.AlignBottom)

        y_axis = QLogValueAxis()
        y_axis.setTitleText("残差")
        y_axis.setLabelFormat("%e")
        y_axis.setBase(10.0)
        self._chart.addAxis(y_axis, Qt.AlignLeft)

        global_min = float("inf")
        global_max = float("-inf")
        parsed: list[tuple[str, list[float], list[float]]] = []

        for i, rf in enumerate(residual_files):
            stem = rf.stem
            series_name = stem[:-2] if stem.endswith("_0") else stem
            if series_name in _EXCLUDE_SERIES or series_name.endswith(_EXCLUDE_SUFFIXES):
                continue
            iterations, values = _parse_residual_file(str(rf))
            if not iterations:
                continue
            parsed.append((series_name, iterations, values))
            if values:
                global_min = min(global_min, min(values))
                global_max = max(global_max, max(values))

        if not parsed:
            self._chart.setTitle("残差履歴 (データなし)")
            self._generate_btn.setEnabled(True)
            self._progress.hide()
            self._status_label.setText("パース可能な残差データがありませんでした")
            return

        for i, (name, iters, vals) in enumerate(parsed):
            series = QLineSeries()
            series.setName(name)
            color = QColor(_COLORS[i % len(_COLORS)])
            series.setColor(color)
            series.setPen(QPen(color, 1.5))
            for x, y in zip(iters, vals):
                series.append(x, y)
            self._chart.addSeries(series)
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)

        if global_min == float("inf"):
            global_min = 1e-10
        if global_max == float("-inf"):
            global_max = 1.0

        y_lower = max(1e-10, global_min * 0.5)
        y_upper = max(global_max * 2.0, 1.0)

        x_min = min(s[1][0] for s in parsed)
        x_max = max(s[1][-1] for s in parsed)

        x_axis.setRange(x_min, x_max)
        y_axis.setRange(y_lower, y_upper)

        self._chart.setTitle("残差履歴 (Residual History)")
        self._chart_view.update()

        total_points = sum(len(v) for _, _, v in parsed)
        self._generate_btn.setEnabled(True)
        self._progress.hide()
        self._status_label.setText(f"完了: {len(parsed)} 系列 / {total_points} 点をプロット")
