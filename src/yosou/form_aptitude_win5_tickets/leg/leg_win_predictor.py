"""対象レース1つの全頭の1着の確率を出す。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.shared.dataset import HORSE_NAME, HORSE_NO, RACE_ID, OddsResolver
from yosou.shared.feature.group import WIN_ODDS
from yosou.shared.feature.odds import MarketWinProbability
from yosou.shared.repository import AnnouncedOddsRepository
from yosou.shared.workflow import WIN_PROBABILITY, FormAptitudePrediction

from ..repository import LegRunnerRepository
from ..repository.leg_runner_repository import HORSE_NAME as RUNNER_NAME
from ..repository.leg_runner_repository import HORSE_NO as RUNNER_NO
from ..repository.leg_runner_repository import ODDS as RUNNER_ODDS
from .leg_model import LegModel
from .leg_model_choice import LegModelChoice

#: 結果の表の列（今のモデルの予測の結果の列の名前に合わせる）。
COLUMNS: tuple[str, ...] = (RACE_ID, HORSE_NO, HORSE_NAME, WIN_ODDS, WIN_PROBABILITY)


class LegWinPredictor:
    """選んだ確率（``LegModelChoice``）で、対象レースの全頭の1着の確率を出す（設計書 05 の図2）。

    今のモデルの当日・前日は、``FormAptitudePrediction``（道具「今週の予想」と同じ組み立て）でその時点の予測をして、
    1着になる確率（2つのモデルの平均）と単勝オッズを取り出す。当日に券種のオッズが無いときに券種オッズなしのモデルに
    切り替えるのは、今のモデルの流れの中で行われる。オッズだけ（障害）は、締め切り前の単勝オッズ（無ければ出走の行の確定オッズ）から
    オッズから見た勝率を出して、そのまま1着の確率にする。
    ``prediction`` はコマンドが作って渡す（材料を作る部品 ``MaterialAttachers`` を、接続から作る関数として渡したもの）。
    """

    def __init__(self, prediction: FormAptitudePrediction) -> None:
        self._prediction = prediction
        self._market = MarketWinProbability()

    def predict(self, con: duckdb.DuckDBPyConnection, race_id: str, choice: LegModelChoice) -> pd.DataFrame:
        """列は ``COLUMNS``（1行 = 1頭）。"""
        if choice.model is LegModel.ODDS_ONLY:
            return self._odds_only(con, race_id)
        table = self._prediction.run(con, race_id, choice.model.timing)
        if WIN_PROBABILITY not in table.columns:
            raise FileNotFoundError(
                "今のモデルの1着のモデルがありません。`uv run python -m yosou.form_aptitude_top3 train` で今のモデルを学び直してください"
            )
        return table[list(COLUMNS)].reset_index(drop=True)

    def _odds_only(self, con: duckdb.DuckDBPyConnection, race_id: str) -> pd.DataFrame:
        """障害の対象レース。オッズから見た勝率をそのまま1着の確率にする。"""
        runners = LegRunnerRepository(con).read(race_id)
        announced = OddsResolver(AnnouncedOddsRepository(con)).resolve(race_id, None)
        odds = runners[RUNNER_NO].map(announced) if announced else runners[RUNNER_ODDS]
        if odds.isna().all():
            raise LookupError(
                f"{race_id} の単勝オッズが元DB にありません。jvdata-store で `jvstore realtime` を実行して、締め切り前のオッズを取り込んでください"
            )
        race_ids = pd.Series(race_id, index=runners.index)
        return pd.DataFrame({
            RACE_ID: race_ids, HORSE_NO: runners[RUNNER_NO], HORSE_NAME: runners[RUNNER_NAME], WIN_ODDS: odds.astype(float),
            WIN_PROBABILITY: self._market.of(race_ids, odds),
        })
