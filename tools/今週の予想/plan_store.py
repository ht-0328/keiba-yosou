"""買うレースの計画を、今週の予想の結果と一緒に保存する。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.race_plan import RacePlan

#: 1日の計画のファイル名。
PLAN_FILE = "plan.json"


class PlanStore:
    """1開催日の計画を ``<置き場所>/<開催日>/plan.json`` に書き、各レースの結果の JSON にも ``plan``（参加の種類・理由・買い目・金額）を書き足す
    （画面の「今週の予想」タブが、レースの一覧と1レースの頭に出す）。"""

    def __init__(self, forecasts: ForecastStore) -> None:
        self._forecasts = forecasts

    def save(self, day: date, plans: list[RacePlan], wallet: dict[str, Any]) -> Path:
        folder = self._forecasts.folder / day.isoformat()
        folder.mkdir(parents=True, exist_ok=True)
        payload = {"date": day.isoformat(), "wallet": wallet, "races": [plan.to_dict() for plan in plans]}
        path = folder / PLAN_FILE
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        for plan in plans:
            forecast = self._forecasts.load(plan.rid)
            if forecast is not None:
                forecast["plan"] = plan.to_dict()
                self._forecasts.save(forecast)
        return path

    def load(self, day: date) -> dict[str, Any] | None:
        path = self._forecasts.folder / day.isoformat() / PLAN_FILE
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
