import re


class OFDictParser:

    @staticmethod
    def parse(text: str) -> dict:
        lines = OFDictParser._preprocess(text)
        tokens = OFDictParser._tokenize(lines)
        parsed, _ = OFDictParser._parse_block(tokens, 0)
        return parsed

    @staticmethod
    def _preprocess(text: str) -> list[str]:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        lines = []
        for line in text.splitlines():
            line = re.sub(r"//.*$", "", line).strip()
            if line:
                lines.append(line)
        return lines

    @staticmethod
    def _tokenize(lines: list[str]) -> list[str]:
        tokens = []
        delimiters = "{}();[]"
        for line in lines:
            i = 0
            while i < len(line):
                c = line[i]
                if c in delimiters:
                    tokens.append(c)
                    i += 1
                elif c in '"\'': 
                    quote = c
                    j = i + 1
                    while j < len(line) and line[j] != quote:
                        if line[j] == '\\':
                            j += 1
                        j += 1
                    tokens.append(line[i:j + 1])
                    i = j + 1
                elif c.isspace():
                    i += 1
                else:
                    j = i
                    while j < len(line) and line[j] not in delimiters and not line[j].isspace():
                        j += 1
                    tokens.append(line[i:j])
                    i = j
        return tokens

    @staticmethod
    def _parse_block(tokens: list[str], start: int) -> tuple[dict, int]:
        result = {}
        i = start
        current_key = None

        while i < len(tokens):
            token = tokens[i]

            if token == "}":
                return result, i + 1

            if token == ";":
                current_key = None
                i += 1
                continue

            if token == "{":
                sub_dict, i = OFDictParser._parse_block(tokens, i + 1)
                if current_key is not None:
                    result[current_key] = sub_dict
                    current_key = None
                else:
                    result.update(sub_dict)
                continue

            if token == "(" and current_key is not None:
                content, end = OFDictParser._peek_paren_content(tokens, i)
                if content is not None and end < len(tokens) and tokens[end] != ";":
                    current_key = current_key + "(" + " ".join(content) + ")"
                    i = end
                    continue

            if token == "(":
                list_val, i = OFDictParser._parse_list(tokens, i + 1, delimiter=")")
                if current_key is not None:
                    result[current_key] = list_val
                    current_key = None
                continue

            if current_key is None:
                current_key = token
                i += 1
                continue

            key_to_set = current_key
            current_key = None
            value_tokens = [token]
            i += 1

            while i < len(tokens):
                t = tokens[i]
                if t == ";":
                    i += 1
                    break
                if t == "}":
                    break
                if t == "{":
                    sub_dict, i2 = OFDictParser._parse_block(tokens, i + 1)
                    value_tokens.append(sub_dict)
                    i = i2
                    continue
                if t == "(":
                    sub_list, i2 = OFDictParser._parse_list(tokens, i + 1, delimiter=")")
                    value_tokens.append(sub_list)
                    i = i2
                    continue
                value_tokens.append(t)
                i += 1

            result[key_to_set] = OFDictParser._join_value_tokens(value_tokens)

        return result, i

    @staticmethod
    def _peek_paren_content(tokens: list[str], start: int) -> tuple[list[str] | None, int]:
        if start >= len(tokens) or tokens[start] != "(":
            return None, start
        depth = 1
        j = start + 1
        content = []
        while j < len(tokens) and depth > 0:
            t = tokens[j]
            if t == "(":
                depth += 1
                content.append(t)
            elif t == ")":
                depth -= 1
                if depth == 0:
                    return content, j + 1
                content.append(t)
            else:
                content.append(t)
            j += 1
        return None, start

    @staticmethod
    def _join_value_tokens(tokens: list):
        if not tokens:
            return True
        result = []
        for t in tokens:
            if isinstance(t, (dict, list)):
                result.append(str(t))
            else:
                result.append(t)
        if len(result) == 1:
            return OFDictParser._parse_value(result[0])
        if result[0] == "[" and result[-1] == "]":
            return " ".join(result)
        return " ".join(result)

    @staticmethod
    def _parse_list(tokens: list[str], start: int, delimiter: str = ")") -> tuple[list, int]:
        values = []
        i = start
        while i < len(tokens):
            token = tokens[i]
            if token == delimiter:
                return values, i + 1
            if token == "(":
                sub_list, i = OFDictParser._parse_list(tokens, i + 1, delimiter=")")
                values.append(sub_list)
                continue
            if token == "{":
                sub_dict, i = OFDictParser._parse_block(tokens, i + 1)
                values.append(sub_dict)
                continue
            values.append(OFDictParser._parse_value(token))
            i += 1
        return values, i

    @staticmethod
    def _parse_value(token: str):
        if (token.startswith('"') and token.endswith('"')) or \
           (token.startswith("'") and token.endswith("'")):
            return token[1:-1]
        if token.lower() == "true":
            return True
        if token.lower() == "false":
            return False
        if token.lower() == "off":
            return "off"
        if token.lower() == "on":
            return "on"
        if token.lower() == "yes":
            return "yes"
        if token.lower() == "no":
            return "no"
        try:
            if "." in token or "e" in token.lower():
                return float(token)
            return int(token)
        except (ValueError, TypeError):
            pass
        return token
