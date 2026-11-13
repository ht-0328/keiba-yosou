"""元DB の写しで予想するときに使う、スピード指数のとっておき（``reports/能力指数/cache``）の写しを作る。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from 共通.ability.figure_cache import DEFAULT_FOLDER

#: とっておきのファイル（中身と、どの DB・どの日まで・どの作り方で作ったかの印）。
_FIGURES, _STAMP = "figures.parquet", "stamp.json"
#: 写しの置き場所のフォルダ名（元DB の写しと同じフォルダの中）。
FOLDER_NAME = "能力指数のキャッシュ"


class FigureCacheCopy:
    """スピード指数のとっておきは、作ったときの DB のファイルの場所を印に持ち、場所が違うと作り直して上書きする。元DB の写しで予想すると、
    本物のとっておきが写しの印で上書きされ、そのあとのレースの予想が作り直し（1回 1分ほど）で遅れる。そのため、写しの隣にとっておきを写し、
    印の DB の場所だけを写しに書き換えて、予想にはこちらを渡す（中身は同じ元DB から作ったものなので、そのまま使える）。
    本物のとっておきがまだ無ければ何もせず、予想は写しの隣に作り直す（本物は書き換えない）。"""

    def __init__(self, source: Path = DEFAULT_FOLDER) -> None:
        self._source = Path(source)

    def copy(self, snapshot_db: Path) -> Path:
        """``snapshot_db`` の隣にとっておきを写し、その場所を返す。"""
        target = snapshot_db.parent / FOLDER_NAME
        target.mkdir(parents=True, exist_ok=True)
        figures, stamp = self._source / _FIGURES, self._source / _STAMP
        if not (figures.is_file() and stamp.is_file()):
            return target
        shutil.copyfile(figures, target / _FIGURES)
        mark = json.loads(stamp.read_text(encoding="utf-8"))
        mark["db"] = str(snapshot_db.resolve())
        (target / _STAMP).write_bytes(json.dumps(mark, ensure_ascii=False).encode("utf-8"))
        return target
