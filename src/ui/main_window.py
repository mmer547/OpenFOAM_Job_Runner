from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.models import JobStatus
from src.scheduler import JobScheduler
from src.wsl_manager import clean_output
from src.ui.job_list_widget import JobListWidget
from src.ui.settings_dialog import SettingsDialog
from src.ui.submit_dialog import SubmitDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WSL OpenFOAM Job Runner")
        self.setMinimumSize(900, 600)

        self._scheduler = JobScheduler(max_concurrent=2)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_signals()
        self._setup_timer()

        self._scheduler.start()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        splitter = QSplitter()
        layout.addWidget(splitter)

        self._job_list = JobListWidget()
        splitter.addWidget(self._job_list)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlaceholderText("ジョブを選択するとログが表示されます")
        self._log_view.setMaximumBlockCount(10000)
        self._log_view.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace;")
        splitter.addWidget(self._log_view)

        splitter.setOrientation(Qt.Vertical)
        splitter.setSizes([300, 200])

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status_bar()

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("ファイル")
        file_menu.addAction("新規ジョブ", self._add_job)
        file_menu.addSeparator()
        file_menu.addAction("終了", self.close)

        job_menu = menubar.addMenu("ジョブ")
        job_menu.addAction("削除", self._remove_selected_job)

        settings_menu = menubar.addMenu("設定")
        settings_menu.addAction("同時実行数...", self._open_settings)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("メインツールバー")
        self.addToolBar(toolbar)

        add_btn = QToolButton()
        add_btn.setText("+ ジョブ追加")
        add_btn.clicked.connect(self._add_job)
        toolbar.addWidget(add_btn)

        remove_btn = QToolButton()
        remove_btn.setText("- 削除")
        remove_btn.clicked.connect(self._remove_selected_job)
        toolbar.addWidget(remove_btn)

        settings_btn = QToolButton()
        settings_btn.setText("設定")
        settings_btn.clicked.connect(self._open_settings)
        toolbar.addWidget(settings_btn)

    def _setup_signals(self) -> None:
        sig = self._scheduler.signals
        sig.job_status_changed.connect(self._on_status_changed)
        sig.job_log_updated.connect(self._on_log_updated)
        sig.job_started.connect(self._on_job_started)
        sig.job_completed.connect(self._on_job_completed)

        self._job_list.itemSelectionChanged.connect(self._on_selection_changed)

    def _setup_timer(self) -> None:
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh_elapsed)
        self._timer.start(1000)

    def _add_job(self) -> None:
        dialog = SubmitDialog(self)
        if dialog.exec() == SubmitDialog.Accepted:
            job = dialog.get_job()
            if job:
                self._scheduler.add_job(job)
                self._job_list.add_or_update_job(job)
                self._update_status_bar()

    def _remove_selected_job(self) -> None:
        row = self._job_list.currentRow()
        if row < 0:
            return
        item = self._job_list.item(row, 0)
        if item is None:
            return
        job_id = item.text()
        job = next((j for j in self._scheduler.jobs if j.id == job_id), None)
        if job and job.status == JobStatus.RUNNING:
            QMessageBox.warning(self, "エラー", "実行中のジョブは削除できません。")
            return
        self._scheduler.remove_job(job_id)
        self._job_list.remove_job_row(job_id)
        self._update_status_bar()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._scheduler.max_concurrent, self)
        if dialog.exec() == SettingsDialog.Accepted:
            self._scheduler.max_concurrent = dialog.get_max_concurrent()
            self._update_status_bar()

    def _on_status_changed(self, job_id: str, status: JobStatus) -> None:
        jobs = self._scheduler.jobs
        job = next((j for j in jobs if j.id == job_id), None)
        if job:
            self._job_list.add_or_update_job(job)
            self._update_status_bar()

    def _on_log_updated(self, job_id: str, line: str) -> None:
        selected_id = self._selected_job_id()
        if selected_id == job_id:
            self._log_view.appendPlainText(clean_output(line).rstrip("\n"))

    def _on_job_started(self, job_id: str) -> None:
        pass

    def _on_job_completed(self, job_id: str, status: JobStatus) -> None:
        jobs = self._scheduler.jobs
        job = next((j for j in jobs if j.id == job_id), None)
        if job:
            self._job_list.add_or_update_job(job)

    def _on_selection_changed(self) -> None:
        self._log_view.clear()
        job_id = self._selected_job_id()
        if job_id:
            jobs = self._scheduler.jobs
            job = next((j for j in jobs if j.id == job_id), None)
            if job and job.log:
                self._log_view.setPlainText(clean_output(job.log))

    def _refresh_elapsed(self) -> None:
        for job in self._scheduler.jobs:
            if job.status == JobStatus.RUNNING:
                self._job_list.add_or_update_job(job)

    def _selected_job_id(self) -> str | None:
        row = self._job_list.currentRow()
        if row < 0:
            return None
        item = self._job_list.item(row, 0)
        return item.text() if item else None

    def _update_status_bar(self) -> None:
        jobs = self._scheduler.jobs
        total = len(jobs)
        waiting = sum(1 for j in jobs if j.status == JobStatus.WAITING)
        running = sum(1 for j in jobs if j.status == JobStatus.RUNNING)
        completed = sum(1 for j in jobs if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED))
        self._status_bar.showMessage(
            f"合計: {total}  |  待機: {waiting}  |  実行中: {running}/{self._scheduler.max_concurrent}  |  完了/終了: {completed}"
        )
