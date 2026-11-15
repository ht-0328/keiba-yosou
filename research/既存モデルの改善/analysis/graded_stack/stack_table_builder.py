"""二段の予想の2段目に使う、重賞の行の表（1段目の確率・市場の見立て・W・K・結果）を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TOP3, WIN, TrainingData

from ..graded_race import IS_GRADED, K_NAMES, W_NAMES

#: 表の列（W・K のほか）。
BASE_TOP3, BASE_WIN, MARKET_WIN, MARKET_TOP3 = "base_top3", "base_win", "market_win", "market_top3"
Y_TOP3, Y_WIN, YEAR, FIELD = "y_top3", "y_win", "year", "field_size"
#: 1段目の予測の、テストの期間の行。
_TEST = "テスト"


class StackTableBuilder:
    """平地の重賞の行ごとに、1段目の確率（その年より前だけで学んだ予測のテストの行）と、確定オッズから見た勝率・3着以内率、
    W（重賞の格と実績）・K（その重賞の傾向）、目的変数（3着以内・1着）を並べる（1行 = 重賞の1頭）。

    ``table`` は1段目と同じ元の表（目的変数と評価用の列を取る）。``top3``・``win`` は1段目の予測（``PredictionStore`` の形）。
    ``materials`` は W の表、``tendency`` は K の表（どちらも race_id・horse_id の鍵）。1段目の予測の無い行は落とす。
    """

    def build(self, table: TrainingData, top3: pd.DataFrame, win: pd.DataFrame, materials: pd.DataFrame,
              tendency: pd.DataFrame) -> pd.DataFrame:
        rows = pd.DataFrame({
            "race_id": table.ids[RACE_ID].astype(str).to_numpy(), "horse_id": table.ids[HORSE_ID].astype(str).to_numpy(),
            "horse_no": table.ids[HORSE_NO].to_numpy(), "race_date": pd.to_datetime(table.ids[RACE_DATE]).to_numpy(),
            Y_TOP3: table.targets[TOP3].to_numpy(), Y_WIN: table.targets[WIN].to_numpy(),
            MARKET_WIN: table.evaluation["オッズから見た勝率"].to_numpy(), MARKET_TOP3: table.evaluation["オッズから見た3着以内率"].to_numpy(),
            FIELD: table.evaluation["確定の出走頭数"].to_numpy(),
        })
        graded = materials[materials[IS_GRADED].eq(1.0)][["race_id", "horse_id", *W_NAMES]]
        rows = rows.merge(graded, on=["race_id", "horse_id"], how="inner")
        rows = rows.merge(self._base(top3, BASE_TOP3), on=["race_id", "horse_id"], how="inner")
        rows = rows.merge(self._base(win, BASE_WIN), on=["race_id", "horse_id"], how="inner")
        rows = rows.merge(tendency[["race_id", "horse_id", *K_NAMES]], on=["race_id", "horse_id"], how="left")
        rows[YEAR] = rows["race_date"].dt.year
        return rows.dropna(subset=[Y_TOP3, Y_WIN, MARKET_WIN, MARKET_TOP3]).reset_index(drop=True)

    def _base(self, predictions: pd.DataFrame, name: str) -> pd.DataFrame:
        tests = predictions[predictions["期間"] == _TEST]
        frame = pd.DataFrame({"race_id": tests[RACE_ID].astype(str).to_numpy(), "horse_id": tests[HORSE_ID].astype(str).to_numpy(),
                              name: tests["確率"].to_numpy()})
        return frame.drop_duplicates(["race_id", "horse_id"], keep="last")
