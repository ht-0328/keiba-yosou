"""1着のモデルの確率の誤差を、区切りごとに「オッズから見た勝率そのまま」と比べる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import WIN
from yosou.shared.dataset.column_names import POPULARITY

from ..scores import BinaryScores
from ..walk_forward import WINDOW
from .win_prediction_truth import MARKET_WIN, SCORE

#: 全期間の行の名前と、表の列の名前。
OVERALL = "全期間"
BETTER = "小さい"


class WinComparison:
    """1着のモデル（``score``）の確率の誤差（ログ損失）を、何も学ばずにオッズから見た勝率をそのまま使ったときと比べる。

    木曜はオッズが無いので比べる相手が無い（オッズから見た勝率の列は確定オッズから出した値。木曜の行には「確定オッズを知っていたら」の
    値で、本番では使えない）。そのため木曜の表は参考に出す。人気別 AUC（同じ人気の馬どうしの見分けやすさ）も添える。
    """

    def by_window(self, frame: pd.DataFrame) -> pd.DataFrame:
        """区切りごとの行数・ログ損失（モデル・オッズから見た勝率）・差（×1000）・モデルのほうが小さいか・人気別 AUC。最後の行は全期間。"""
        windows = list(dict.fromkeys(frame[WINDOW]))
        rows = [self._row(window, frame[frame[WINDOW] == window]) for window in windows]
        rows.append(self._row(OVERALL, frame))
        return pd.DataFrame(rows)

    def _row(self, window: str, frame: pd.DataFrame) -> dict[str, object]:
        model = BinaryScores().of(frame[WIN], frame[SCORE], frame[POPULARITY])
        market = BinaryScores().of(frame[WIN], frame[MARKET_WIN].fillna(frame[SCORE]), frame[POPULARITY])
        return {
            WINDOW: window, "行数": len(frame),
            "モデルのログ損失": round(model["ログ損失"], 5), "オッズから見た勝率のログ損失": round(market["ログ損失"], 5),
            "差（×1000）": round((model["ログ損失"] - market["ログ損失"]) * 1000, 3), BETTER: model["ログ損失"] < market["ログ損失"],
            "モデルの人気別AUC": round(model["人気別AUC"], 4), "1着の割合": round(model["実際の割合"], 4),
            "モデルの確率の平均": round(model["確率の平均"], 4),
        }
