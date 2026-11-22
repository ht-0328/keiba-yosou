"""LocalRaceMessage（地方の predict の JSON から通知の中身・文・添付の画像を作る）のテスト。予想の値は架空。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from 地方の直前の買い目.late_bet_file import LateBetFile
from 地方の直前の買い目.late_bets import LateBets
from 地方の直前の買い目.late_pick import LatePick

from 地方の推奨買目.mark_bets import MarkBets
from 地方の推奨買目.recommendation import Recommendation
from 地方の推奨買目.recommendation_set import RecommendationSet

from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.local_race_message import LocalRaceMessage
from 発走前の通知.position_counts import PositionCounts
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.track_tendency import TrackTendency

COLUMNS = ["順位", "馬番", "馬名", "単勝オッズ", "オッズから見た3着以内率", "複勝的中の確率", "複勝の期待値", "1着になる確率", "単勝の期待値",
           "3着以内に入る確率", "LightGBM", "CatBoost"]
ROWS = [
    [1, 7, "イチバン", 3.0, 0.70, 0.78, 1.10, 0.35, 1.05, 0.78, 0.77, 0.79],
    [2, 4, "ニバン", 2.7, 0.75, 0.71, 0.95, 0.27, 0.74, 0.71, 0.72, 0.70],
    [3, 8, "サンバン", 5.4, 0.55, 0.60, 1.00, 0.15, 0.81, 0.60, 0.61, 0.59],
    [4, 3, "ヨンバン", 14.2, 0.25, 0.34, 1.30, 0.06, 0.80, 0.34, 0.33, 0.35],
    [5, 2, "ゴバン", 18.3, 0.19, 0.29, 0.90, 0.04, 0.64, 0.29, 0.29, 0.29],
    [6, 1, "ロクバン", 40.0, 0.08, 0.10, 0.60, 0.01, 0.40, 0.10, 0.10, 0.10],
    [7, 6, "ナナバン", 80.0, 0.04, 0.05, 0.50, 0.005, 0.40, 0.05, 0.05, 0.05],
    [8, 5, "ハチバン", 150.0, 0.02, 0.02, 0.30, 0.002, 0.30, 0.02, 0.02, 0.02],
]
RID = "2026110547150401"
RACE = ScheduledRace(rid=RID, venue="笠松", number=1, name="", post=datetime(2026, 11, 5, 10, 25))
MARKS = MarkBets("買う（見込みの回収率 112%）。合計 5,000円で、どれが当たっても 6,000円以上戻る",
                 ("単勝（1点 計 3,500円）: 7 3,500円", "馬単（2点 計 1,500円）: 7→4 900円・7→8 600円"))
RECOMMENDED = RecommendationSet((Recommendation("枠連", (3, 5), 8.0, 0.30, 2.40), Recommendation("3連単", (7, 4, 8), 25.0, 0.076, 1.90),
                                 Recommendation("単勝", (7,), 3.0, 0.36, 1.08)))


def _forecast(timing: str) -> dict:
    return {"title": f"{RID}（2026-11-05）の予測: {timing}の時点", "columns": COLUMNS, "rows": [list(row) for row in ROWS], "note": "", "meta": {}}


class _Schedule:
    def read(self, day: str) -> list[ScheduledRace]:
        return [RACE]


class _Jockeys:
    def read(self, rid: str) -> dict[int, str]:
        return {7: "騎手A"}


class _Frames:
    def read(self, rid: str) -> dict[int, int]:
        return {7: 5, 4: 3}


class _Recommendations:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.marked: list[list[str]] = []

    def recommend(self, rid: str, forecast: dict) -> RecommendationSet:
        self.calls.append(rid)
        return RECOMMENDED

    def marks(self, rid: str, forecast: dict, marked) -> MarkBets:
        self.marked.append(list(marked["mark"]))
        return MARKS


def test_中身は印の順の全頭と_見出し_推奨買目() -> None:
    card = LocalRaceMessage().card(_forecast("当日"), RACE, {7: 5}, RECOMMENDED)
    assert card.title == "笠松 1R（10:25 発走）"
    assert card.heading == "笠松 1R" and card.post == "10:25 発走" and card.race_day
    assert list(card.table["mark"]) == ["◎", "○", "▲", "△", "△", "△", "☆", "注"]
    assert list(card.table["horse_no"])[:6] == [7, 4, 8, 3, 2, 1]
    assert card.frames == {7: 5}
    # 推奨買目の 単勝 7 は ◎ の単勝と同じ組なので1度だけ。複勝 3 は全頭の予想の線（1.30 ≥ 1.25）
    assert card.bets.lines() == ["単勝 7", "複勝 3", "枠連 3-5", "3連単 7→4→8"] and card.bets.points == 4


def test_文は_見出し_期待度_印の付いた馬_推奨買目だけ() -> None:
    message = LocalRaceMessage()
    text = message.describe(message.card(_forecast("当日"), RACE, {}, RECOMMENDED))
    assert text.splitlines() == [
        "**笠松 1R（10:25 発走）** 地方の予想・当日の時点",
        "期待度 なし（見込みを出せない）",   # 直前の買い目のファイルが無い組み立て
        "◎ 7 イチバン：単勝 30倍以下の馬の中で単勝の期待値がレース内1位（1着になる確率 35.0% × 単勝 3.0倍 = 1.05）",
        "○ 4 ニバン",
        "▲ 8 サンバン",
        "△ 3 ヨンバン・2 ゴバン・1 ロクバン",
        "☆ 5 ハチバン：穴馬（8番人気）の中で複勝の期待値がいちばん高い（0.30。線の 1.25 に届かないので表示だけで、買い目の相手には入れない）",
        "注 6 ナナバン：印の無い馬の中で、市場の見立て（4.0%）より来ると見る度合いがいちばん大きい（予想 5.0%）",
        "推奨買目（1点 100円・合計 4点 400円）:",
        "単勝 7",
        "複勝 3",
        "枠連 3-5",
        "3連単 7→4→8",
    ]


def test_推奨買目が無ければ_全頭の予想の単勝と複勝だけ() -> None:
    message = LocalRaceMessage()
    text = message.describe(message.card(_forecast("当日"), RACE, {}))
    assert text.splitlines()[8:] == ["推奨買目（1点 100円・合計 2点 200円）:", "単勝 7", "複勝 3"]


def test_前日の時点は買い目も期待度も出さず_その旨を書く() -> None:
    message = LocalRaceMessage()
    card = message.card(_forecast("前日"), RACE, {}, RECOMMENDED)
    text = message.describe(card)
    assert "前日の時点（馬体重が届く前なのでオッズだけ）" in text.splitlines()[0]
    assert text.splitlines()[1] == "期待度 なし（馬体重が届く前の前日の時点では出さない。当日の時点で出す）" and card.badge == ""
    assert "推奨買目: なし（馬体重が届く前の前日の時点では買わない）" in text
    assert "100円" not in text.splitlines()[-1]


def test_期待度は直前の買い目の線への近さから出し_推奨買目は前と同じ() -> None:
    message = LocalRaceMessage()
    near = LateBets((), "2つの見込みがそろって線以上の馬がいない", "11051015", 0.91)
    card = message.card(_forecast("当日"), RACE, {7: 5}, RECOMMENDED, late=near)
    assert card.expectation.grade == "A" and card.expectation.score == 0.91 and card.badge == "期待度 A"
    assert message.describe(card).splitlines()[1] == "期待度 A（点数 0.91）"
    assert card.bets.lines() == ["単勝 7", "複勝 3", "枠連 3-5", "3連単 7→4→8"]   # 期待度は買い目の条件に使わない
    # 推奨買目の見込みがどれだけ高くても、期待度には入らない
    bought = LateBets((LatePick(3, 14.2, 0.5, 1.1, (7, 4)),), "", "11051015", 1.158)
    assert message.card(_forecast("当日"), RACE, {}, RecommendationSet((), "期待値が線に届く組が無い"), late=bought).badge == "期待度 S"


def test_見込みを出せなければ_期待度は理由つきの_なし() -> None:
    message = LocalRaceMessage()
    card = message.card(_forecast("当日"), RACE, {}, RECOMMENDED, late=LateBets.none("時系列オッズの断面がまだ無い"))
    assert message.describe(card).splitlines()[1] == "期待度 なし（見込みを出せない: 時系列オッズの断面がまだ無い）" and card.badge == ""


def test_レース一覧に無ければ_predict_の見出しを使う() -> None:
    message = LocalRaceMessage()
    card = message.card(_forecast("当日"), None, {})
    assert message.describe(card).startswith(f"**{RID}（2026-11-05）の予測: 当日の時点** 地方の予想・当日の時点")


def test_組み立てると_推奨買目を呼び_文と_保存した表の画像の添付(tmp_path: Path) -> None:
    store = LocalForecastStore(tmp_path)
    store.path(RID).parent.mkdir(parents=True)
    store.path(RID).write_text(json.dumps(_forecast("当日"), ensure_ascii=False), encoding="utf-8")
    recommendations = _Recommendations()
    notice = LocalRaceMessage(store=store, schedule=_Schedule(), frames=_Frames(), jockeys=_Jockeys(), recommendations=recommendations).build(RID)
    assert recommendations.calls == [RID]
    assert recommendations.marked == [["◎", "○", "▲", "△", "△", "△", "☆", "注"]]   # 印を付けた表を渡す
    assert notice.text.startswith("**笠松 1R（10:25 発走）** 地方の予想・当日の時点")
    assert "3連単 7→4→8" in notice.text
    assert notice.text.splitlines()[-3:] == ["印の買い目: 買う（見込みの回収率 112%）。合計 5,000円で、どれが当たっても 6,000円以上戻る",
                                             "- 単勝（1点 計 3,500円）: 7 3,500円", "- 馬単（2点 計 1,500円）: 7→4 900円・7→8 600円"]
    assert notice.attachments == (store.image_path(RID),)
    assert store.image_path(RID).stat().st_size > 0


class _Styles:
    def read(self, rid: str) -> dict[int, str]:
        return {7: "逃げ", 4: "差し"}


def test_推定脚質を表の中身に渡す(tmp_path: Path) -> None:
    store = LocalForecastStore(tmp_path)
    store.path(RID).parent.mkdir(parents=True)
    store.path(RID).write_text(json.dumps(_forecast("当日"), ensure_ascii=False), encoding="utf-8")
    seen = []

    class _Image:
        def draw(self, card):
            seen.append(card)
            from PIL import Image
            return Image.new("RGB", (1, 1))

    LocalRaceMessage(store=store, schedule=_Schedule(), frames=_Frames(), jockeys=_Jockeys(), image=_Image(), styles=_Styles()).build(RID)
    assert seen[0].styles == {7: "逃げ", 4: "差し"}


class _Tendencies:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def of(self, rid: str, venue: str) -> TrackTendency:
        self.calls.append((rid, venue))
        return TrackTendency(venue, "ダート", PositionCounts(2, 6, 1, 2, 3), PositionCounts(100, 300, 150, 100, 50))


def test_先に終わったレースがあれば_見出しの下に馬場の傾向の行(tmp_path: Path) -> None:
    store = LocalForecastStore(tmp_path)
    store.path(RID).parent.mkdir(parents=True)
    store.path(RID).write_text(json.dumps(_forecast("当日"), ensure_ascii=False), encoding="utf-8")
    tendencies = _Tendencies()
    notice = LocalRaceMessage(store=store, schedule=_Schedule(), frames=_Frames(), jockeys=_Jockeys(), tendencies=tendencies).build(RID)
    assert tendencies.calls == [(RID, "笠松")]
    lines = notice.text.splitlines()
    assert lines[1] == "期待度 なし（見込みを出せない）"   # 直前の買い目のファイルが無い組み立て
    assert lines[2] == "馬場 笠松・ダート（ここまで2R）: 後ろから差せる。3着以内6頭の4角は 前 1・中 2・後ろ 3（過去3年の笠松・ダートは 前 50%・中 33%・後ろ 17%）"
    assert lines[3].startswith("◎ 7 イチバン：")


def test_印の買い目は推奨買目のあとに出し_画像の欄にも添える() -> None:
    message = LocalRaceMessage()
    card = message.card(_forecast("当日"), RACE, {}, RECOMMENDED, marks=MARKS)
    lines = message.describe(card).splitlines()
    assert lines.index("3連単 7→4→8") + 1 == lines.index("印の買い目: " + MARKS.heading)
    assert card.footer.notes[-3:] == ("印の買い目 " + MARKS.heading, "印の買い目 " + MARKS.lines[0], "印の買い目 " + MARKS.lines[1])


def test_印の買い目が出せなければ理由を書き_前日の時点は出さない(tmp_path: Path) -> None:
    message = LocalRaceMessage()
    none = MarkBets.none("印の買い目を出せない: 3連単のオッズがまだ DB にありません")
    assert message.describe(message.card(_forecast("当日"), RACE, {}, marks=none)).splitlines()[-1] == f"印の買い目: {none.heading}"
    text = message.describe(message.card(_forecast("前日"), RACE, {}, marks=MARKS))
    assert "印の買い目" not in text
    store = LocalForecastStore(tmp_path)
    store.path(RID).parent.mkdir(parents=True)
    store.path(RID).write_text(json.dumps(_forecast("前日"), ensure_ascii=False), encoding="utf-8")
    recommendations = _Recommendations()
    LocalRaceMessage(store=store, schedule=_Schedule(), frames=_Frames(), jockeys=_Jockeys(), recommendations=recommendations).build(RID)
    assert recommendations.marked == []   # 前日の時点は印の買い目を呼ばない


LATE = LateBets((LatePick(3, 14.2, 0.52, 1.10, (4, 7, 8, 2, 1)),), "", "11051015")


def test_直前の買い目は最後に出し_買う馬がいなければ理由_ファイルが無ければ出さない() -> None:
    message = LocalRaceMessage()
    lines = message.describe(message.card(_forecast("当日"), RACE, {}, RECOMMENDED, marks=MARKS, late=LATE)).splitlines()
    marks = dict(zip(message.marked(_forecast("当日"))["horse_no"], message.marked(_forecast("当日"))["mark"]))
    label = {no: f"{no}{'' if marks[no] == '－' else marks[no]}" for no in (3, 4, 7, 8, 2, 1)}
    others = ",".join(label[no] for no in (4, 7, 8, 2, 1))
    assert lines[-3:] == ["直前の買い目（確かめ中・1点 100円）:", f"- 単勝 {label[3]}（決めたときの単勝 14.2倍）100円",
                          f"- 3連単 {label[3]} → {others} → {others}（20点 2,000円）"]
    assert label[7] == "7◎"
    assert LocalRaceMessage.late_lines(LATE)[1] == "- 単勝 3（決めたときの単勝 14.2倍）100円"   # 印の表が無ければ馬番だけ
    none = LateBets.none("2つの見込みがそろって線以上の馬がいない")
    text = message.describe(message.card(_forecast("当日"), RACE, {}, late=none))
    assert text.splitlines()[-1] == "直前の買い目（確かめ中・1点 100円）: なし（2つの見込みがそろって線以上の馬がいない）"
    assert "直前の買い目" not in message.describe(message.card(_forecast("当日"), RACE, {}))
    assert "直前の買い目" not in message.describe(message.card(_forecast("前日"), RACE, {}, late=LATE))


def test_組み立てると_保存してある直前の買い目を読んで文に出す_推奨買目の合計は変えない(tmp_path: Path) -> None:
    store = LocalForecastStore(tmp_path)
    store.path(RID).parent.mkdir(parents=True)
    store.path(RID).write_text(json.dumps(_forecast("当日"), ensure_ascii=False), encoding="utf-8")
    message = LocalRaceMessage(store, _Schedule(), frames=_Frames(), jockeys=_Jockeys(), recommendations=_Recommendations())
    before = message.build(RID).text
    LateBetFile().write(store.late_path(RID), LATE)
    after = message.build(RID).text
    assert "直前の買い目" not in before and after.startswith(before)
    assert after.splitlines()[-3] == "直前の買い目（確かめ中・1点 100円）:"


def test_高知ファイナルの買い目は最後に出し_出せなければ理由_ファイルが無ければ出さない(tmp_path: Path) -> None:
    from 高知ファイナルの買い目.final_bet_file import FinalBetFile
    from 高知ファイナルの買い目.final_bets import FinalBets

    bets = FinalBets(5, (1, 2, 3), 1, {"単勝": ((5,),), "馬単": ((5, 1), (5, 2))}, 0.7, 0.85, "11051015")
    message = LocalRaceMessage()
    for title in ("当日", "前日"):                       # 時点を問わず出す
        lines = message.describe(message.card(_forecast(title), RACE, {}, RECOMMENDED, kochi_final=bets)).splitlines()
        assert lines[-5:] == ["高知ファイナルの予想（荒れる前提・確かめ中）（1点 100円・合計 3点 300円）:", "- ◎5 ○1 ▲2 △3（1番人気 1 は ◎ にしない）",
                              "- 単勝 5（1点 100円）", "- 馬単 5→1 / 5→2（2点 200円）",
                              "- 複勝・ワイド・3連複: 見送り（◎ の複勝の見込み 0.70。0.85 以上で買う）"]
    none = message.describe(message.card(_forecast("当日"), RACE, {}, kochi_final=FinalBets.none("時系列オッズの断面がまだ無い")))
    assert none.splitlines()[-1] == "高知ファイナルの予想（荒れる前提・確かめ中）: なし（時系列オッズの断面がまだ無い）"
    assert "高知ファイナル" not in message.describe(message.card(_forecast("当日"), RACE, {}))
    store = LocalForecastStore(tmp_path)
    store.path(RID).parent.mkdir(parents=True)
    store.path(RID).write_text(json.dumps(_forecast("当日"), ensure_ascii=False), encoding="utf-8")
    built = LocalRaceMessage(store, _Schedule(), frames=_Frames(), jockeys=_Jockeys(), recommendations=_Recommendations())
    before = built.build(RID).text
    FinalBetFile().write(store.kochi_final_path(RID), bets)
    after = built.build(RID).text
    assert "高知ファイナル" not in before and after.startswith(before) and "◎5 ○1 ▲2 △3" in after
