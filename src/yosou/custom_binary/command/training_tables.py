"""学習の結果を表にする。"""

from 共通.render import Table

from ..evaluation import HISTORICAL_NOTE, PAYBACK_NOTE
from ..workflow import TrainedModel


class TrainingTables:
    """設定の要約・検証期間の成績・検証期間の回収率の3つの表。"""

    def __init__(self, trained: TrainedModel) -> None:
        self._trained = trained

    def tables(self) -> list[Table]:
        validation = self._trained.validation
        # 検証期間は早期終了の判定にも使ったので、未学習の成績は evaluate（テスト期間）で見る。
        note = "検証期間は早期終了の判定に使ったため、成績はやや良く出る。" + HISTORICAL_NOTE
        return [
            self._summary(), Table.from_records(validation["scores"], title="検証期間の成績", note=note),
            Table.from_records(validation["paybacks"], title="検証期間の回収率", note=PAYBACK_NOTE),
        ]

    def _summary(self) -> Table:
        settings = self._trained.settings
        return Table(["項目", "値"], [
            ["保存先", str(self._trained.folder)], ["目的", settings.target], ["時点", settings.timing.label],
            ["特徴量数", len(settings.selected)], ["特徴量", " / ".join(settings.selected)],
            ["人気範囲", f"{settings.popularity.minimum or 1}〜{settings.popularity.maximum or '上限なし'}"],
            ["条件", settings.conditions.label()],
            ["オッズの基準", "あり" if settings.odds_baseline else "なし"],
        ], title="学習完了")
