from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class FileCategory(Enum):
    SYSTEM = "system"
    CONSTANT = "constant"
    ZERO = "0"
    SCRIPT = "script"


@dataclass
class FileInfo:
    rel_path: str
    category: FileCategory
    file_name: str


@dataclass
class ParsedFile:
    rel_path: str
    category: FileCategory
    file_name: str
    raw: dict
    is_boundary_field: bool = False
    bc_data: dict | None = None


@dataclass
class CaseData:
    name: str
    path: str
    files: list[FileInfo] = field(default_factory=list)
    parsed: dict[str, ParsedFile] = field(default_factory=dict)
    scanned_at: str = ""

    def __post_init__(self):
        if not self.scanned_at:
            self.scanned_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
