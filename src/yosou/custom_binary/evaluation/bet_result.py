"""選んだ馬を、単勝・複勝1点100円ずつ買った結果。"""

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import PLACE_PAYOUT, RACE_DATE, RACE_ID, WIN_PAYOUT
from yosou.shared.feature.value_types import as_numbers

from .bootstrap_lower_bound import BootstrapLowerBound
from .payback_rules import STAKE


class BetResult:
    """``rows``（真偽の配列）の馬を買ったときの、点数・レース数・的中率・回収率・回収率の下限。"""

    def of(self, data: TrainingData, rows: np.ndarray, name: str) -> dict:
        bets = int(rows.sum())
        win = as_numbers(data.evaluation[WIN_PAYOUT]).fillna(0).to_numpy()[rows]
        place = as_numbers(data.evaluation[PLACE_PAYOUT]).fillna(0).to_numpy()[rows]
        races = data.ids[RACE_ID].to_numpy()[rows]
        days = data.ids[RACE_DATE].to_numpy()[rows]
        if bets == 0:
            return {"買い方": name, "点数": 0, "レース数": 0, "単勝的中率": None, "単勝回収率": None, "単勝回収率の下限": None,
                    "複勝的中率": None, "複勝回収率": None, "複勝回収率の下限": None}
        lower = BootstrapLowerBound()
        return {
            "買い方": name, "点数": bets, "レース数": int(len(set(races))),
            "単勝的中率": float((win > 0).mean()), "単勝回収率": float(win.sum() / (STAKE * bets)),
            "単勝回収率の下限": lower.of(days, win),
            "複勝的中率": float((place > 0).mean()), "複勝回収率": float(place.sum() / (STAKE * bets)),
            "複勝回収率の下限": lower.of(days, place),
        }
