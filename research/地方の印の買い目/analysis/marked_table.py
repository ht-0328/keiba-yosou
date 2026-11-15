"""地方の印の表（1行 = 1頭）: 地方の全頭の予想（2023年前半までで学んだ当日の予測）のテスト期間の全レースに、道具「印の成績」と同じ部品で印を付け、
確定の着順を添える（研究「裏目を買うかの予想」の ``analysis/marked_table.py`` の地方版）。

印の組の表（``MarkCombos``）の元になった印の成績の動かし方（`--scene 地方 --timing 当日 --no-danger --models <models-2024検証>`）と同じ引数で付ける。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import 印の成績.mark_stats as ms
from 共通 import db


@dataclass(frozen=True)
class MarkedTableSettings:
    """全頭の予想（3着以内）と1着の予想の予測の pkl、複勝の見込みの倍率の置き場所（全頭の予想のモデルと同じ区切りのもの）、元DB のパス（None なら地方の元DB）。"""

    form: Path
    win: Path
    models: Path
    db_path: str | None = None


class MarkedTable:
    def __init__(self, settings: MarkedTableSettings) -> None:
        self._settings = settings

    def build(self) -> pd.DataFrame:
        s = self._settings
        options = ["--form", str(s.form), "--win", str(s.win), "--timing", "当日", "--scene", "地方", "--no-danger", "--no-upset",
                   "--models", str(s.models)]
        args = ms.build_parser().parse_args(options + (["--db", s.db_path] if s.db_path else []))
        predictions = ms.PredictionFile(args.form).load()
        tested = predictions[predictions["period"] == ms.TEST]
        marker = ms.BacktestMarker(ms._estimator(args.models), odds_known=True)
        ids = tested["race_id"].drop_duplicates()
        with db.open_db(args.db, default=db.LOCAL) as con:
            wins = ms.PredictionFile(args.win).load()
            places = marker.places(ms.RaceResults().read(con, pd.concat([tested["race_id"], wins["race_id"]])))
            pools = ms.PoolWinReader().read(con, ids)
            movements = ms.OddsSnapshotRepository().read(con, ids)
        dangers = pd.DataFrame(columns=list(ms.DANGER_COLUMNS))
        marked = marker.mark(tested, places, dangers, ms.WinValueAttacher().attach(wins, places), pools, movements)
        return marked[marked["race_id"].isin(set(ids))].reset_index(drop=True)
