"""学習に使っていない期間の予測に、本番と同じ決め方で印・危険な人気馬・期待値を付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.place_value import PlacePriceEstimator

from 今週の予想.danger_picker import MARKED_BANDS
from 印の成績.backtest_marker import BacktestMarker
from 印の成績.favorite_danger_judge import FavoriteDangerJudge
from 印の成績.win_value_attacher import WinValueAttacher

from 高配当の買い目.marking_inputs import MarkingInputs


class HorseMarker:
    """全頭の予想・1着の予想・人気馬の予想の予測（``PredictionFile.load``）と、元DB から読んだもの（``MarkingInputs``）から、
    印（◎○▲△☆注消）・危険な人気馬・単勝と複勝の期待値を付けた1頭1行の表を作る。元DB は使わない（読む段は ``MarkingInputReader``）。

    道具「印の成績」の部品を、当日の予想と同じ順に呼ぶ（``BacktestMarker.places`` → ``FavoriteDangerJudge`` → ``WinValueAttacher`` →
    ``BacktestMarker.mark``。オッズのある時点の決め方。消にできる人気帯は今週の予想と同じ ``MARKED_BANDS``）。
    ``estimator`` は複勝の見込みの倍率（全頭の予想の学習済みモデルと一緒に保存した ``place_price.json``。無ければ複勝の期待値は欠損値）。
    ``tested`` は印を付ける行（全頭の予想のテスト期間の行。開催日で絞ったものでもよい）。危険な人気馬の線は区切りごとの検証期間で決めるので、
    ``favorites`` は絞らずに全部の行を渡す。
    """

    def __init__(self, estimator: PlacePriceEstimator | None) -> None:
        self._marker = BacktestMarker(estimator, odds_known=True)

    def mark(self, tested: pd.DataFrame, wins: pd.DataFrame, favorites: pd.DataFrame, inputs: MarkingInputs) -> pd.DataFrame:
        places = self._marker.places(inputs.results)
        dangers, _ = FavoriteDangerJudge(tuple(MARKED_BANDS)).judge(favorites, places)
        win_values = WinValueAttacher().attach(wins, places)
        marked = self._marker.mark(tested, places, dangers, win_values, inputs.pools, inputs.movements)
        return marked.assign(race_id=marked["race_id"].astype(str))
