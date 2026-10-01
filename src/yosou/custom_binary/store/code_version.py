"""学習したときのコードの版。"""

import hashlib
from pathlib import Path
import subprocess

from .model_location import PROJECT_ROOT


class CodeVersion:
    """未コミットの新しい実装も識別できるよう、Git のコミットと、Pythonソースのハッシュを残す。"""

    def __init__(self, root: Path = PROJECT_ROOT) -> None:
        self._root = root

    def current(self) -> dict:
        return {"git_revision": self._revision(), "python_source_sha256": self._source_digest()}

    def _source_digest(self) -> str:
        digest = hashlib.sha256()
        for folder in (self._root / "src", self._root / "tools"):
            for path in sorted(folder.rglob("*.py")):
                digest.update(path.relative_to(self._root).as_posix().encode())
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def _revision(self) -> str:
        try:
            return subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=self._root, capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "unknown"
