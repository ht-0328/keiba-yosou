"""RaceDescriber（1レースの予想を、印の付いた馬・買い目・◎ の理由と近走の文にする）のテスト。値は架空。"""

from __future__ import annotations

from yosou.review import names

from 今週の予想.race_describer import RaceDescriber
from 今週の予想.race_plan import PlacePick, RacePlan
from 今週の予想.tests.test_forecast_store import sample_forecast
from 今週の予想.ticket_pick import TicketPick
from 今週の予想.ticket_rules import PLACE_LABEL

RID = "2025041905010101"
TRIFECTA_RULE = "3連単（◎軸・マルチ・期待値 1.0 以上）"


def _ticket(rule: str, ticket_type: str, horses: list[int], label: str, value: float | None, odds: float | None, dropped: str = "") -> dict:
    return {"rule": rule, "ticket_type": ticket_type, "combo": "".join(f"{horse:02d}" for horse in horses), "horses": horses, "label": label,
            "stake_units": 1.0, "value": value, "probability": None, "odds": odds, "dropped": dropped}


def _forecast(timing: str = "前日") -> dict:
    """◎ 3 馬A・○ 1 馬B・消 8 馬C（危険な人気馬）・無印 5 馬D・消 6 馬E（前の版の、危険でない消）。"""
    forecast = sample_forecast(RID)
    top = forecast["horses"][0]
    forecast["horses"] = [
        top,
        {**top, "rank": 2, "mark": "○", "horse_no": 1, "horse_name": "馬B", "probability": 0.30, "win_odds": 5.0, "popularity": 2.0,
         "place_value": 0.9, "win_value": 0.8, "summary": "", "is_danger": False},
        {**top, "rank": 3, "mark": "消", "horse_no": 8, "horse_name": "馬C", "probability": 0.20, "win_odds": 2.5, "popularity": 1.0,
         "place_value": 0.7, "win_value": 0.6, "summary": "", "is_danger": True},
        {**top, "rank": 4, "mark": "－", "horse_no": 5, "horse_name": "馬D", "probability": 0.05, "win_odds": 40.0, "popularity": 9.0,
         "place_value": 0.5, "win_value": 0.4, "summary": ""},
        {**top, "rank": 5, "mark": "消", "horse_no": 6, "horse_name": "馬E", "probability": 0.04, "win_odds": 50.0, "popularity": 10.0,
         "place_value": 0.4, "win_value": 0.3, "summary": "", "is_danger": False},
    ]
    trifectas = [_ticket(TRIFECTA_RULE, "3連単", [3, 1, other], f"3→1→{other}", 1.0 + other / 100, 50.0) for other in range(10, 21)]
    forecast["tickets"] = [
        _ticket(PLACE_LABEL, "複勝", [3], "3", 1.05, 1.5),
        _ticket("単勝", "単勝", [3], "3", None, 3.1),
        _ticket("ワイド", "ワイド", [1, 3], "1-3", 1.2, 6.0),
        _ticket("ワイド（2モデル一致）", "ワイド", [1, 3], "1-3", 1.2, 6.0),
        *trifectas,
        _ticket(TRIFECTA_RULE, "3連単", [3, 1, 8], "3→1→8", 1.23, 60.0, dropped="トリガミ"),
        _ticket("馬連", "馬連", [1, 3], "1-3", 0.8, 2.0, dropped="トリガミ"),
    ]
    forecast["timing"] = timing
    return forecast


def _plan(**changes) -> RacePlan:
    base = dict(rid=RID, title="2025-04-19（土） 東京 1R", timing="当日", kind="勝負", reason="見込みの利益 E = 0.30単位 > 0", profit_units=0.3,
                max_value=1.05, graded=False, picks=(PlacePick(3, 0.42, 1.05, 1.5, 1600),), budget_yen=5000,
                tickets=(TicketPick("単勝", "03", "3", 1.085, 3.1, 300), TicketPick("馬単", "0301", "3→1", None, 12.0, 100),
                         TicketPick("ワイド", "0103", "1-3", 1.2, 6.0, 100, kind=names.MATCH_COMBO)),
                ticket_reason="◎の単勝の期待値が 1.00 以上なので馬単も買う")
    return RacePlan(**{**base, **changes})


def test_印の付いた馬と危険な人気馬だけを書き_無印と危険でない消は出さない() -> None:
    text = RaceDescriber().describe(_forecast())
    lines = text.splitlines()
    assert lines[0] == "### 2025-04-19（土） 東京 1R"
    assert lines[1] == "時点: 前日（出馬表とオッズがある）。◎ランク A（的中率 23%）・配当率 A（56%）。"
    assert lines[2] == "◎  3 馬A  1人気 3.1倍  3着内 42%  単勝の期待値 1.08  複勝の期待値 1.05"
    assert lines[3] == "○  1 馬B  2人気 5.0倍  3着内 30%  単勝の期待値 0.80  複勝の期待値 0.90"
    assert lines[4] == "消  8 馬C  1人気 2.5倍  3着内 20%  単勝の期待値 0.60  複勝の期待値 0.70  （危険な人気馬なので消）"
    assert "馬D" not in text and "馬E" not in text


