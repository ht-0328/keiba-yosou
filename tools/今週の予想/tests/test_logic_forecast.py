"""AI＋ロジック予想（展開のロジック ``SlowPaceLogic``・クラスのロジック ``OpenClassLogic`` と、印の買い目を直す1行 ``LogicForecast``）のテスト。値は架空。"""

from __future__ import annotations

from 今週の予想.logic_forecast import LogicForecast
from 今週の予想.logic_skip import LogicSkip
from 今週の予想.open_class_logic import OpenClassLogic
from 今週の予想.slow_pace_logic import SlowPaceLogic

#: 10頭。逃げ・先行は 1・2 の2頭（20%）。◎ の 5 は差し。
SLOW = {1: "逃げ", 2: "先行", 3: "差し", 4: "差し", 5: "差し", 6: "追込", 7: "差し", 8: "追込", 9: "差し", 10: "差し"}


def test_逃げ先行が頭数の2割以下で_本命が差し追込なら見送る() -> None:
    logic = SlowPaceLogic()
    assert logic.skips(SLOW, 10, 5)
    assert logic.reason(SLOW, 10, 5) == "逃げ・先行が 2頭（頭数の 20%）と少なく、ペースが遅くなりそうで、◎ が差し"
    # ◎ が逃げ・先行なら見送らない。逃げ・先行が3頭（30%）なら見送らない。◎ の脚質が無ければ見送らない
    assert not logic.skips(SLOW, 10, 1)
    assert not logic.skips({**SLOW, 3: "先行"}, 10, 5)
    assert not logic.skips({key: value for key, value in SLOW.items() if key != 5}, 10, 5)
    assert not logic.skips(SLOW, 10, None)


def _forecast(expected_value: float) -> dict:
    """当日の予想。◎ は 5。印の買い目は単勝 5 だけ（期待値で、買うか見送りかが決まる）。"""
    horses = [{"horse_no": number, "mark": "◎" if number == 5 else "－"} for number in range(1, 11)]
    tickets = [{"rule": "単勝", "label": "5", "value": expected_value, "odds": 4.0, "dropped": ""}]
    return {"timing": "当日", "horses": horses, "tickets": tickets}


def test_AIが買うレースでロジックに当たれば見送り_当たらなければAIと同じく買う() -> None:
    assert LogicForecast().line(_forecast(1.2), SLOW) == ("印の買い目は見送り（逃げ・先行が 2頭（頭数の 20%）と少なく、"
                                                          "ペースが遅くなりそうで、◎ が差し）")
    assert LogicForecast().line(_forecast(1.2), {**SLOW, 3: "先行"}) == "印の買い目を AI と同じく買う（ロジックに当たらない）"


def test_AIが見送るレースは見送り_当日でなければ行を出さない() -> None:
    assert LogicForecast().line(_forecast(0.8), SLOW) == "見送り（AI と同じ）"
    assert LogicForecast().line({**_forecast(1.2), "timing": "前日"}, SLOW) is None


#: 逃げ・先行が3頭（30%）で、展開のロジックに当たらない。
NOT_SLOW = {**SLOW, 3: "先行"}


def test_オープン以上のクラスだけ見送る() -> None:
    logic = OpenClassLogic()
    assert [logic.skips(name) for name in ("オープン", "L", "G3", "G2", "G1")] == [True] * 5
    assert [logic.skips(name) for name in ("新馬", "未勝利", "1勝クラス", "2勝クラス", "3勝クラス", "")] == [False] * 6
    assert logic.reason("G3") == "オープン以上のレース（G3）で、◎ が勝ち切りにくい"


def test_展開に当たらなくてもオープン以上なら見送り_両方に当たれば展開の理由を出す() -> None:
    graded = {**_forecast(1.2), "header": {"クラス": "G3"}}
    assert LogicForecast().line(graded, NOT_SLOW) == "印の買い目は見送り（オープン以上のレース（G3）で、◎ が勝ち切りにくい）"
    assert LogicForecast().skip(graded, NOT_SLOW) == LogicSkip("クラス", "オープン以上のレース（G3）で、◎ が勝ち切りにくい")
    assert LogicForecast().skip(graded, SLOW).name == "展開"
    assert LogicForecast().line({**_forecast(1.2), "header": {"クラス": "3勝クラス"}}, NOT_SLOW) == "印の買い目を AI と同じく買う（ロジックに当たらない）"


def test_見送りの理由は_AIが見送るレースとロジックに当たらないレースでは無い() -> None:
    assert LogicForecast().skip({**_forecast(0.8), "header": {"クラス": "G3"}}, SLOW) is None
    assert LogicForecast().skip(_forecast(1.2), NOT_SLOW) is None
