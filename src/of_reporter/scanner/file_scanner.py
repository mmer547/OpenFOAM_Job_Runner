from pathlib import Path

from ..model import FileInfo, FileCategory, CaseData


EXCLUDE_DIRS = {"polyMesh", "polyMeshTri", "sets", "surfaces", "VTK", "postProcessing"}

ROOT_SCRIPT_SUFFIX = {"Allrun", "Allclean", "Allprep", "Allinit", "Allmesh", "Allserial", "Allparallel"}

EXCLUDED_ROOT_EXTENSIONS = {".xlsx", ".xls", ".txt", ".md", ".pdf", ".py", ".ipynb", ".bak", ".log", ".csv", ".dat"}
EXCLUDED_ROOT_FILES = {"README", "README.md", "readme.md", ".gitignore", ".gitattributes", "LICENSE", "LICENSE.txt"}


class FileScanner:

    @staticmethod
    def scan(case_dir: str | Path) -> CaseData:
        case_path = Path(case_dir).resolve()
        case_data = CaseData(
            name=case_path.name,
            path=str(case_path),
            files=[],
            parsed={},
        )

        if not case_path.is_dir():
            return case_data

        for entry in sorted(case_path.iterdir()):
            name = entry.name

            if name.startswith("."):
                continue

            if entry.is_dir():
                if name in EXCLUDE_DIRS:
                    continue

                if name == "system":
                    FileScanner._scan_dir(entry, FileCategory.SYSTEM, case_data)
                elif name == "constant":
                    FileScanner._scan_dir(entry, FileCategory.CONSTANT, case_data)
                elif name == "0" or name.startswith("0."):
                    FileScanner._scan_dir(entry, FileCategory.ZERO, case_data)
            else:
                FileScanner._collect_root_script(entry, case_data)

        return case_data

    @staticmethod
    def _scan_dir(dir_path: Path, category: FileCategory, case_data: CaseData):
        for entry in sorted(dir_path.rglob("*")):
            if not entry.is_file():
                continue
            parts = entry.relative_to(dir_path).parts
            if any(p in EXCLUDE_DIRS for p in parts):
                continue
            rel_path = str(entry.relative_to(dir_path.parent)).replace("\\", "/")
            case_data.files.append(
                FileInfo(rel_path=rel_path, category=category, file_name=entry.name)
            )

    @staticmethod
    def _collect_root_script(file_path: Path, case_data: CaseData):
        name = file_path.stem
        if name in ROOT_SCRIPT_SUFFIX:
            rel_path = file_path.name
            case_data.files.append(
                FileInfo(rel_path=rel_path, category=FileCategory.SCRIPT, file_name=file_path.name)
            )
            return

        if file_path.suffix.lower() in EXCLUDED_ROOT_EXTENSIONS:
            return
        if file_path.name in EXCLUDED_ROOT_FILES:
            return

        is_executable = False
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline()
                is_executable = file_path.name.startswith("All") or first_line.startswith("#!")
        except Exception:
            pass

        if is_executable:
            rel_path = file_path.name
            case_data.files.append(
                FileInfo(rel_path=str(rel_path), category=FileCategory.SCRIPT, file_name=file_path.name)
            )
