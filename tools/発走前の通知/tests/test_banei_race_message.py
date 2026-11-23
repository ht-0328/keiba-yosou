"""BaneiRaceMessage（ばんえいの通知の文と表の画像）のテスト。予想は架空。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from 今週の予想.forecast_columns import HORSE_NO, MARK, WIN_ODDS

from 発走前の通知.banei_forecast_store import BaneiForecastStore
from 発走前の通知.banei_race_message import BaneiRaceMessage

_RID = "2026112383170309"
_PICKS = [{"order": [8, 1, 7], "probability": 0.0123, "gap": 2.41, "strong": True},
          {"order": [1, 8, 7], "probability": 0.02, "gap": 1.6, "strong": False},
          {"order": [8, 7, 1], "probability": 0.011, "gap": 1.5, "strong": False}]


class _Fixed:
    """枠番・騎手名を元DB から読む代わりに、決まった値を返す。"""

    def __init__(self, values: dict[int, object]) -> None:
        self._values = values

    def read(self, rid: str) -> dict[int, object]:
        return self._values


def _runner(number: int, name: str, mark: str, p_win: float, reason: str = "", win_odds: float | None = None) -> dict:
    return {"number": number, "name": name, "mark": mark, "mark_reason": reason, "p_win": p_win, "p_top3": min(p_win * 2.5, 1.0), "c_win": p_win,
            "win_odds": win_odds, "place_odds": None, "win_value": None if win_odds is None else p_win * win_odds, "place_value": None}


def _forecast(picks: list[dict], body_weights: int = 10) -> dict:
    runners = [_runner(1, "ウマイチ", "◎", 0.31, "勝つ確率がレース内1位（31%）", 2.5), _runner(7, "ウマナナ", "○", 0.2), _runner(3, "ウマサン", "▲", 0.15),
               _runner(4, "ウマヨン", "△", 0.1), _runner(5, "ウマゴ", "△", 0.09), _runner(2, "ウマニ", "－", 0.08),
               _runner(8, "ウマハチ", "☆", 0.07, "印の無い馬の中で、予想が世間の見立てを上回る度合いが1位")]
    return {"rid": _RID, "race_number": 9, "race_name": "テスト特別", "condition": "Ｂ３－３", "post": "1830", "water": 2.4,
            "body_weights": body_weights, "runners": runners, "picks": picks}


def _message(folder: Path, forecast: dict | None) -> BaneiRaceMessage:
    store = BaneiForecastStore(folder)
    if forecast is not None:
        store.path(_RID).parent.mkdir(parents=True)
        store.path(_RID).write_text(json.dumps(forecast, ensure_ascii=False), encoding="utf-8")
    return BaneiRaceMessage(store, frames=_Fixed({1: 1, 7: 6}), jockeys=_Fixed({1: "騎手一"}))


def test_文は地方の通知と同じ形_見出しと時点_印は1つにつき1行_推奨買目(tmp_path: Path) -> None:
    notice = _message(tmp_path, _forecast(_PICKS)).build(_RID)
    lines = notice.text.splitlines()
    assert lines[0] == "**ばんえい帯広 9R テスト特別 Ｂ３－３（18:30 発走）** ばんえいの予想・当日の時点"
    assert lines[1] == "馬場水分 2.4%"
    assert lines[2] == "◎ 1 ウマイチ：勝つ確率がレース内1位（31%）"
    assert lines[5] == "△ 4 ウマヨン・5 ウマゴ"
    assert lines[6] == "☆ 8 ウマハチ：印の無い馬の中で、予想が世間の見立てを上回る度合いが1位"
    assert "ウマニ" not in notice.text
    assert lines[7] == "推奨買目（1点 100円・合計 3点 300円）:"
    assert lines[8:10] == ["3連単 ★8→1→7・8→7→1", "3連単 1→8→7"]


def test_全頭の表の画像を添付する(tmp_path: Path) -> None:
    notice = _message(tmp_path, _forecast(_PICKS)).build(_RID)
    assert notice.attachments == (tmp_path / "2026-11-23" / f"{_RID}.png",)
    assert notice.attachments[0].stat().st_size > 0


def test_表は印の順で_無印は最後_オッズが無ければ欠損(tmp_path: Path) -> None:
    card = _message(tmp_path, None).card(_forecast(_PICKS), {}, {})
    assert card.table[MARK].tolist() == ["◎", "○", "▲", "△", "△", "☆", "－"]
    assert card.table[HORSE_NO].tolist() == [1, 7, 3, 4, 5, 8, 2]
    assert card.table[WIN_ODDS].iloc[0] == 2.5 and card.table[WIN_ODDS].isna().iloc[1]
    assert card.footer.total == "合計 3点 300円（1点 100円）"


def test_買う組が無ければ_推奨買目はなしと理由(tmp_path: Path) -> None:
    message = _message(tmp_path, _forecast([]))
    assert "推奨買目: なし（世間の見立てよりずれて高い 3連単の組が無い）" in message.build(_RID).text
    assert message.card(_forecast([]), {}, {}).footer.none


def test_馬体重が届く前は_時点にそう書く(tmp_path: Path) -> None:
    card = _message(tmp_path, None).card(_forecast([], body_weights=0), {}, {})
    assert (card.timing, card.race_day) == ("馬体重が届く前の時点", False)


def test_予想が無ければ_LookupError(tmp_path: Path) -> None:
    with pytest.raises(LookupError):
        _message(tmp_path, None).build(_RID)
