"""研究「裏目を買うかの予想」の印の表（1行 = 1頭）を書く。

    uv run python research/裏目を買うかの予想/analysis/marked_table.py [--db <DB>]

当日の予想（オッズの動きで直したもの。研究「既存モデルの改善」の ``graded_race_day/odds_move-top3``・``odds_move-win``）の
テスト期間の全レースに、道具「印の成績」と同じ部品で印を付け、確定の着順を添える。
出るもの（Git 対象外）: ``reports/裏目を買うかの予想/marked.pkl``。``--db`` は元DB の写しを渡せる（既定は元DB。読むだけ）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "tools"))

import 印の成績.mark_stats as ms  # noqa: E402
from 共通 import db  # noqa: E402

OUT = _ROOT / "reports" / "裏目を買うかの予想" / "marked.pkl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default=None, help="読む DB（既定は元DB）")
    given = parser.parse_args()
    options = ["--form", "graded_race_day/odds_move-top3", "--win", "graded_race_day/odds_move-win", "--timing", "当日"]
    args = ms.build_parser().parse_args(options + (["--db", given.db] if given.db else []))
    predictions = ms.PredictionFile(args.form).load()
    tested = predictions[predictions["period"] == ms.TEST]
    marker = ms.BacktestMarker(ms._estimator(args.models), odds_known=True)
    ids = tested["race_id"].drop_duplicates()
    with db.open_db(args.db, default=db.JRA) as con:
        favorites, wins = ms.PredictionFile(args.danger).load(), ms.PredictionFile(args.win).load()
        places = marker.places(ms.RaceResults().read(con, pd.concat([tested["race_id"], favorites["race_id"], wins["race_id"]])))
        pools = ms.PoolWinReader().read(con, ids)
        movements = ms.OddsSnapshotRepository().read(con, ids)
    dangers, _ = ms.FavoriteDangerJudge(tuple(args.danger_bands)).judge(favorites, places)
    marked = marker.mark(tested, places, dangers, ms.WinValueAttacher().attach(wins, places), pools, movements)
    marked = marked[marked["race_id"].isin(set(ids))]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    marked.to_pickle(OUT)
    print(f"{marked['race_id'].nunique():,} レースの印の表を {OUT} に書いた")


if __name__ == "__main__":
    main()
