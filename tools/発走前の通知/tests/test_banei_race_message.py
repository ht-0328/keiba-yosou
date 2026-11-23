"""BaneiRaceMessage（ばんえいの通知の文）のテスト。予想は架空。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from 発走前の通知.banei_forecast_store import BaneiForecastStore
from 発走前の通知.banei_race_message import BaneiRaceMessage

_RID = "2026112383170309"


def _store(folder: Path, picks: list[dict]) -> BaneiForecastStore:
    store = BaneiForecastStore(folder)
    forecast = {"rid": _RID, "race_number": 9, "race_name": "テスト特別", "condition": "Ｂ３－３", "post": "1830", "water": 2.4, "body_weights": 0,
                "runners": [{"number": 1, "name": "ウマイチ", "mark": "◎", "p_win": 0.314, "c_win": 0.348},
                            {"number": 7, "name": "ウマナナ", "mark": "○", "p_win": 0.111, "c_win": 0.134},
                            {"number": 3, "name": "ウマサン", "mark": "", "p_win": 0.05, "c_win": 0.05}],
                "picks": picks}
    store.path(_RID).parent.mkdir(parents=True)
    store.path(_RID).write_text(json.dumps(forecast, ensure_ascii=False), encoding="utf-8")
    return store


def test_見出しと馬場水分と印と3連単の買い目を書く(tmp_path: Path) -> None:
    picks = [{"order": [8, 1, 7], "probability": 0.0123, "gap": 2.41, "strong": True},
             {"order": [1, 8, 7], "probability": 0.02, "gap": 1.6, "strong": False}]
    lines = BaneiRaceMessage(_store(tmp_path, picks)).build(_RID).text.splitlines()
    assert lines[0] == "**帯広（ばんえい） 9R テスト特別 Ｂ３－３（18:30 発走）**"
    assert lines[1] == "馬場水分 2.4%・馬体重は未着（馬体重なしで予想）"
    assert lines[3] == "◎ 1 ウマイチ（勝つ確率 31%・世間の見立て 35%）"
    assert "ウマサン" not in "\n".join(lines)
    assert "3連単 2点・200円（1点 100円）" in lines
    assert "★ 8→1→7（確率 1.2%・ずれ 2.4倍）" in lines
    assert "1→8→7（確率 2.0%・ずれ 1.6倍）" in lines


def test_買う組が無ければ_見送りと書く(tmp_path: Path) -> None:
    text = BaneiRaceMessage(_store(tmp_path, [])).build(_RID).text
    assert "3連単: 買う組なし" in text


def test_予想が無ければ_RuntimeError(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        BaneiRaceMessage(BaneiForecastStore(tmp_path)).build(_RID)
