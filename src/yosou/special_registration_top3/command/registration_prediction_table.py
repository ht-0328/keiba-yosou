"""登録馬の予測の結果を表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from yosou.shared.command.cell_format import day_text, rounded
from yosou.shared.dataset import HORSE_NAME, RACE_DATE, RACE_ID
from yosou.shared.ml_model import MEMBER_TYPES

from ..repository import CARRIED, EXCHANGE, TRAINER
from ..workflow import PROBABILITY, TIMING_LABELS, WIN_PROBABILITY

#: 馬名のあとに出す列（特別登録から添えたもの）。
_INFO_COLUMNS = (TRAINER, CARRIED, EXCHANGE)


class RegistrationPredictionTable:
    """登録馬の予測の結果（1行 = 1頭）を、3着以内に入る確率の高い順に並べた表にする（設計書 04 の「コマンドの引数」）。

    列は 順位・馬名・調教師・負担重量・交流区分・出走すれば3着以内に入る確率・出走すれば1着になる確率・LightGBM と CatBoost の確率。
    馬番・オッズ・期待値の列は出ない（この時点には無い）。1着のモデルが無ければ、1着の確率の列は出ない。
    """

    def __init__(self, prediction: pd.DataFrame) -> None:
        self._prediction = prediction
        self._member_names = [model_type.name for model_type in MEMBER_TYPES]
        self._has_win = WIN_PROBABILITY in prediction.columns

    def table(self) -> Table:
        ranked = self._prediction.sort_values(PROBABILITY, ascending=False, kind="stable")
        rows = [self._row(rank, runner) for rank, (_, runner) in enumerate(ranked.iterrows(), start=1)]
        win_columns = [f"出走すれば{WIN_PROBABILITY}"] if self._has_win else []
        return Table(
            ["順位", "馬名", *_INFO_COLUMNS, f"出走すれば{PROBABILITY}", *win_columns, *self._member_names], rows,
            title=self._title(),
            note=f"確率は {' と '.join(self._member_names)} の平均（LightGBM・CatBoost の列は3着以内）。登録馬の全員に出し、出走するかどうかは当てていない。",
        )

    def _row(self, rank: int, runner: pd.Series) -> list[object]:
        info = [runner.get(column) for column in _INFO_COLUMNS]
        info[1] = rounded(info[1]) if isinstance(info[1], float) else info[1]
        win = [rounded(runner[WIN_PROBABILITY])] if self._has_win else []
        return [rank, runner[HORSE_NAME], *info, rounded(runner[PROBABILITY]), *win,
                *(rounded(runner[name]) for name in self._member_names)]

    def _title(self) -> str:
        first = self._prediction.iloc[0]
        return f"{first[RACE_ID]}（{day_text(first[RACE_DATE])}）の予測: {next(iter(TIMING_LABELS.values()))}の時点"
