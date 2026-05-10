from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from src.models import Job, JobStatus


class JobListWidget(QTableWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["ID", "名前", "ステータス", "経過時間", "完了時間", "コマンド"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()

    def add_or_update_job(self, job: Job) -> None:
        row = self._find_row(job.id)
        if row < 0:
            row = self.rowCount()
            self.insertRow(row)

        self._set_item(row, 0, job.id)
        self._set_item(row, 1, job.name)
        self._set_status_item(row, 2, job)

        if job.status == JobStatus.WAITING:
            self._set_item(row, 3, "---")
            self._set_item(row, 4, "---")
        elif job.status == JobStatus.RUNNING and job.started_at:
            elapsed = datetime.now() - job.started_at
            self._set_item(row, 3, self._format_delta(elapsed))
            self._set_item(row, 4, "---")
        elif job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            if job.started_at and job.completed_at:
                elapsed = job.completed_at - job.started_at
                self._set_item(row, 3, self._format_delta(elapsed))
            if job.completed_at:
                self._set_item(row, 4, job.completed_at.strftime("%H:%M:%S"))
            else:
                self._set_item(row, 4, "---")

        self._set_item(row, 5, job.commands[0] + ("..." if len(job.commands) > 1 else ""))

    def remove_job_row(self, job_id: str) -> None:
        row = self._find_row(job_id)
        if row >= 0:
            self.removeRow(row)

    def _find_row(self, job_id: str) -> int:
        for r in range(self.rowCount()):
            item = self.item(r, 0)
            if item and item.text() == job_id:
                return r
        return -1

    def _set_item(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, col, item)

    def _set_status_item(self, row: int, col: int, job: Job) -> None:
        item = QTableWidgetItem(job.status.display_name)
        item.setTextAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        color = QColor(job.status.color)
        item.setForeground(color)
        self.setItem(row, col, item)

    @staticmethod
    def _format_delta(delta) -> str:
        total_sec = int(delta.total_seconds())
        h, rem = divmod(total_sec, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}h{m:02d}m{s:02d}s"
        elif m > 0:
            return f"{m}m{s:02d}s"
        return f"{s}s"
