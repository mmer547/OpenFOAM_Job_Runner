from .of_dict_parser import OFDictParser


class BCFieldParser:

    @staticmethod
    def parse(text: str) -> dict | None:
        raw = OFDictParser.parse(text)

        has_dimensions = "dimensions" in raw
        has_internal = "internalField" in raw
        has_boundary = "boundaryField" in raw

        if not (has_dimensions or has_internal or has_boundary):
            return None

        result = {}

        if "dimensions" in raw:
            dims = raw["dimensions"]
            if isinstance(dims, list):
                result["dimensions"] = f"[{' '.join(str(d) for d in dims)}]"
            else:
                result["dimensions"] = str(dims)

        if "internalField" in raw:
            val = raw["internalField"]
            if isinstance(val, list):
                result["internalField"] = " ".join(str(v) for v in val)
            else:
                result["internalField"] = str(val)

        if "boundaryField" in raw and isinstance(raw["boundaryField"], dict):
            patches = raw["boundaryField"]
            result["patches"] = {}
            for patch_name, patch_data in patches.items():
                if isinstance(patch_data, dict):
                    entry = {}
                    for k, v in patch_data.items():
                        if isinstance(v, list):
                            entry[k] = " ".join(str(x) for x in v)
                        else:
                            entry[k] = str(v)
                    result["patches"][patch_name] = entry

        return result
