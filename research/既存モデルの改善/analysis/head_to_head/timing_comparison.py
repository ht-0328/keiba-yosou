"""1つの時点で、今の予想と対戦レーティングを足した作り方を、区切りごとのログ損失で比べて採否を決める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TOP3
from yosou.shared.dataset.column_names import POPULARITY

from ..scores import BinaryScores
from ..walk_forward import WINDOW
from .prediction_truth import SCORE

#: 突き合わせる鍵。
_KEY = [RACE_ID, HORSE_ID]
#: 採用の基準: 7つの区切りのうち、足した作り方のログ損失が小さい区切りの数の下限（材料の実験と同じ）。
MIN_BETTER_WINDOWS = 5
#: 全期間の行の名前。
OVERALL = "全期間"
#: 表の列の名前。
BETTER = "小さい"


class TimingComparison:
    """今の予想（``current``）と足した作り方（``rated``）のテスト期間の予測を、両方にある行だけで比べる。

    採用の基準は研究の材料の実験と同じ: テスト期間のログ損失が今の予想より小さい区切りが 7つのうち 5つ以上あり、
    全期間を合わせても小さいこと。ログ損失の差は小さいので 1000倍して出す。人気別 AUC（同じ人気の馬どうしの見分けやすさ）も添える。
    ``label`` は答えの列（既定は3着以内。1着のモデルどうしを比べるときは ``WIN``）。
    """

    def __init__(self, label: str = TOP3) -> None:
        self._label = label

    def common(self, current: pd.DataFrame, rated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """両方にある行だけにした2つの表（並びは同じ）。"""
        keys = current[_KEY].merge(rated[_KEY], on=_KEY)
        return keys.merge(current, on=_KEY, how="left"), keys.merge(rated, on=_KEY, how="left")

    def by_window(self, current: pd.DataFrame, rated: pd.DataFrame) -> pd.DataFrame:
        """区切りごとの行数・ログ損失・差（×1000）・足した作り方のほうが小さいか・人気別 AUC。最後の行は全期間。"""
        windows = list(dict.fromkeys(current[WINDOW]))
        rows = [self._row(window, current[current[WINDOW] == window], rated[rated[WINDOW] == window]) for window in windows]
        rows.append(self._row(OVERALL, current, rated))
        return pd.DataFrame(rows)

    def adopted(self, table: pd.DataFrame) -> bool:
        """採用の基準を満たすか（``by_window`` の表から）。"""
        windows = table[table[WINDOW] != OVERALL]
        overall = table[table[WINDOW] == OVERALL].iloc[0]
        return int(windows[BETTER].sum()) >= MIN_BETTER_WINDOWS and bool(overall[BETTER])

    def _row(self, window: str, current: pd.DataFrame, rated: pd.DataFrame) -> dict[str, object]:
        now, new = self._scores(current), self._scores(rated)
        return {
            WINDOW: window, "行数": len(current),
            "今の予想のログ損失": round(now["ログ損失"], 5), "足した作り方のログ損失": round(new["ログ損失"], 5),
            "差（×1000）": round((new["ログ損失"] - now["ログ損失"]) * 1000, 3), BETTER: new["ログ損失"] < now["ログ損失"],
            "今の予想の人気別AUC": round(now["人気別AUC"], 4), "足した作り方の人気別AUC": round(new["人気別AUC"], 4),
        }

    def _scores(self, frame: pd.DataFrame) -> dict[str, float]:
        return BinaryScores().of(frame[self._label], frame[SCORE], frame[POPULARITY])
