from __future__ import annotations

import os
import re
import subprocess
from typing import Callable


def _sanitize(text: str) -> str:
    return text.replace("\x00", "").replace("\r", "").replace("\n", "").strip()


def detect_wsl_distro() -> str:
    try:
        result = subprocess.run(
            ["wsl.exe", "-l", "-q"],
            capture_output=True,
            timeout=10,
        )
        raw = result.stdout.decode("utf-8", errors="replace")
        distros = [
            _sanitize(d) for d in raw.splitlines()
            if _sanitize(d)
        ]
        for name in distros:
            lower = name.lower()
            if "docker" in lower:
                continue
            if "ubuntu" in lower or "default" in lower:
                return name
        if distros:
            return distros[0]
    except Exception:
        pass
    return "Ubuntu"


_OF_BASHRC_CACHE: str | None = "__UNSET__"


def _find_openfoam_bashrc() -> str | None:
    global _OF_BASHRC_CACHE
    if _OF_BASHRC_CACHE != "__UNSET__":
        return _OF_BASHRC_CACHE if _OF_BASHRC_CACHE else None
    try:
        distro = detect_wsl_distro()
        result = subprocess.run(
            ["wsl.exe", "-d", distro, "--", "bash", "-c",
             "compgen -G '/opt/openfoam*/etc/bashrc' | tail -1"],
            capture_output=True, timeout=10,
        )
        path = result.stdout.decode("utf-8", errors="replace").strip()
        _OF_BASHRC_CACHE = path if path else ""
        return path if path else None
    except Exception:
        _OF_BASHRC_CACHE = ""
        return None


def win_to_wsl_path(win_path: str) -> str:
    if not win_path:
        return win_path
    abs_path = os.path.abspath(win_path)
    drive, rest = os.path.splitdrive(abs_path)
    if drive:
        drive_letter = drive[0].lower()
        rest = rest.replace("\\", "/")
        return f"/mnt/{drive_letter}{rest}"
    return abs_path.replace("\\", "/")


_ANSI_ESC_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_output(text: str) -> str:
    text = _ANSI_ESC_RE.sub("", text)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def run_wsl_command(
    wsl_path: str,
    command: str,
    distro: str | None = None,
    on_stdout: Callable[[str], None] | None = None,
    on_stderr: Callable[[str], None] | None = None,
) -> tuple[int, str, str]:
    if distro is None:
        distro = detect_wsl_distro()
    of_bashrc = _find_openfoam_bashrc()
    prefix = f"source {of_bashrc}; " if of_bashrc else ""
    full_cmd = [
        _sanitize("wsl.exe"),
        _sanitize("-d"),
        _sanitize(distro),
        _sanitize("--cd"),
        _sanitize(wsl_path),
        _sanitize("--"),
        _sanitize("bash"),
        _sanitize("-c"),
        _sanitize(f"{prefix}export LANG=C.UTF-8; {command}"),
    ]
    process = subprocess.Popen(
        full_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def read_stream(
        stream: subprocess.PIPE | None,
        lines: list[str],
        callback: Callable[[str], None] | None,
    ) -> None:
        if stream is None:
            return
        for raw_line in iter(stream.readline, b""):
            line = raw_line.decode("utf-8", errors="replace")
            line = clean_output(line)
            lines.append(line)
            if callback:
                callback(line)

    from threading import Thread

    t_out = Thread(target=read_stream, args=(process.stdout, stdout_lines, on_stdout))
    t_err = Thread(target=read_stream, args=(process.stderr, stderr_lines, on_stderr))
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()

    process.wait()
    return process.returncode, "".join(stdout_lines), "".join(stderr_lines)


def kill_wsl_process(distro: str, pid_in_wsl: int) -> bool:
    try:
        subprocess.run(
            [_sanitize("wsl.exe"), _sanitize("-d"), _sanitize(distro),
             _sanitize("--"), _sanitize("kill"), _sanitize(str(pid_in_wsl))],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False
