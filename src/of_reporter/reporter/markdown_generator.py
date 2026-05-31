from ..model import CaseData, FileInfo, FileCategory, ParsedFile
from ..parser import BCFieldParser


class MarkdownGenerator:

    CATEGORY_LABELS = {
        FileCategory.SYSTEM: "system/ 設定ファイル",
        FileCategory.CONSTANT: "constant/ 物性ファイル",
        FileCategory.ZERO: "0/ 境界条件",
        FileCategory.SCRIPT: "実行スクリプト",
    }

    def __init__(self, case_data: CaseData):
        self.case_data = case_data

    def generate(self) -> str:
        md = []
        md.append(f"# OpenFOAM ケースレポート: {self.case_data.name}")
        md.append("")
        md.append(f"> 生成日時: {self.case_data.scanned_at}")
        md.append("")
        md.append("## ケース情報")
        md.append("")
        md.append(f"- **ケース名**: {self.case_data.name}")
        md.append(f"- **パス**: `{self.case_data.path}`")
        md.append("")

        categories = [FileCategory.SYSTEM, FileCategory.CONSTANT, FileCategory.ZERO, FileCategory.SCRIPT]

        for cat in categories:
            files_in_cat = [f for f in self.case_data.files if f.category == cat]
            if not files_in_cat:
                continue

            md.append(f"---")
            md.append("")
            md.append(f"## {self.CATEGORY_LABELS.get(cat, cat.value)}")
            md.append("")

            for finfo in files_in_cat:
                pf = self.case_data.parsed.get(finfo.rel_path)
                md.append(f"### {finfo.rel_path}")
                md.append("")

                if pf is None:
                    md.append("> ※ パース未実行")
                    md.append("")
                    continue

                if pf.is_boundary_field and pf.bc_data:
                    self._append_bc_table(md, pf.bc_data)
                else:
                    self._append_dict_table(md, pf.raw, level=0)

                md.append("")

        md.append("---")
        md.append("")
        md.append(f"*本レポートは OFFileReporter により自動生成されました*")
        md.append("")

        return "\n".join(md)

    def _append_dict_table(self, md: list, data: dict, level: int = 0):
        rows = []
        sub_blocks = []

        for key, value in data.items():
            if key in ("FoamFile",):
                continue
            if isinstance(value, dict):
                sub_blocks.append((key, value))
            elif isinstance(value, list):
                rows.append([key, self._format_value(value)])
            else:
                rows.append([key, self._format_value(value)])

        if rows:
            if level == 0:
                md.append("| キー | 値 |")
                md.append("|------|-----|")
            else:
                md.append("| キー | 値 |")
                md.append("|------|-----|")
            for k, v in rows:
                md.append(f"| {k} | {v} |")

        for sub_key, sub_val in sub_blocks:
            md.append("")
            md.append(f"**{sub_key}**")
            md.append("")
            self._append_dict_table(md, sub_val, level + 1)

    def _format_value(self, value) -> str:
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, list):
                    parts.append(f"({' '.join(str(x) for x in item)})")
                else:
                    parts.append(str(item))
            return " ".join(parts)
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _append_bc_table(self, md: list, bc_data: dict):
        if "dimensions" in bc_data:
            md.append(f"- **次元**: {bc_data['dimensions']}")
        if "internalField" in bc_data:
            md.append(f"- **内部フィールド**: `{bc_data['internalField']}`")
        md.append("")

        patches = bc_data.get("patches", {})
        if patches:
            all_keys = set()
            for patch_data in patches.values():
                all_keys.update(patch_data.keys())
            all_keys.discard("type")
            sorted_keys = sorted(all_keys)
            header = "| パッチ | タイプ |"
            sep = "|--------|--------|"
            for k in sorted_keys:
                header += f" {k} |"
                sep += "--------|"
            md.append(header)
            md.append(sep)

            for patch_name, patch_data in patches.items():
                row = f"| {patch_name} | {patch_data.get('type', '-')} |"
                for k in sorted_keys:
                    val = patch_data.get(k, "-")
                    row += f" {val} |"
                md.append(row)
