"""保存してある1レースの予想と計画から、通知の文と添付を作る。"""

from __future__ import annotations

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.race_describer import RaceDescriber
from 今週の予想.race_plan import RacePlan

from 発走前の通知.race_notice import RaceNotice


class RaceMessage:
    """文は、次のレースの予想（スキル）と開催日ごとのまとめと同じ ``RaceDescriber`` の文（印の付いた馬・消・実際に買う買い目・
    参考の買い目・◎ の理由と近走）。買う計画は forecast.py が結果の JSON に書き足した ``plan``。
    添付は ``ForecastStore`` が書いた全頭の予想根拠（``<rid>.md``）。"""

    def __init__(self, store: ForecastStore | None = None, describer: RaceDescriber | None = None) -> None:
        self._store = store or ForecastStore()
        self._describer = describer or RaceDescriber()

    def build(self, rid: str) -> RaceNotice:
        forecast = self._store.load(rid)
        if forecast is None:
            raise LookupError(f"予想の結果がありません（{rid}）")
        plan = RacePlan.from_dict(forecast["plan"]) if forecast.get("plan") else None
        reasons = self._store.reasons_path(rid)
        return RaceNotice(self._describer.describe(forecast, plan), reasons if reasons.is_file() else None)
