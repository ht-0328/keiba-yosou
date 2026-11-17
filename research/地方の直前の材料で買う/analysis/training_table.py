"""道具「地方の直前の買い目」の学習用の表を作る。

    uv run python "research/地方の直前の材料で買う/analysis/training_table.py"            # 締め切りの 10分前の断面で作る
    uv run python "research/地方の直前の材料で買う/analysis/training_table.py" --minutes 12

材料は reports/地方の12分前の材料で買う/ にあるもの:
- table.pkl: 馬ごとの「締め切りの k 分前の単勝・複勝オッズ」と確定オッズ・着順・オッズを使わない出馬表の時点の予想（build.py が作る）
- pred-stale12/: 12分前のオッズを材料にした当日の時点の予想（swap_odds.py で作業用の DB の写しのオッズを差し替えて backtest したもの）
- 先生（確定オッズを材料にした当日の時点の予想）は reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証/
1着の馬がちょうど1頭のレースの、着順のある馬だけを残す。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_PROJECT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(_PROJECT / "tools")]

from 地方の直前の買い目 import late_columns as c  # noqa: E402
from 地方の直前の買い目.late_training_table import DEFAULT_PATH  # noqa: E402

SOURCE = _PROJECT / "reports" / "地方の12分前の材料で買う"
TEACHER = _PROJECT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証"
#: 断面の分 → 動きを見る2つの前の断面の分。
EARLIER: dict[int, tuple[int, int]] = {8: (15, 30), 10: (20, 30), 12: (20, 30)}


def probabilities(path: Path, name: str) -> pd.DataFrame:
    """backtest の予測の表（レースID・馬番・確率）を、結ぶ鍵と ``name`` の列にする。"""
    table = pd.read_pickle(path)
    frame = pd.DataFrame({c.RACE_ID: table["レースID"].astype(str), c.HORSE_NO: pd.to_numeric(table["馬番"], errors="coerce"),
                          name: table["確率"].astype(float)})
    return frame.dropna().astype({c.HORSE_NO: int}).drop_duplicates([c.RACE_ID, c.HORSE_NO])


def main(args: argparse.Namespace) -> None:
    minutes = args.minutes
    first, second = EARLIER[minutes]
    table = pd.read_pickle(SOURCE / "table.pkl")
    table = table.rename(columns={f"win_{minutes}": c.ODDS_NOW, f"win_{first}": c.ODDS_A, f"win_{second}": c.ODDS_B, "win_first": c.ODDS_FIRST,
                                  f"plo_{minutes}": c.PLACE_LOW, f"phi_{minutes}": c.PLACE_HIGH, "p1_thu": c.WIN_FREE, "p3_thu": c.TOP3_FREE,
                                  "win_odds": c.FINAL_ODDS})
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
    parser.add_argument("--minutes", type=int, choices=sorted(EARLIER), default=10, help="締め切りの何分前の断面で作るか（既定: 10）")
    parser.add_argument("--out", type=Path, default=DEFAULT_PATH, help=f"書く先（既定: {DEFAULT_PATH}）")
    main(parser.parse_args())
