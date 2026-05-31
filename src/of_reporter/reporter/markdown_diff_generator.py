from ..model import CaseData, FileInfo, FileCategory


class MarkdownDiffGenerator:

    CATEGORY_LABELS = {
        FileCategory.SYSTEM: "system/ 設定ファイル",
        FileCategory.CONSTANT: "constant/ 物性ファイル",
        FileCategory.ZERO: "0/ 境界条件",
        FileCategory.SCRIPT: "実行スクリプト",
    }

    def __init__(self, cases: list[CaseData]):
        self.cases = cases

    def generate(self) -> str:
        md = []
        md.append("# OpenFOAM ケース比較レポート")
        md.append("")
        md.append(f"> 生成日時: {self.cases[0].scanned_at if self.cases else ''}")
        md.append("")

        md.append("## 比較ケース一覧")
        md.append("")
        md.append("| # | ケース名 | パス |")
        md.append("|---|----------|------|")
        for i, c in enumerate(self.cases, 1):
            md.append(f"| {i} | {c.name} | `{c.path}` |")
        md.append("")

        all_file_paths = set()
        for c in self.cases:
            for f in c.files:
                all_file_paths.add(f.rel_path)

        categories = [FileCategory.SYSTEM, FileCategory.CONSTANT, FileCategory.ZERO, FileCategory.SCRIPT]

        for cat in categories:
            cat_paths = sorted(
                p for p in all_file_paths
                if any(f.rel_path == p and f.category == cat for c in self.cases for f in c.files)
            )
            if not cat_paths:
                continue

            md.append("---")
            md.append("")
            md.append(f"## {self.CATEGORY_LABELS.get(cat, cat.value)}")
            md.append("")

            for rel_path in cat_paths:
                md.append(f"### {rel_path}")
                md.append("")

                parsed_list = []
                for c in self.cases:
                    pf = c.parsed.get(rel_path)
                    parsed_list.append(pf)

                if all(pf is None for pf in parsed_list):
                    md.append("> ※ 全ケースでパース未実行")
                    md.append("")
                    continue

                if any(pf is not None and pf.is_boundary_field for pf in parsed_list):
                    self._append_bc_diff(md, parsed_list, case_names=[c.name for c in self.cases], rel_path=rel_path)
                else:
                    raw_list = []
                    for pf in parsed_list:
                        raw_list.append(pf.raw if pf is not None else {})
                    self._append_dict_diff(md, raw_list, case_names=[c.name for c in self.cases])

                md.append("")

        md.append("---")
        md.append("")
        md.append(f"*本レポートは OFFileReporter により自動生成されました*")
        md.append("")

        return "\n".join(md)

    def _collect_keys(self, data_list: list[dict]) -> list[str]:
        keys = set()
        for d in data_list:
            for k, v in d.items():
                if k != "FoamFile":
                    keys.add(k)
        return sorted(keys)

    def _is_value_equal(self, values: list) -> bool:
        if not values:
            return True
        first = self._val_str(values[0])
        return all(self._val_str(v) == first for v in values)

    def _val_str(self, v) -> str:
        if v is None:
            return "-"
        if isinstance(v, list):
            return " ".join(str(x) for x in v)
        return str(v)

    def _append_dict_diff(self, md: list, raw_list: list[dict], case_names: list[str]):
        keys = self._collect_keys(raw_list)
        if not keys:
            md.append("> ※ パース結果なし")
            return

        md.append("| キー |")
        for cn in case_names:
            md[-1] += f" {cn} |"
        md.append("|------|")
        for _ in case_names:
            md[-1] += "------|"

        for key in keys:
            values = []
            for raw in raw_list:
                v = raw.get(key)
                values.append(v)
            row = f"| {key} |"
            vals_str = [self._val_str(v) for v in values]

            if not self._is_value_equal(values):
                for vs in vals_str:
                    row += f" **{vs}** |"
            else:
                for vs in vals_str:
                    row += f" {vs} |"
            md.append(row)

            sub_dicts = [v for v in values if isinstance(v, dict)]
            if sub_dicts and len(sub_dicts) == len(values):
                md.append("")
                self._append_dict_diff(md, sub_dicts, case_names)

    def _append_bc_diff(self, md: list, parsed_list: list, case_names: list[str], rel_path: str):
        bc_list = []
        for pf in parsed_list:
            if pf is not None and pf.bc_data:
                bc_list.append(pf.bc_data)
            else:
                bc_list.append({})

        dims = [bc.get("dimensions", "-") for bc in bc_list]
        if not self._is_value_equal(dims):
            md.append("| 次元 |")
            for cn in case_names:
                md[-1] += f" {cn} |"
            md.append("|------|" + "|------|" * len(case_names))
            md.append("| dimensions |")
            for d in dims:
                md[-1] += f" **{d}** |"
            md.append("")
        elif dims[0] != "-":
            md.append(f"- **次元**: {dims[0]}")
            md.append("")

        internals = [bc.get("internalField", "-") for bc in bc_list]
        if not self._is_value_equal(internals):
            md.append("| 内部フィールド |")
            for cn in case_names:
                md[-1] += f" {cn} |"
            md.append("|--------------|" + "|------|" * len(case_names))
            md.append("| internalField |")
            for it in internals:
                md[-1] += f" **{it}** |"
            md.append("")
        elif internals[0] != "-":
            md.append(f"- **内部フィールド**: `{internals[0]}`")
            md.append("")

        all_patches = set()
        for bc in bc_list:
            all_patches.update(bc.get("patches", {}).keys())

        if all_patches:
            patch_keys = set()
            for bc in bc_list:
                for pn, pd in bc.get("patches", {}).items():
                    patch_keys.update(pd.keys())
            patch_keys.discard("type")
            sorted_pkeys = sorted(patch_keys)

            for patch_name in sorted(all_patches):
                md.append(f"**{patch_name}**")
                md.append("")
                md.append("| 項目 |")
                for cn in case_names:
                    md[-1] += f" {cn} |"
                md.append("|------|" + "|------|" * len(case_names))

                md.append(f"| type |")
                for bc in bc_list:
                    pd = bc.get("patches", {}).get(patch_name, {})
                    md[-1] += f" {pd.get('type', '-')} |"

                for pk in sorted_pkeys:
                    vals = [bc.get("patches", {}).get(patch_name, {}).get(pk, "-") for bc in bc_list]
                    if self._is_value_equal(vals):
                        continue
                    row = f"| {pk} |"
                    for v in vals:
                        row += f" **{v}** |"
                    md.append(row)
                md.append("")
