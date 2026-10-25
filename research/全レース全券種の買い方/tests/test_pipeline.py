"""数え上げ・選ぶ・確かめる・事例・比べる相手の部品のテスト。値は架空。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from 全レース全券種の買い方.analysis.baseline_tickets import BaselineTickets  # noqa: E402
from 全レース全券種の買い方.analysis.candidate_counter import CandidateCounter  # noqa: E402
from 全レース全券種の買い方.analysis.cases_report import CasesReport  # noqa: E402
from 全レース全券種の買い方.analysis.cell_selector import CellChoice, CellSelector  # noqa: E402
from 全レース全券種の買い方.analysis.choice_summary import ChoiceSummary  # noqa: E402
from 全レース全券種の買い方.analysis.combos_source import CombosSource  # noqa: E402
from 全レース全券種の買い方.analysis.day_table import PAYOUT, POINTS  # noqa: E402
from 全レース全券種の買い方.analysis.formation import Formation  # noqa: E402
from 全レース全券種の買い方.analysis.grades_table import GradesTable  # noqa: E402
from 全レース全券種の買い方.analysis.horse_slots import HorseSlots  # noqa: E402

DAYS = [pd.Timestamp("2025-01-05"), pd.Timestamp("2025-01-06")]


class _Source:
    """組の表の代わり。1年に2レース（A: 2025-01-05 セル S/A、B: 2025-01-06 セル B/C）。"""

    def load(self, label: str, year: int) -> pd.DataFrame:
        return pd.DataFrame({
            "race_id": ["A", "A", "B", "B"], "race_date": [DAYS[0], DAYS[0], DAYS[1], DAYS[1]], "cell": ["S/A", "S/A", "B/C", "B/C"],
            "value": [1.2, 0.8, 1.5, 0.5], "odds": [3.0, 10.0, 4.0, 20.0], "payout": [300.0, 0.0, 0.0, 0.0], "pos1": [0.0, 1.0, 0.0, 2.0],
        })


def test_数え上げは候補ごとにセルと開催日の配列にして保存と読み戻しができる(tmp_path: Path) -> None:
    formations = [Formation(1, 2), Formation(3, 2, value_line=1.0)]
    counter = CandidateCounter(_Source(), "単勝", formations, ["S/A", "B/C"], DAYS)
    values = counter.count([2025])
    assert values.shape == (2, 2, 2, 4)
    # 候補1（◎ だけ）: A は ◎ の1点（当たり 300円）、B は ◎ の1点（外れ）
    assert values[0, 0, 0, POINTS] == 1 and values[0, 0, 0, PAYOUT] == 300 and values[0, 1, 1, POINTS] == 1
    # 候補2（◎○▲・期待値 1.0 以上）: A は 1.2 の1点、B は 1.5 の1点
    assert values[1, 0, 0, POINTS] == 1 and values[1, 1, 1, POINTS] == 1
    path = counter.save(tmp_path / "単勝.npz")
    loaded, cells, days, labels = CandidateCounter.load(path)
    assert np.array_equal(loaded, values) and cells == ["S/A", "B/C"] and days == DAYS and labels[0] == formations[0].label


def test_セルごとに当たりが足りる候補から下の端がいちばん高い型を選ぶ() -> None:
    days = 40
    values = np.zeros((2, 1, days, 4))
    values[:, 0, :, 0] = 1            # 毎日1点
    values[:, 0, :, 2] = 1            # 毎日1レース
    values[0, 0, :, 1] = 120          # 候補0: 毎日 120円 の払戻（当たり 40）
    values[0, 0, :, 3] = 1
    values[1, 0, :5, 1] = 2000        # 候補1: 5日だけ 2000円（当たり 5。合計は高いが当たり不足）
    values[1, 0, :5, 3] = 1
    choices = CellSelector(["型0", "型1"], ["S/A"]).select(values, np.ones(days, dtype=bool))
    assert choices[0].index == 0 and choices[0].enough and choices[0].hits == 40 and choices[0].recovery == pytest.approx(1.2)
    table = CellSelector(["型0", "型1"], ["S/A"]).table(values, np.ones(days, dtype=bool))
    assert list(table["型"]) == ["型0", "型1"] and table.loc[1, "当たったレース"] == 5


def test_二回目は下の端が届かないセルを同じ型の1点に落とす() -> None:
    formations = [Formation(1, 2), Formation(1, 2, max_points=1), Formation(2, 2), Formation(2, 2, max_points=1)]
    days = 40
    values = np.zeros((4, 2, days, 4))
    values[:, :, :, 0] = 1
    values[:, :, :, 2] = 1
    values[:, :, :, 3] = 1
    values[0, 0, :, 1] = 130     # セル0: 型0（12点）が毎日 130円 → 下の端 100% 超え
    values[2, 0, :, 1] = 90
    values[0, 1, :, 1] = 90      # セル1: どちらも届かない → 1点に落とす
    values[2, 1, :, 1] = 95
    selector = CellSelector([formation.label for formation in formations], ["S/A", "B/C"], formations=formations, token=True)
    choices = selector.select(values, np.ones(days, dtype=bool))
    assert choices[0].index == 0 and not choices[0].token
    assert choices[1].index == 3 and choices[1].token and choices[1].label.endswith("1点まで") and choices[1].recovery == pytest.approx(0.95)


def test_三回目は2倍以下のセルで単複を買わず_馬単は二重丸頭固定の型から選ぶ() -> None:
    formations = [Formation(1, 2), Formation(1, 2, max_points=1), Formation(2, 2), Formation(2, 2, max_points=1)]
    days = 40
    values = np.zeros((4, 2, days, 4))
    values[:, :, :, 0] = 1
    values[:, :, :, 2] = 1
    values[:, :, :, 3] = 1
    values[0, :, :, 1] = 110    # 型0（◎ 軸）は 110%、型2（◎○ 軸）は 130% だが、2倍以下のセルでは ◎ 軸だけが候補
    values[2, :, :, 1] = 130
    labels = [formation.label for formation in formations]
    allowed = lambda cell, formation: formation.axis_size == 1 if cell.endswith("/2倍以下") else True  # noqa: E731
    choices = CellSelector(labels, ["S/A", "S/2倍以下"], formations=formations, token=True, allowed=allowed).select(values, np.ones(days, dtype=bool))
    assert choices[0].index == 2 and choices[1].index == 0 and not choices[1].skip
    skipped = CellSelector(labels, ["S/A", "S/2倍以下"], formations=formations, token=True, skip_cells=["S/2倍以下"]).select(values, np.ones(days, dtype=bool))
    assert skipped[1].skip and ChoiceSummary.selected(values, skipped)[1].sum() == 0 and ChoiceSummary.selected(values, skipped)[0, 0, 1] == 130


def test_選んだ型の成績と採用の基準() -> None:
    days = [pd.Timestamp(f"{year}-01-05") for year in range(2019, 2027)]
    values = np.zeros((1, 1, len(days), 4))
    values[0, 0, :, 0] = 10
    values[0, 0, :, 2] = 10
    values[0, 0, :, 1] = [1200, 1100, 900, 1300, 1200, 1100, 1000, 1200]
    values[0, 0, :, 3] = 2
    choices = [CellChoice("S/A", 0, "型0", 1.0, 1.0, 16, 80, 1.0, True)]
    summary_of = ChoiceSummary(days)
    selected = ChoiceSummary.selected(values, choices)
    summary = summary_of.summary(selected, np.ones(len(days), dtype=bool))
    assert summary["回収率"] == pytest.approx(9000 / 8000) and summary["的中率"] == pytest.approx(0.2) and summary["1レースの点数"] == 1.0
    yearly = summary_of.yearly(selected)
    assert list(yearly["年"]) == list(range(2019, 2027)) and yearly.loc[2, "回収率"] == pytest.approx(0.9)
    passed, reason = ChoiceSummary.passes(summary, yearly)
    assert "100% 超えの年 6/8" in reason and passed == (summary["下の端"] > 1.0)


def test_事例の表はセルごとに二重丸の着順と印の内訳を出す() -> None:
    marked = pd.DataFrame({
        "race_id": ["R"] * 4, "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半", "horse_no": [1, 2, 3, 4],
        "mark": ["◎", "○", "▲", "－"], "probability": [0.5, 0.4, 0.3, 0.1], "win_probability": [0.5, 0.2, 0.1, 0.05], "win_value": [1.1, 0.9, 0.8, 0.5],
        "win_odds": [2.2, 4.5, 8.0, 10.0],
        "finish": [1.0, 3.0, 5.0, 2.0],
    })
    slots = HorseSlots().build(marked)
    grades = GradesTable().build(marked, pd.DataFrame({"race_id": ["R"], "payout_rate": [0.6]}))
    table = CasesReport().table(marked, slots, grades).set_index("セル")
    assert table.loc["S/A", "◎1着"] == 1.0 and table.loc["S/A", "◎○▲が2頭以上"] == 1.0 and table.loc["S/A", "◎○▲で決着"] == 0.0
    assert table.loc["S/A", "無印"] == 1.0 and table.loc["全部", "レース"] == 1


def test_比べる相手は今の印の買い目を開催日ごとにまとめる(tmp_path: Path) -> None:
    csv = tmp_path / "買い目.csv"
    pd.DataFrame({
        "レースID": ["A", "A", "B", "B"], "開催日": ["2025-01-05", "2025-01-05", "2025-01-05", "2025-01-06"], "買い方": ["単勝", "馬連", "単勝", "3連単（◎軸・マルチ）"],
        "払戻（100円あたり）": [500.0, 0.0, 0.0, 900.0], "外した理由": [None, "トリガミ", None, None],
    }).to_csv(csv, index=False)
    summary = BaselineTickets().summarize(csv)
    assert set(summary["券種"]) == {"単勝"}   # 馬連はトリガミで外れ、3連単（◎軸・マルチ）は比べる相手の買い方ではない
    row = summary.iloc[0]
    assert (row["points"], row["payout"], row["races"], row["hits"]) == (2, 500.0, 2, 1)


def test_単勝と枠連の組の表は位置とセルが付く() -> None:
    marked = pd.DataFrame({
        "race_id": ["R"] * 3, "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半", "horse_no": [1, 2, 3], "mark": ["◎", "○", "消"],
        "probability": [0.5, 0.4, 0.3], "win_probability": [0.5, 0.2, 0.1], "win_value": [1.1, 0.9, 0.8], "win_odds": [3.0, 5.0, 6.0], "win_payout": [300.0, 0.0, 0.0],
        "place_value": [1.0, 1.0, 1.0], "place_odds_low": [1.5, 2.0, 2.0], "place_payout": [150.0, 0.0, 0.0],
    })
    slots = HorseSlots().build(marked)
    grades = GradesTable().build(marked, None)
    bracket = pd.DataFrame({"race_id": ["R", "R"], "race_date": pd.Timestamp("2025-01-05"), "h1": [1, 1], "h2": [2, 3], "odds": [5.0, 9.0],
                            "payout": [500.0, 0.0], "value": [1.1, 0.7]})
    frames = pd.DataFrame({"race_id": ["R"] * 3, "horse_no": [1, 2, 3], "frame": [1, 2, 3]})
    source = CombosSource(Path("combos"), marked, pd.DataFrame(), {}, slots, grades, bracket=bracket, frames=frames)
    single = source.load("単勝", 2025)
    assert single["pos1"].tolist() == [0.0, 1.0] + [np.nan] * 0 or single["pos1"].isna().sum() == 1
    assert single.loc[single["h1"] == 1, "payout"].iloc[0] == 300.0 and (single["cell"] == "S/－").all()
    pair = source.load("枠連", 2025)
    assert pair["pos1"].tolist() == [0.0, 0.0] and pair["pos2"].tolist()[0] == 1.0 and np.isnan(pair["pos2"].tolist()[1])
