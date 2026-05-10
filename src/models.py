from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum, auto


class JobStatus(Enum):
    WAITING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

    @property
    def display_name(self) -> str:
        return {
            JobStatus.WAITING: "待機中",
            JobStatus.RUNNING: "実行中",
            JobStatus.COMPLETED: "完了",
            JobStatus.FAILED: "失敗",
            JobStatus.CANCELLED: "キャンセル",
        }[self]

    @property
    def color(self) -> str:
        return {
            JobStatus.WAITING: "#2196F3",
            JobStatus.RUNNING: "#4CAF50",
            JobStatus.COMPLETED: "#9E9E9E",
            JobStatus.FAILED: "#F44336",
            JobStatus.CANCELLED: "#FF9800",
        }[self]


class Job:
    def __init__(
        self,
        name: str,
        working_dir_win: str,
        wsl_path: str,
        commands: list[str],
    ) -> None:
        self.id: str = uuid.uuid4().hex[:12]
        self.name: str = name
        self.working_dir_win: str = working_dir_win
        self.wsl_path: str = wsl_path
        self.commands: list[str] = commands
        self.status: JobStatus = JobStatus.WAITING
        self.created_at: datetime = datetime.now()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.log: str = ""
