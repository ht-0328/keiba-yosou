"""YAML の1つの組（キーと値）が、知っているキーだけでできているかを確かめる。"""


class YamlMapping:
    """``where`` は、誤りのときに見せる場所の名前（例: ``training``）。"""

    def check(self, value, allowed: set[str], where: str) -> dict:
        if not isinstance(value, dict):
            raise ValueError(f"{where}はキーと値の組で指定してください")
        unknown = value.keys() - allowed
        if unknown:
            raise ValueError(f"{where}に未知のキーがあります: {', '.join(sorted(unknown))}")
        return value