def test_枠順の無い木曜の予想は馬番を横線で書き_人気とオッズと期待値も横線() -> None:
    forecast = _forecast("木曜")
    for horse in forecast["horses"]:
        horse.update(horse_no=None, popularity=None, win_odds=None, win_value=None, place_value=None)
    forecast["tickets"] = []
    text = RaceDescriber().describe(forecast)
    assert "◎  - 馬A  -人気 -倍  3着内 42%  単勝の期待値 -  複勝の期待値 -" in text
    assert "- 複勝: なし（財布かオッズが無いので金額は出さない）" in text


def test_計画が無ければ複勝は金額なしで期待値の線の馬だけ_当日でなければ組の期待値は買わない() -> None:
    text = RaceDescriber().describe(_forecast())
    assert "実際に買う買い目:\n- 複勝: 3 馬A（期待値 1.05）（財布かオッズが無いので金額は出さない）\n" in text
    assert "- 単勝・馬単: なし（単勝（期待値）の馬がいない。馬単は ◎の単勝の期待値が 1.00 以上のレースだけ。くわしくは下の理由）" in text
    assert "- 組の期待値の買い目（枠連・馬連・馬単・ワイド・3連複・3連単）: なし（当日の予想でないので買わない）" in text
    # 当日の予想で組が無いときは、理由の言い回しが変わる
    assert "なし（組の期待値が線以上の組が無いか、下の理由のとおり）" in RaceDescriber().describe(_forecast("当日"))


def test_計画があれば複勝の参加の種類と合計_単勝馬単と組の期待値は1点の額と点数で書く() -> None:
    text = RaceDescriber().describe(_forecast("当日"), _plan())
    assert "- 複勝（勝負）: 3 馬A（期待値 1.05、1,600円）  合計 1,600円\n  （見込みの利益 E = 0.30単位 > 0）" in text
    assert "- 単勝: 3（オッズ 3.1）  1点 300円 × 1点 = 300円" in text
    assert "- 馬単: 3→1（オッズ 12.0）  1点 100円 × 1点 = 100円" in text
    assert "- ワイド（組の期待値）: 1-3（期待値 1.20・オッズ 6.0）  1点 100円 × 1点 = 100円" in text
    assert "  （◎の単勝の期待値が 1.00 以上なので馬単も買う）" in text
    # 買った券種（単勝）は参考に出さない
    assert "- 単勝: 1点" not in text
    # 複勝を買わない計画は、理由だけ
    assert "- 複勝: なし（期待値が線に届かない）" in RaceDescriber().describe(_forecast("当日"), _plan(kind="買わない", reason="期待値が線に届かない", picks=()))


def test_参考の買い目は複勝と2モデル一致を除き_10点を超えれば残りは点数だけ_トリガミは数だけ() -> None:
    text = RaceDescriber().describe(_forecast())
    assert "参考の買い目（回収率 100% 超えをまだ確かめられていない買い方。金額は1点 100円で数えた額）:" in text
    assert "- 単勝: 1点 100円  3" in text
    assert "- ワイド: 1点 100円  1-3" in text and "2モデル一致" not in text
    assert ("- 3連単（◎軸・マルチ・期待値 1.0 以上）: 11点 1,100円  3→1→20・3→1→19・3→1→18・3→1→17・3→1→16・3→1→15・3→1→14・3→1→13・3→1→12・3→1→11"
            " ほか 1点（トリガミ・オッズ無しで外す 1点）") in text
    assert "- 馬連: なし（トリガミ・オッズ無しで外す 1点）" in text
    assert text.count("\n- 複勝") == 1  # 複勝の行は「実際に買う買い目」だけで、参考の買い目には出ない


def test_本命の理由と近走の文を最後に書き_近走が無い前の版では省く() -> None:
    forecast = _forecast()
    assert RaceDescriber().describe(forecast).splitlines()[-1] == "◎ の理由: 総合の文"
    forecast["horses"][0]["story"] = {"career_runs": 2, "runs": [], "words": [], "lines": ["- 2025-03-01 未勝利（…）2着。", "- 評価: 上向き（…）"]}
    assert RaceDescriber().describe(forecast).endswith("◎ の理由: 総合の文\n◎ の近走（古い順）:\n- 2025-03-01 未勝利（…）2着。\n- 評価: 上向き（…）")
