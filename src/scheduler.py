from __future__ import annotations

import time
from collections import deque
from threading import Lock, Thread

from PySide6.QtCore import QObject, Signal

from src.models import Job, JobStatus
from src.wsl_manager import run_wsl_command


class SchedulerSignals(QObject):
    job_status_changed = Signal(str, JobStatus)
    job_log_updated = Signal(str, str)
    job_started = Signal(str)
    job_completed = Signal(str, JobStatus)


class JobScheduler:
    def __init__(self, max_concurrent: int = 2) -> None:
        self._max_concurrent = max_concurrent
        self._jobs: dict[str, Job] = {}
        self._queue: deque[str] = deque()
        self._lock = Lock()
        self._running = False
        self._thread: Thread | None = None
        self.signals = SchedulerSignals()

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        with self._lock:
            self._max_concurrent = max(1, value)

    @property
    def jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def add_job(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job
            self._queue.append(job.id)

    def remove_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                if job_id in self._queue:
                    self._queue.remove(job_id)
                return True
            return False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            with self._lock:
                running_count = sum(
                    1 for j in self._jobs.values() if j.status == JobStatus.RUNNING
                )
                available = self._max_concurrent - running_count
                next_ids: list[str] = []
                while available > 0 and self._queue:
                    candidate = self._queue.popleft()
                    if candidate in self._jobs and self._jobs[candidate].status == JobStatus.WAITING:
                        next_ids.append(candidate)
                        available -= 1

            for job_id in next_ids:
                thread = Thread(target=self._execute_job, args=(job_id,), daemon=True)
                thread.start()

            time.sleep(0.5)

    def _execute_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = JobStatus.RUNNING
            job.started_at = __import__("datetime").datetime.now()

        self.signals.job_status_changed.emit(job_id, JobStatus.RUNNING)
        self.signals.job_started.emit(job_id)

        combined_log: list[str] = []
        returncode = 0

        for cmd in job.commands:
            rc, stdout, stderr = run_wsl_command(
                wsl_path=job.wsl_path,
                command=cmd,
                on_stdout=lambda line: self._on_job_output(job_id, line),
                on_stderr=lambda line: self._on_job_output(job_id, line),
            )
            combined_log.append(f"$ {cmd}\n")
            if stdout:
                combined_log.append(stdout)
            if stderr:
                combined_log.append(stderr)
            returncode = rc
            if rc != 0:
                break

        final_status = JobStatus.COMPLETED if returncode == 0 else JobStatus.FAILED

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = final_status
            job.completed_at = __import__("datetime").datetime.now()
            job.log = "".join(combined_log)

        self.signals.job_status_changed.emit(job_id, final_status)
        self.signals.job_log_updated.emit(job_id, job.log)
        self.signals.job_completed.emit(job_id, final_status)

    def _on_job_output(self, job_id: str, line: str) -> None:
        cleaned = line.replace("\x00", "")
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.log += cleaned
        self.signals.job_log_updated.emit(job_id, cleaned)
