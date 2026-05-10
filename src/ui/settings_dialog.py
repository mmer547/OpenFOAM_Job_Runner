from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, current_max: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumWidth(350)
        self._max_concurrent = current_max
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel("同時実行ジョブ数")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        desc = QLabel(
            "WSLのリソース制限のため、同時に実行するジョブの最大数を制限できます。\n"
            "デフォルト: 2"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        slider_layout = QHBoxLayout()

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(1)
        self._slider.setMaximum(8)
        self._slider.setValue(self._max_concurrent)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(1)
        slider_layout.addWidget(self._slider)

        self._spin = QSpinBox()
        self._spin.setMinimum(1)
        self._spin.setMaximum(8)
        self._spin.setValue(self._max_concurrent)
        slider_layout.addWidget(self._spin)

        layout.addLayout(slider_layout)

        self._slider.valueChanged.connect(self._spin.setValue)
        self._spin.valueChanged.connect(self._slider.setValue)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_max_concurrent(self) -> int:
        return self._spin.value()
