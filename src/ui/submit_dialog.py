from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.models import Job
from src.wsl_manager import win_to_wsl_path


class SubmitDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新規ジョブ")
        self.setMinimumWidth(550)
        self._job: Job | None = None
        self._commands: list[str] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._dir_edit = QLineEdit()
        self._dir_edit.setPlaceholderText("OpenFOAMケースフォルダを選択...")
        browse_btn = QPushButton("参照...")
        browse_btn.clicked.connect(self._browse_folder)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self._dir_edit)
        dir_layout.addWidget(browse_btn)
        form.addRow("作業フォルダ:", dir_layout)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("自動: フォルダ名")
        form.addRow("ジョブ名:", self._name_edit)

        layout.addLayout(form)

        cmd_label_layout = QHBoxLayout()
        cmd_label_layout.addWidget(QLabel("実行コマンド:"))
        layout.addLayout(cmd_label_layout)

        self._cmd_list = QListWidget()
        layout.addWidget(self._cmd_list)

        btn_layout = QHBoxLayout()
        add_cmd_btn = QPushButton("+ 追加")
        add_cmd_btn.clicked.connect(self._add_command)
        remove_cmd_btn = QPushButton("- 削除")
        remove_cmd_btn.clicked.connect(self._remove_command)
        btn_layout.addWidget(add_cmd_btn)
        btn_layout.addWidget(remove_cmd_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        presets = QHBoxLayout()
        for label, cmds in [
            ("blockMesh + simpleFoam", ["blockMesh", "simpleFoam"]),
            ("simpleFoam", ["simpleFoam"]),
            ("blockMesh", ["blockMesh"]),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, c=cmds: self._set_preset(c))
            presets.addWidget(btn)
        layout.addLayout(presets)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "OpenFOAMケースフォルダを選択")
        if folder:
            self._dir_edit.setText(folder)
            if not self._name_edit.text():
                self._name_edit.setText(os.path.basename(folder))

    def _add_command(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        cmd, ok = QInputDialog.getText(self, "コマンド追加", "コマンド:")
        if ok and cmd.strip():
            self._cmd_list.addItem(cmd.strip())
            self._commands.append(cmd.strip())

    def _remove_command(self) -> None:
        row = self._cmd_list.currentRow()
        if row >= 0:
            self._cmd_list.takeItem(row)
            self._commands.pop(row)

    def _set_preset(self, cmds: list[str]) -> None:
        self._cmd_list.clear()
        self._commands = list(cmds)
        for c in cmds:
            self._cmd_list.addItem(c)

    def _accept(self) -> None:
        folder = self._dir_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "エラー", "有効なフォルダを選択してください。")
            return
        if not self._commands:
            QMessageBox.warning(self, "エラー", "少なくとも1つのコマンドを追加してください。")
            return

        name = self._name_edit.text().strip() or os.path.basename(folder)
        wsl_path = win_to_wsl_path(folder)

        self._job = Job(
            name=name,
            working_dir_win=folder,
            wsl_path=wsl_path,
            commands=list(self._commands),
        )
        self.accept()

    def get_job(self) -> Job | None:
        return self._job


from PySide6.QtWidgets import QLabel
