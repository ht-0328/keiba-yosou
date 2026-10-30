"""DaySummary（1開催日のまとめ）・SummaryStore（まとめ.md）・summary.py（道具）のテスト。値は架空。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pytest

from 今週の予想 import summary
from 今週の予想.day_summary import NO_PLAN_TEXT, NOTHING_FEATURED_TEXT, DaySummary
from 今週の予想.forecast_store import ForecastStore
from 今週の予想.plan_store import PlanStore
from 今週の予想.race_plan import PlacePick, RacePlan
from 今週の予想.summary_store import SummaryStore
from 今週の予想.tests.test_forecast_store import sample_forecast

DAY = date(2025, 4, 19)
TOKYO_1R, TOKYO_11R, KYOTO_5R = "2025041905010101", "2025041905010111", "2025041908010105"
WALLET = {"勝負用": 100000, "ポリシー用": 30000, "単勝・馬単用": 100000, "組の期待値用": 500000,
          "予算": {"勝負": 5000, "ノルマ（重賞）": 900, "ノルマ（日）": 400}, "1点": 1600, "単勝・馬単の1点": {"単勝": 300, "馬単": 0},
          "組の期待値の1点": {"馬連": 500, "ワイド": 100}}


def _forecast(rid: str, venue: str, number: int, name: str, klass: str, made_at: str) -> dict:
    forecast = sample_forecast(rid)
    forecast["title"] = f"2025-04-19（土） {venue} {number}R {name}（{klass} 芝・左 1200m 16頭 09:50 出馬表）"
    forecast["header"] = {"rid": rid, "競馬場": venue, "R": number, "レース名": name, "クラス": klass, "コース": "芝・左", "距離": 1200,
                          "頭数": 16, "発走": "09:50", "状態": "出馬表"}
    forecast["horses"].append({**forecast["horses"][0], "rank": 2, "mark": "○", "horse_no": 7, "horse_name": "馬B", "is_danger": False})
    forecast["horses"].append({**forecast["horses"][0], "rank": 3, "mark": "▲", "horse_no": 2, "horse_name": "馬C", "is_danger": False})
    forecast["horses"].append({**forecast["horses"][0], "rank": 4, "mark": "消", "horse_no": 9, "horse_name": "馬D", "is_danger": True})
    forecast["made_at"] = made_at
    return forecast


def _store(tmp_path: Path, *, with_plan: bool = True) -> ForecastStore:
    """東京 1R（勝負 1,600円）・東京 11R（重賞。ノルマ 300円）・京都 5R（買わない）の3レースと、計画。rid の順に並ばないように書く。"""
    store = ForecastStore(tmp_path)
    forecasts = [_forecast(KYOTO_5R, "京都", 5, "", "新馬", "2025-04-18T20:05:00"),
                 _forecast(TOKYO_11R, "東京", 11, "テスト記念", "G3", "2025-04-18T20:03:00"),
                 _forecast(TOKYO_1R, "東京", 1, "", "未勝利", "2025-04-18T20:01:00")]
    for forecast in forecasts:
        store.save(forecast)
    if with_plan:
        plans = [RacePlan(TOKYO_1R, forecasts[2]["title"], "前日", "勝負", "見込みの利益 E = 0.30単位 > 0", 0.3, 1.05, False, (PlacePick(3, 0.42, 1.05, 1.5, 1600),), 5000),
                 RacePlan(TOKYO_11R, forecasts[1]["title"], "前日", "ノルマ（重賞）", "平地の重賞", 0.0, 1.05, True, (PlacePick(3, 0.42, 1.05, 1.5, 300),), 900),
                 RacePlan(KYOTO_5R, forecasts[0]["title"], "前日", "買わない", "期待値が線に届かない", 0.0, 0.9, False)]
        PlanStore(store).save(DAY, plans, WALLET)
    return store


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def test_保存してある結果は開催日ごとに_rid_の順で読め_計画のファイルは含めない(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert [forecast["rid"] for forecast in store.load_day(DAY)] == [TOKYO_1R, TOKYO_11R, KYOTO_5R]
    assert store.load_day(date(2025, 4, 20)) == []


def test_まとめは_見出し_一覧_買うレース_競馬場ごとのレースの順で_一覧は_rid_の順(tmp_path: Path) -> None:
    text = DaySummary(_store(tmp_path)).markdown(DAY)
    assert text.startswith("# 2025-04-19（土） の予想のまとめ\n\n- 予想 3 レース（前日 3）。作った時刻 2025-04-18 20:05（いちばん新しいもの）\n"
                           "- 実際に買う: 2 レース・合計 1,900円（計画は同じフォルダの plan.json）\n")
    assert text.index("## 一覧") < text.index("## 買うレース") < text.index("## 東京") < text.index("## 京都")
    rows = [line for line in text.splitlines() if line.startswith("| 東京") or line.startswith("| 京都")]
    assert [_cells(row)[0] for row in rows] == ["東京 1R", "東京 11R", "京都 5R"]
    assert _cells(rows[0]) == ["東京 1R", "未勝利", "芝・左 1200m 16頭", "09:50", "前日", "A（23%）", "A（56%）", "3 馬A（1人気 3.1倍）", "7 馬B", "2 馬C", "9 馬D",
                               "複勝（勝負）1,600円"]
    assert _cells(rows[1])[1] == "テスト記念（G3）" and _cells(rows[1])[-1] == "複勝（ノルマ（重賞））300円"
    assert _cells(rows[2])[-1] == "買わない"
    # 買うレースの表は計画の表と同じ列で、題は付けない（見出しがあるので）
    assert "| レース | 時点 | 参加の種類 | E（単位） | M |" in text and "### 買うレース" not in text and "この日の合計 1,900円" in text
    # レースの文は3つ（東京 1R・東京 11R・京都 5R の順）
    titles = [line for line in text.splitlines() if line.startswith("### ")]
    assert len(titles) == 3 and text.index("### 2025-04-19（土） 東京 1R") < text.index("### 2025-04-19（土） 東京 11R") < text.index("### 2025-04-19（土） 京都 5R")
    assert "- 複勝（勝負）: 3 馬A（期待値 1.05、1,600円）  合計 1,600円" in text
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_短い版は一覧と買うレースのあと_重賞と実際に買うレースの文だけ(tmp_path: Path) -> None:
    text = DaySummary(_store(tmp_path)).markdown(DAY, brief=True)
    assert "## 一覧" in text and "## 買うレース" in text and "## 東京" in text
    # 京都 5R は買わないので文が無い（買うレースの表の行には残る）
    assert "## 京都" not in text and "### 2025-04-19（土） 京都 5R" not in text
    assert len([line for line in text.splitlines() if line.startswith("### ")]) == 2


def test_計画が無い日は_計画なしと書き_買う列は空で_短い版は重賞の文だけ(tmp_path: Path) -> None:
    store = _store(tmp_path, with_plan=False)
    text = DaySummary(store).markdown(DAY)
    assert f"- {NO_PLAN_TEXT}" in text and text.count(NO_PLAN_TEXT) == 2 and "- 実際に買う:" not in text
    rows = [line for line in text.splitlines() if line.startswith("| 東京 1R")]
    assert _cells(rows[0])[-1] == ""
    brief = DaySummary(store).markdown(DAY, brief=True)
    assert [line for line in brief.splitlines() if line.startswith("### ")] == [line for line in brief.splitlines() if "テスト記念" in line and line.startswith("### ")]
    # 重賞も買うレースも無い日の短い版
    for rid in (TOKYO_11R,):
        (tmp_path / DAY.isoformat() / f"{rid}.json").unlink()
    assert NOTHING_FEATURED_TEXT in DaySummary(store).markdown(DAY, brief=True)


def test_枠順の無い木曜の予想は一覧に馬名だけを書く(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    forecast = _forecast(TOKYO_1R, "東京", 1, "", "未勝利", "2025-04-16T18:00:00")
    forecast["timing"] = "木曜"
    for horse in forecast["horses"]:
        horse.update(horse_no=None, popularity=None, win_odds=None)
    store.save(forecast)
    text = DaySummary(store).markdown(DAY)
    row = next(line for line in text.splitlines() if line.startswith("| 東京 1R"))
    assert _cells(row)[4:] == ["木曜", "A（23%）", "A（56%）", "馬A", "馬B", "馬C", "馬D", ""]


def test_予想が無い日は_無いと書く(tmp_path: Path) -> None:
    assert DaySummary(ForecastStore(tmp_path)).markdown(DAY) == "# 2025-04-19（土） の予想のまとめ\n\n（予想がありません）\n"


def test_まとめの保存は_まとめ_md_に書いて読み戻せる(tmp_path: Path) -> None:
    store = SummaryStore(ForecastStore(tmp_path))
    assert store.load(DAY) is None
    path = store.save(DAY, "# まとめ\n")
    assert path == tmp_path / "2025-04-19" / "まとめ.md" and store.load(DAY) == "# まとめ\n"
    assert path.read_bytes().endswith(b"\n") and b"\r\n" not in path.read_bytes()


def test_道具は_date_の日のまとめを_out_に書き_まとめ_md_も書く(tmp_path: Path) -> None:
    _store(tmp_path)
    out = tmp_path / "出力.md"
    summary.main(argparse.Namespace(date=DAY, brief=False, out_dir=tmp_path, out=out))
    assert out.read_text(encoding="utf-8").startswith("# 2025-04-19（土） の予想のまとめ")
    assert (tmp_path / "2025-04-19" / "まとめ.md").read_text(encoding="utf-8") == out.read_text(encoding="utf-8")
    # 短い版はまとめ.md を書き換えない
    (tmp_path / "2025-04-19" / "まとめ.md").write_text("x", encoding="utf-8")
    summary.main(argparse.Namespace(date=DAY, brief=True, out_dir=tmp_path, out=out))
    assert (tmp_path / "2025-04-19" / "まとめ.md").read_text(encoding="utf-8") == "x" and "## 京都" not in out.read_text(encoding="utf-8")
    with pytest.raises(LookupError, match="2025-04-20 の予想がありません"):
        summary.main(argparse.Namespace(date=date(2025, 4, 20), brief=False, out_dir=tmp_path, out=None))
