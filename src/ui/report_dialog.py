from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from src.models import Job
from src.of_reporter.model import CaseData, FileCategory
from src.of_reporter.scanner import FileScanner
from src.of_reporter.parser import OFDictParser, BCFieldParser
from src.of_reporter.reporter import MarkdownGenerator


class ReportDialog(QDialog):
    def __init__(self, job: Job, parent=None) -> None:
        super().__init__(parent)
        self._job = job
        self._markdown_text = ""
        self._setup_ui()
        self._generate_report()

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"ケースレポート - {self._job.name}")
        self.resize(900, 650)

        layout = QVBoxLayout(self)

        self._status_label = QLabel("準備中...")
        layout.addWidget(self._status_label)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        layout.addWidget(self._browser)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._save_btn = QPushButton("名前を付けて保存")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_report)
        btn_layout.addWidget(self._save_btn)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _generate_report(self) -> None:
        case_path = self._job.working_dir_win
        if not case_path or not os.path.isdir(case_path):
            QMessageBox.warning(self, "エラー", "ジョブのケースディレクトリが見つかりません。")
            self._status_label.setText("エラー: ディレクトリが見つかりません")
            return

        self._status_label.setText("スキャン中...")

        case_data = FileScanner.scan(case_path)
        if not case_data.files:
            QMessageBox.information(
                self, "情報",
                "OpenFOAMケースファイルが見つかりませんでした。\n"
                "有効なケースディレクトリを選択してください。"
            )
            self._status_label.setText("ファイルが見つかりません")
            return

        self._status_label.setText(f"パース中... ({len(case_data.files)} ファイル)")

        for finfo in case_data.files:
            full_path = os.path.join(case_data.path, finfo.rel_path)
            if not os.path.isfile(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except Exception:
                continue

            is_bc = finfo.category == FileCategory.ZERO
            if is_bc:
                bc_data = BCFieldParser.parse(text)
                if bc_data is not None:
                    raw = OFDictParser.parse(text)
                    from src.of_reporter.model import ParsedFile
                    pf = ParsedFile(
                        rel_path=finfo.rel_path,
                        category=finfo.category,
                        file_name=finfo.file_name,
                        raw=raw,
                        is_boundary_field=True,
                        bc_data=bc_data,
                    )
                    case_data.parsed[finfo.rel_path] = pf
                    continue

            raw = OFDictParser.parse(text)
            from src.of_reporter.model import ParsedFile
            pf = ParsedFile(
                rel_path=finfo.rel_path,
                category=finfo.category,
                file_name=finfo.file_name,
                raw=raw,
            )
            case_data.parsed[finfo.rel_path] = pf

        self._status_label.setText("レポート生成中...")

        gen = MarkdownGenerator(case_data)
        self._markdown_text = gen.generate()

        self._browser.setMarkdown(self._markdown_text)
        self._save_btn.setEnabled(True)

        self._status_label.setText(
            f"完了: {case_data.name} ({len(case_data.files)} ファイル, "
            f"{len(case_data.parsed)} パース済)"
        )

    def _save_report(self) -> None:
        if not self._markdown_text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "レポートを保存",
            f"{self._job.name}_report.md",
            "Markdown Files (*.md);;All Files (*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._markdown_text)
                self._save_btn.setText("保存完了 ✓")
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"保存に失敗しました:\n{e}")
