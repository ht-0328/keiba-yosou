"""研究「AIとロジックの予想」: 展開のロジックの上に足す、見送りのロジックの候補と、期間ごとの成績。

    uv run python research/AIとロジックの予想/analysis/logic_candidates.py            # 探す期間（参考1・参考2・作る）
    uv run python research/AIとロジックの予想/analysis/logic_candidates.py --verify   # 確かめる期間と追加の確かめの期間（選んだ候補だけを数える）

候補は ``logic_scan.py`` で3つの期間とも低かった条件から作った。どれも「その条件のレースは印の買い目を見送る」。
``+`` でつなぐと、どれかに当たれば見送る組み合わせ（例 ``--also オープン以上+◎の単勝20倍以上``）。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import logic_scan  # noqa: E402
import race_materials  # noqa: E402

#: オープン以上のクラス（本番の ``tools/今週の予想/open_class_logic.py`` と同じ）。
OPEN_CLASSES: tuple[str, ...] = ("オープン", "L", "G3", "G2", "G1")
#: 確かめに使う期間（確かめる期間と、ロジックを探すときに一度も見ていない追加の確かめの期間）。
VERIFY: tuple[str, ...] = ("確かめる", race_materials.EXTRA[0])

Skip = Callable[[pd.DataFrame], pd.Series]


def _rarely_wins(t: pd.DataFrame) -> pd.Series:
    return (t["h_runs_before"] >= 10) & (t["h_wins_before"] / t["h_runs_before"].replace(0, np.nan) <= 0.10)


#: 名前 → 見送るレース（真が見送り）。
CANDIDATES: dict[str, Skip] = {
    "オープン以上": lambda t: t["class_name"].isin(OPEN_CLASSES),
    "11R": lambda t: t["race_no"] == 11,
    "◎の単勝20倍以上": lambda t: t["top_win_odds"] >= 20,
    "◎の単勝15倍以上": lambda t: t["top_win_odds"] >= 15,
    "2番人気の単勝7倍超": lambda t: t["odds2"] > 7,
    "◎が1枠": lambda t: t["h_frame_no"] == 1,
    "◎が16走以上": lambda t: t["h_runs_before"] > 15,
    "◎が10走以上で勝率10%以下": _rarely_wins,
}


def skip_of(name: str) -> Callable[[pd.DataFrame], np.ndarray]:
    """``+`` でつないだ名前なら、どれかに当たれば見送る。"""
    rules = [CANDIDATES[part] for part in name.split("+")]
    return lambda t: np.logical_or.reduce([rule(t).fillna(False).to_numpy(dtype=bool) for rule in rules])


def metrics(bought: pd.DataFrame, skip: np.ndarray, days: int) -> dict[str, float]:
    """見送らなかったレースだけの 買う数・回収率・的中率・1日の儲け。"""
    kept = bought[~skip]
    paid, back = kept["stake"].sum(), kept["back"].sum()
    return {"買う": len(kept), "回収率": back / paid, "的中率": (kept["back"] > 0).mean(), "1日の儲け": (back - paid) / days}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true", help="確かめる期間を数える（選んだ候補だけを見る）")
    parser.add_argument("--also", nargs="*", default=[], help="+ でつないだ組み合わせ")
    args = parser.parse_args()
    parts = pd.read_pickle(race_materials.PATH)
    for part in VERIFY if args.verify else logic_scan.SEARCH:
        bought, days = logic_scan.bought(parts[part]), parts[part]["day"].nunique()
        base = metrics(bought, np.zeros(len(bought), dtype=bool), days)
        print(f"{part} 今（AI＋展開） 買う {base['買う']} 回収率 {base['回収率']:.1%} 的中率 {base['的中率']:.1%} 1日の儲け {base['1日の儲け']:,.0f}円")
        for name in [*CANDIDATES, *args.also]:
            m = metrics(bought, skip_of(name)(bought), days)
            print(f"  {name}: 買う {m['買う']} 回収率 {m['回収率']:.1%}（{m['回収率'] - base['回収率']:+.1%}） "
                  f"的中率 {m['的中率']:.1%}（{m['的中率'] - base['的中率']:+.1%}） "
                  f"1日の儲け {m['1日の儲け']:,.0f}円（{m['1日の儲け'] - base['1日の儲け']:+,.0f}）")


if __name__ == "__main__":
    main()
