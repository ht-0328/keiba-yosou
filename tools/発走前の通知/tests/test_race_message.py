"""RaceMessage（保存した中央の予想から通知の文と添付を作る）のテスト。予想の値は架空。DB は開かず、レース一覧と枠番は偽物。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.race_plan import PlacePick, RacePlan
from 今週の予想.tests.test_forecast_store import sample_forecast
from 今週の予想.ticket_pick import TicketPick

from 発走前の通知.race_message import RaceMessage
from 発走前の通知.position_counts import PositionCounts
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.track_tendency import TrackTendency

RID = "2025041905010101"
RACE = ScheduledRace(rid=RID, venue="東京", number=1, name="テスト特別", post=datetime(2025, 4, 19, 10, 5))


class _Schedule:
    def read(self, day: str) -> list[ScheduledRace]:
        return [RACE]


class _Frames:
    def read(self, rid: str) -> dict[int, int]:
        return {3: 2}


def _forecast(*, plan: RacePlan | None = None, danger: bool = True) -> dict:
    forecast = sample_forecast(RID)
    forecast["timing"] = "当日"
    favorite = {**forecast["horses"][0], "rank": 2, "mark": "消", "horse_no": 7, "horse_name": "馬B", "probability": 0.30,
                "is_danger": danger, "mark_reason": "危険な人気馬（2番人気）"}
    longshot = {**forecast["horses"][0], "rank": 3, "mark": "－", "horse_no": 1, "horse_name": "馬C", "probability": 0.05}
    forecast["horses"] += [favorite, longshot]
    if plan is not None:
        forecast["plan"] = plan.to_dict()
    return forecast


def _message(tmp_path: Path, forecast: dict) -> tuple[RaceMessage, ForecastStore]:
    store = ForecastStore(tmp_path / "今週の予想")
    store.save(forecast)
    return RaceMessage(store, schedule=_Schedule(), frames=_Frames(), folder=tmp_path / "中央"), store


def test_文は見出し_目安_印の付いた馬_買い目だけで_添付は表の画像と全頭の予想根拠(tmp_path: Path) -> None:
    plan = RacePlan(RID, "t", "当日", "勝負", "見込みの利益が大きい", 0.3, 1.05, False,
                    picks=(PlacePick(3, 0.42, 1.05, 1.5, 1200),), budget_yen=1200,
                    tickets=(TicketPick("単勝", "03", "3", 1.085, 3.1, 300),))
    message, store = _message(tmp_path, _forecast(plan=plan))
    notice = message.build(RID)
    lines = notice.text.splitlines()
    assert lines[0] == "**東京 1R テスト特別（10:05 発走）** 中央の予想・当日の時点"
    assert lines[1] == "期待度 A（点数 0.28）"
    # 画像の見出しにも地方と同じ期待度の札。オッズの無い木曜は札を描かない
    assert message.card(_forecast(plan=plan), None, {}).badge == "期待度 A"
    assert message.card({**_forecast(plan=plan), "rank": None, "rank_score": None}, None, {}).badge == ""
    # 印の付いた馬を1つの印につき1行（◎・消 は印の理由を添える）。無印は書かない
    assert lines[2:4] == ["◎ 3 馬A：単勝の期待値がレース内1位", "消 7 馬B：危険な人気馬（2番人気）"]
    assert lines[4] == "買い目（合計 1,500円）:"
    assert lines[5].startswith("- 複勝（勝負）: 3 馬A（期待値 1.05、1,200円）")
    assert lines[6] == "- 単勝: 3（オッズ 3.1）  1点 300円 × 1点 = 300円"
    assert "参考の買い目" not in notice.text and "◎ の理由" not in notice.text
    image = tmp_path / "中央" / "2025-04-19" / f"{RID}.png"
    assert notice.attachments == (image, store.reasons_path(RID))
    assert image.stat().st_size > 0


class _Tendencies:
    def of(self, rid: str, venue: str) -> TrackTendency:
        return TrackTendency(venue, "芝", PositionCounts(3, 9, 8, 1, 0), PositionCounts(100, 300, 150, 100, 50))


def test_先に終わったレースがあれば_目安の下に馬場の傾向の行(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path / "今週の予想")
    store.save(_forecast())
    message = RaceMessage(store, schedule=_Schedule(), frames=_Frames(), folder=tmp_path / "中央", tendencies=_Tendencies())
    lines = message.build(RID).text.splitlines()
    assert lines[2] == "馬場 東京・芝（ここまで3R）: 前が止まらない。3着以内9頭の4角は 前 8・中 1・後ろ 0（過去3年の東京・芝は 前 50%・中 33%・後ろ 17%）"
    assert lines[3] == "◎ 3 馬A：単勝の期待値がレース内1位"


class _Styles:
    def read(self, rid: str) -> dict[int, str]:
        return {3: "先行", 7: "逃げ"}


def test_推定脚質を表の中身に渡す(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path / "今週の予想")
    store.save(_forecast())
    seen = []

    class _Image:
        def draw(self, card):
            seen.append(card)
            from PIL import Image
            return Image.new("RGB", (1, 1))

    RaceMessage(store, schedule=_Schedule(), frames=_Frames(), image=_Image(), folder=tmp_path / "中央", styles=_Styles()).build(RID)
    assert seen[0].styles == {3: "先行", 7: "逃げ"}


def test_表は印の順で_危険な人気馬でない消は無印(tmp_path: Path) -> None:
    message, _ = _message(tmp_path, _forecast(danger=False))
    card = message.card(_forecast(danger=False), RACE, {})
    assert list(card.table["mark"]) == ["◎", "－", "－"]
    assert list(card.table["horse_no"]) == [3, 7, 1]   # 同じ印の中は 3着以内の確率の高い順


def test_買わないときは_なし_と理由(tmp_path: Path) -> None:
    plan = RacePlan(RID, "t", "当日", "買わない", "見込みの利益が線に届かない", 0.0, 0.9, False)
    message, _ = _message(tmp_path, _forecast(plan=plan))
    assert message.build(RID).text.splitlines()[-1] == "買い目: なし（見込みの利益が線に届かない）"


def test_予想が無ければ止まる(tmp_path: Path) -> None:
    with pytest.raises(LookupError, match=RID):
        RaceMessage(ForecastStore(tmp_path), schedule=_Schedule(), frames=_Frames(), folder=tmp_path).build(RID)


def test_重賞は実際に買う買い目のあとに印の買い目を参考で出し_重賞でなければ出さない(tmp_path: Path) -> None:
    forecast = _forecast()
    forecast["header"] = {"クラス": "G1"}
    forecast["tickets"].append({"rule": "3連単（◎→○▲☆→○▲△☆）", "ticket_type": "3連単", "combo": "030701", "horses": [3, 7, 1],
                                "label": "3→7→1", "stake_units": 0.1, "value": None, "probability": None, "odds": 250.0, "dropped": ""})
    message, _ = _message(tmp_path, forecast)
    lines = message.build(RID).text.splitlines()
    head = lines.index("印の買い目（参考・1点 100円）:")
    # 単勝 ◎ と 3連単 ◎→○▲☆→○▲△☆ だけ（軸から流す形・トリガミの組は出さない）。予想に無い印の買い方は出さない
    assert lines[head + 1:] == ["- 単勝: 1点 100円  3", "- 3連単（◎→○▲☆→○▲△☆）: 1点 100円  3→7→1"]
    forecast["header"] = {"クラス": "3勝クラス"}
    message, _ = _message(tmp_path / "別", forecast)
    assert "印の買い目" not in message.build(RID).text
