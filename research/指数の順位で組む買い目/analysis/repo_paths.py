"""keiba-yosou のリポジトリの src（予想のパッケージ）と tools（道具）を import の探索路に足す。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: この研究を research/<研究>/ に置いたときのリポジトリ直下（analysis/ の3つ上）。
_PLACED_ROOT = Path(__file__).resolve().parents[3]
#: 研究フォルダをリポジトリの外に置いて動かすときに、リポジトリ直下を指す環境変数。
ROOT_ENV = "KEIBA_YOSOU_ROOT"


class RepoPaths:
    """リポジトリ直下を見つけ、``src`` と ``tools`` を ``sys.path`` に足す。

    置き場所が research/<研究>/ ならそのリポジトリ、そうでなければ環境変数 ``KEIBA_YOSOU_ROOT`` のフォルダ。
    どちらも無ければ ``FileNotFoundError``。絶対パスはコードに埋め込まない。
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = self._resolve(root)

    @property
    def src(self) -> Path:
        return self.root / "src"

    @property
    def tools(self) -> Path:
        return self.root / "tools"

    @property
    def reports(self) -> Path:
        """Git 対象外の出力の置き場所。"""
        return self.root / "reports"

    def add_to_sys_path(self) -> "RepoPaths":
        for folder in (self.src, self.tools):
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
        return self

    @staticmethod
    def _looks_like_repo(folder: Path) -> bool:
        return (folder / "pyproject.toml").is_file() and (folder / "tools").is_dir() and (folder / "src" / "yosou").is_dir()

    def _resolve(self, root: Path | None) -> Path:
        candidates = [Path(root)] if root else []
        if os.environ.get(ROOT_ENV):
            candidates.append(Path(os.environ[ROOT_ENV]))
        candidates.append(_PLACED_ROOT)
        for candidate in candidates:
            if self._looks_like_repo(candidate.resolve()):
                return candidate.resolve()
        raise FileNotFoundError(
            f"keiba-yosou のリポジトリが見つかりません。研究フォルダを research/ に置くか、環境変数 {ROOT_ENV} でリポジトリ直下を指定してください。"
        )
