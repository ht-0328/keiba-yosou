"""道具「地方の直前の買い目」の学習用の表を作る。

    uv run python "research/地方の直前の材料で買う/analysis/training_table.py"            # 締め切りの 10分前の断面で作る
    uv run python "research/地方の直前の材料で買う/analysis/training_table.py" --minutes 12

材料は reports/地方の12分前の材料で買う/ にあるもの:
- chunks/: 時系列オッズの断面（odds_history_fetch.py が貯めたもの）。「今の断面」は、締め切りの --minutes 分前かそれより前でいちばん新しい発売中の断面。
  前の断面（約2分前・約5分前・約10分前・約20分前・約35分前）は、通知のとき（tools/地方の直前の買い目/repository の OddsSnapshotRepository）と同じに、
  今の断面の時刻から数えて、その時刻かそれより前でいちばん新しい断面を取る
- table.pkl: 馬ごとの確定オッズ・着順・オッズを使わない出馬表の時点の予想（odds_table.py が作る）
- pred-stale12/: 12分前のオッズを材料にした当日の時点の予想（stale_odds_swap.py で作業用の DB の写しのオッズを差し替えて backtest したもの）
- 先生（確定オッズを材料にした当日の時点の予想）は reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証/
1着の馬がちょうど1頭のレースの、着順のある馬だけを残す。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

_PROJECT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(_PROJECT / "tools")]

from 地方の直前の買い目 import late_columns as c  # noqa: E402
from 地方の直前の買い目.late_training_table import DEFAULT_PATH  # noqa: E402
from 地方の直前の買い目.repository.odds_snapshot_repository import EARLIER, EARLIER_A  # noqa: E402

SOURCE = _PROJECT / "reports" / "地方の12分前の材料で買う"
TEACHER = _PROJECT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証"
#: 断面のファイルの列（CSV には見出しが無い）。
_CSV_COLUMNS = "{'key':'VARCHAR','kubun':'VARCHAR','announced':'VARCHAR','win_total':'BIGINT','horse_no':'INTEGER','win':'DOUBLE','plo':'DOUBLE','phi':'DOUBLE'}"
#: 発表月日時分（MMDDhhmm）→ その月の中での分。
_MINUTE = "(CAST(substr(announced,3,2) AS INT)*24 + CAST(substr(announced,5,2) AS INT))*60 + CAST(substr(announced,7,2) AS INT)"
#: 断面の新しさの順。同じ分に断面が2つあるときは、単勝の票数の合計の多いほうを新しいと見る。
_ORDER = f"CAST({_MINUTE} AS BIGINT) * 10000000000 + coalesce(win_total, 0)"


def snapshots(minutes: int) -> pd.DataFrame:
    """馬ごとの、今の断面と前の断面のオッズ（鍵は ``key``（開催日・競馬場・レース番号の 12桁）と馬番）。今の断面にオッズの無い馬は入らない。"""
    folder = (SOURCE / "chunks").as_posix()
    mem = duckdb.connect()
    mem.execute(f"""CREATE TABLE t AS SELECT DISTINCT key, kubun, horse_no, win, plo, phi, {_MINUTE} AS m, {_ORDER} AS o FROM (
        SELECT * FROM read_parquet('{folder}/snaps-*.parquet') UNION ALL
        SELECT * FROM read_csv('{folder}/snaps-*.csv', header=false, columns={_CSV_COLUMNS})) WHERE win > 0""")
    mem.execute(f"""CREATE TABLE now AS SELECT key, max(m) FILTER (WHERE kubun = '1' AND m <= close_m - {minutes}) AS now_m FROM (
        SELECT *, coalesce(min(m) FILTER (WHERE kubun = '3') OVER (PARTITION BY key), max(m) FILTER (WHERE kubun = '1') OVER (PARTITION BY key)) AS close_m
        FROM t) GROUP BY key""")
    earlier = ", ".join(f"arg_max(t.win, t.o) FILTER (WHERE t.m <= n.now_m - {back}) AS {name}" for name, back in EARLIER.items())
    return mem.execute(f"""
        WITH win_wide AS (
            SELECT t.key, t.horse_no, arg_max(t.win, t.o) AS {c.ODDS_NOW}, {earlier}, arg_min(t.win, t.o) AS {c.ODDS_FIRST}, max(t.m) AS last_m, max(n.now_m) AS now_m
            FROM t JOIN now n USING (key) WHERE t.kubun = '1' AND t.m <= n.now_m GROUP BY t.key, t.horse_no
        ), place_wide AS (
            SELECT t.key, t.horse_no, arg_max(t.plo, t.o) FILTER (WHERE t.m = n.now_m) AS {c.PLACE_LOW}, arg_max(t.phi, t.o) FILTER (WHERE t.m = n.now_m) AS {c.PLACE_HIGH},
                   arg_max(t.plo, t.o) FILTER (WHERE t.m <= n.now_m - {EARLIER_A}) AS {c.PLACE_LOW_A}
            FROM t JOIN now n USING (key) WHERE t.plo > 0 AND t.m <= n.now_m GROUP BY t.key, t.horse_no
        )
        SELECT w.* EXCLUDE (last_m, now_m), p.{c.PLACE_LOW}, p.{c.PLACE_HIGH}, p.{c.PLACE_LOW_A}
        FROM win_wide w LEFT JOIN place_wide p USING (key, horse_no) WHERE w.last_m = w.now_m""").df()


def probabilities(path: Path, name: str) -> pd.DataFrame:
    """backtest の予測の表（レースID・馬番・確率）を、結ぶ鍵と ``name`` の列にする。"""
    table = pd.read_pickle(path)
    frame = pd.DataFrame({c.RACE_ID: table["レースID"].astype(str), c.HORSE_NO: pd.to_numeric(table["馬番"], errors="coerce"),
                          name: table["確率"].astype(float)})
    return frame.dropna().astype({c.HORSE_NO: int}).drop_duplicates([c.RACE_ID, c.HORSE_NO])


def main(args: argparse.Namespace) -> None:
    results = pd.read_pickle(SOURCE / "table.pkl").rename(columns={"p1_thu": c.WIN_FREE, "p3_thu": c.TOP3_FREE, "win_odds": c.FINAL_ODDS})
    results = results[["key", c.RACE_ID, c.HORSE_NO, c.RACE_DATE, c.FIELD_SIZE, c.WIN_FREE, c.TOP3_FREE, c.FINAL_ODDS, "finish", c.WON]]
    table = results.merge(snapshots(args.minutes), on=["key", c.HORSE_NO], how="inner")
    for path, name in ((SOURCE / "pred-stale12" / "race_day-1着.pkl", c.WIN_MODEL), (SOURCE / "pred-stale12" / "race_day.pkl", c.TOP3_MODEL),
                       (TEACHER / "race_day-1着.pkl", c.WIN_TEACHER)):
        table = table.merge(probabilities(path, name), on=[c.RACE_ID, c.HORSE_NO], how="left")
    table = table.dropna(subset=[c.ODDS_NOW, c.FINAL_ODDS, "finish", c.WIN_MODEL])
    table = table[(table[c.FINAL_ODDS] > 0) & (table[c.ODDS_NOW] > 0)]
    table = table[table.groupby(c.RACE_ID)[c.WON].transform("sum") == 1]
    out = table[[*c.MATERIAL_COLUMNS, c.FINAL_ODDS, c.WON, c.WIN_TEACHER]].reset_index(drop=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_pickle(args.out)
    print(f"書きました: {args.out}（{out[c.RACE_ID].nunique():,} レース・{len(out):,} 頭・{out[c.RACE_DATE].min()}〜{out[c.RACE_DATE].max()}）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--minutes", type=int, default=10, help="締め切りの何分前の断面で作るか（既定: 10）")
    parser.add_argument("--out", type=Path, default=DEFAULT_PATH, help=f"書く先（既定: {DEFAULT_PATH}）")
    main(parser.parse_args())
