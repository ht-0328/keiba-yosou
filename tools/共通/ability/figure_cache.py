"""全部の過去の走のスピード指数を作って、ファイルにとっておく。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from .. import keys
from .ability_builder import AbilityBuilder
from .ability_settings import AbilitySettings
from .run_source import RunSource
from .speed_figure import FIGURE

#: とっておく場所（Git 対象外）。
DEFAULT_FOLDER = Path(__file__).resolve().parents[3] / "reports" / "能力指数" / "cache"
#: とっておく列（能力指数を作るのと、表に出すのに要る列）。
KEPT: tuple[str, ...] = (
    "race_id", "race_date", "horse_id", "horse_no", "venue", "venue_code", "surface", "distance_m", "condition",
    "class_name", "finish", FIGURE,
)
#: 読む最初の日（DB にある最初の年）。
_FIRST_DAY = date(2011, 1, 1)


class FigureCache:
    """スピード指数の付いた、全部の過去の走（1行 = 1頭の出走）を返す。

    DB のファイル・中央の確定成績の最後の開催日・作り方の設定が、とっておいたときと同じなら、ファイルを読むだけ（数秒）。
    違えば（新しい週の成績が入った・設定を変えた）、全部作り直してとっておく（1〜2分）。
    1度読んだものは覚えておき、同じ ``FigureCache`` で次に呼ばれたときは読み直さない（検索画面で続けて開くとき）。
    基準タイムとペース補正は、DB にある全部の確定成績で求める。
    """

    def __init__(self, settings: AbilitySettings, folder: Path = DEFAULT_FOLDER) -> None:
        self._settings = settings
        self._folder = folder
        self._memo: tuple[dict, pd.DataFrame] | None = None

    def load(self, con: duckdb.DuckDBPyConnection, *, rebuild: bool = False) -> pd.DataFrame:
        latest = self._latest_final_day(con)
        stamp = {"db": self._db_file(con), "latest": latest, "settings": repr(self._settings)}
        if not rebuild and self._memo is not None and self._memo[0] == stamp:
            return self._memo[1]
        if not rebuild and self._stamp() == stamp:
            frame = self._read()
        else:
            runs = RunSource(con).read(_FIRST_DAY)
            frame = AbilityBuilder(self._settings, pd.Timestamp(latest)).build(runs).runs[list(KEPT)]
            self._write(frame, stamp)
        self._memo = (stamp, frame)
        return frame

    def _db_file(self, con: duckdb.DuckDBPyConnection) -> str:
        rows = con.execute("SELECT file FROM pragma_database_list WHERE name = current_database()").fetchall()
        return str(Path(rows[0][0]).resolve()) if rows and rows[0][0] else ""

    def _latest_final_day(self, con: duckdb.DuckDBPyConnection) -> str:
        sql = f"SELECT max({keys.race_date_expr()}) FROM ra WHERE {keys.jra_only()} AND {keys.final_only()}"
        return str(con.execute(sql).fetchone()[0])

    def _stamp(self) -> dict | None:
        path = self._folder / "stamp.json"
        if not path.exists() or not (self._folder / "figures.parquet").exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _read(self) -> pd.DataFrame:
        with duckdb.connect() as local:
            frame = local.execute(f"SELECT * FROM read_parquet('{(self._folder / 'figures.parquet').as_posix()}')").df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))

    def _write(self, frame: pd.DataFrame, stamp: dict) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        with duckdb.connect() as local:
            local.register("frame", frame)
            local.execute(f"COPY frame TO '{(self._folder / 'figures.parquet').as_posix()}' (FORMAT parquet)")
        (self._folder / "stamp.json").write_text(json.dumps(stamp, ensure_ascii=False), encoding="utf-8")
