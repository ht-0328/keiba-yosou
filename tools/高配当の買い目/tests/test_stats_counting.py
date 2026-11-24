"""高配当の買い目の成績の数え方（``PickNumbers``・母数 ``RaceUniverse``・買い目の選び ``BacktestPicks``・5つの表）のテスト。

予測と買い目の表は架空の値。予想のパッケージは使わず、年ごとの予測の置き場と買い目の決まりは約束どおりの形の偽物を渡す。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from 高配当の買い目.backtest_picks import BacktestPicks
from 高配当の買い目.operation_table import OperationTable
from 高配当の買い目.period_table import PeriodTable
from 高配当の買い目.pick_columns import PICK_COLUMNS, TOTAL
from 高配当の買い目.pick_groups import PickGroups
from 高配当の買い目.pick_numbers import PickNumbers
from 高配当の買い目.race_universe import RaceUniverse
from 高配当の買い目.repository.race_universe_reader import RaceUniverseReader
from 高配当の買い目.repository.yearly_prediction_reader import YearlyPredictionReader
from 高配当の買い目.search_verify_periods import SearchVerifyPeriods
from 高配当の買い目.sensitivity_table import SensitivityTable
from 高配当の買い目.tests.fake_pick_rule import FakePickRule
from 高配当の買い目.tests.fake_prediction_store import FakePredictionStore
from 高配当の買い目.ticket_summary_table import TicketSummaryTable
from 高配当の買い目.year_table import YearTable


def _pick(race: str, day: str, ticket: str, combo: str, odds: float, payout: int, probability: float = 0.1) -> dict:
    return {"race_id": race, "race_date": pd.Timestamp(day), "ticket_type": ticket, "combo": combo, "odds": odds, "payout": payout,
            "hit": int(payout > 0), "probability": probability}


def _picks() -> pd.DataFrame:
    """4開催日・6レース・10点。開催日ごとの収支（1点 100円）は、
    2022-12-03: 3点で払戻 0 → −300、2022-12-04: 2点で払戻 1,200 → +1,000、2023-01-07: 3点で払戻 0 → −300、2023-01-08: 2点で払戻 0 → −200。"""
    return pd.DataFrame([
        _pick("A1", "2022-12-03", "ワイド", "0102", 12.0, 0), _pick("A1", "2022-12-03", "ワイド", "0103", 15.0, 0),
        _pick("A2", "2022-12-03", "馬連", "0102", 40.0, 0),
        _pick("B1", "2022-12-04", "ワイド", "0304", 12.0, 1200), _pick("B1", "2022-12-04", "馬連", "0304", 50.0, 0),
        _pick("C1", "2023-01-07", "ワイド", "0506", 20.0, 0), _pick("C1", "2023-01-07", "ワイド", "0507", 30.0, 0),
        _pick("C2", "2023-01-07", "馬連", "0506", 60.0, 0),
        _pick("D1", "2023-01-08", "ワイド", "0708", 11.0, 0), _pick("D1", "2023-01-08", "馬連", "0708", 35.0, 0),
    ], columns=list(PICK_COLUMNS))


def _universe() -> RaceUniverse:
    """全部で 20レース・5開催日（買い目の無い 2023-01-09 を含む）。期間は 2022-12-03 〜 2023-01-09 の 37日。"""
    days = ["2022-12-03"] * 4 + ["2022-12-04"] * 4 + ["2023-01-07"] * 4 + ["2023-01-08"] * 4 + ["2023-01-09"] * 4
    return RaceUniverse(pd.DataFrame({"race_id": [f"U{number:02d}" for number in range(20)], "race_date": pd.to_datetime(days)}))


def test_回収率と的中数と配当の中央は手計算と合う() -> None:
    numbers = PickNumbers(_picks())
    assert (numbers.points, numbers.hits, numbers.races, numbers.hit_races) == (10, 1, 6, 1)
    assert (numbers.stake, numbers.payout) == (1000, 1200.0)
    assert numbers.rate == pytest.approx(1.2) and numbers.points_per_race == pytest.approx(10 / 6)
    assert numbers.hit_race_share == pytest.approx(1 / 6) and numbers.median_multiple == pytest.approx(12.0)
    wide = PickNumbers(_picks()[_picks()["ticket_type"] == "ワイド"])
    assert (wide.points, wide.races, wide.rate) == (6, 4, pytest.approx(2.0))
    quinella = PickNumbers(_picks()[_picks()["ticket_type"] == "馬連"])
    assert quinella.rate == 0.0 and quinella.hit_days() == 0 and pd.isna(quinella.median_multiple)


def test_落ち込みは開催日の収支を足して_いちばん高い所からの下がり幅() -> None:
    # 収支の足し上げは −300 → +700 → +400 → +200。いちばん高い 700 から 200 まで 500 下がる（始めの 0 から −300 の下がりより大きい）
    assert PickNumbers(_picks()).drawdown() == pytest.approx(500.0)
    # 始めから下がり続ける買い目は、始めの 0 円からの下がり幅（馬連は 4点とも外れで −400）
    assert PickNumbers(_picks()[_picks()["ticket_type"] == "馬連"]).drawdown() == pytest.approx(400.0)
    assert PickNumbers(_picks().iloc[0:0]).drawdown() == 0.0


def test_外れ続きは_買ったレースを古い順に並べて外れの続いた最長の数() -> None:
    # レースの順は A1・A2（外れ）→ B1（当たり）→ C1・C2・D1（外れ）。最長は 3
    assert PickNumbers(_picks()).longest_miss() == 3
    # 1点も当たらなければ、買ったレースの数
    assert PickNumbers(_picks()[_picks()["ticket_type"] == "馬連"]).longest_miss() == 4
    assert PickNumbers(_picks().iloc[0:0]).longest_miss() == 0
    by_day = PickNumbers(_picks()).by_day()
    assert by_day["profit"].tolist() == [-300.0, 1000.0, -300.0, -200.0] and PickNumbers(_picks()).hit_days() == 1


def test_母数は馬ごとの表のレースで_予測のある年にそろえる(tmp_path: Path) -> None:
    for name, days in (("2021-2022", ["2021-06-05", "2022-12-03", "2022-12-03"]), ("2023-2023", ["2023-01-07"])):
        # 1レースに2頭（1頭1行）
        table = pd.DataFrame({"race_id": [f"{name}{at}" for at in range(len(days))] * 2, "race_date": pd.to_datetime(days * 2),
                              "horse_no": [1] * len(days) + [2] * len(days)})
        table.to_parquet(tmp_path / f"{name}.parquet", index=False)
    universe = RaceUniverseReader(tmp_path).read()
    assert (universe.race_count, universe.day_count) == (4, 3)   # 1頭1行の表でも、レースは1回だけ数える
    recent = universe.of_years({2022, 2023})
    assert (recent.race_count, recent.day_count) == (3, 2) and recent.period_text() == "2022-12-03 〜 2023-01-07"
    assert recent.year_span == pytest.approx(35 / 365.25)
    with pytest.raises(FileNotFoundError, match="horses.py"):
        RaceUniverseReader(tmp_path / "無い").read()


def _backtest(tmp_path: Path) -> BacktestPicks:
    """ワイドの予測が 2022年と 2023年、馬連の予測が 2023年だけ。期待値は 確率 × オッズ。使わない列（モデルごとの確率）もファイルにはある。"""
    wide_2022 = [_pick("A1", "2022-12-03", "ワイド", "0102", 12.0, 0, 0.10), _pick("A1", "2022-12-03", "ワイド", "0103", 15.0, 1500, 0.08),
                 _pick("A1", "2022-12-03", "ワイド", "0104", 20.0, 0, 0.051), _pick("A1", "2022-12-03", "ワイド", "0105", 5.0, 0, 0.50)]
    wide_2023 = [_pick("C1", "2023-01-07", "ワイド", "0506", 20.0, 0, 0.06), _pick("C1", "2023-01-07", "ワイド", "0507", 30.0, 0, 0.03)]
    quinella_2023 = [_pick("C1", "2023-01-07", "馬連", "0506", 40.0, 4000, 0.03)]
    for name, rows in (("wide_2022", wide_2022), ("wide_2023", wide_2023), ("quinella_2023", quinella_2023)):
        pd.DataFrame(rows).assign(probability_lightgbm=0.0).to_parquet(tmp_path / f"{name}.parquet", index=False)
    return BacktestPicks(YearlyPredictionReader(FakePredictionStore(tmp_path)), FakePickRule, (TicketType.WIDE, TicketType.QUINELLA))


def test_候補は一番低い線で1回だけ選び_決まりごとの買い目は候補から選び直す(tmp_path: Path) -> None:
    backtest = _backtest(tmp_path)
    assert backtest.years() == {2022, 2023}
    candidates = backtest.candidates(1.0)
    assert list(candidates.columns) == list(PICK_COLUMNS)
    # 期待値は 0102 が 1.2、0103 が 1.2、0104 が 1.02、0105 が 2.5（線より安い）、0506 が 1.2、0507 が 0.9、馬連 0506 が 1.2
    assert sorted(zip(candidates["ticket_type"], candidates["combo"])) == [("ワイド", "0102"), ("ワイド", "0103"), ("ワイド", "0104"),
                                                                           ("ワイド", "0506"), ("馬連", "0506")]
    default = backtest.select(candidates, 1.05, None)
    assert sorted(default["combo"]) == ["0102", "0103", "0506", "0506"]
    capped = backtest.select(candidates, 1.0, 1)   # 1レース・1券種につき確率のいちばん高い組だけ
    assert sorted(zip(capped["ticket_type"], capped["combo"])) == [("ワイド", "0102"), ("ワイド", "0506"), ("馬連", "0506")]
    # 候補から選び直しても、予測の全部から同じ決まりで選んだものと同じ
    assert backtest.select(candidates, 1.05, 1).reset_index(drop=True).equals(
        backtest.select(backtest.candidates(1.05), 1.05, 1).reset_index(drop=True))
    with pytest.raises(FileNotFoundError, match="walk"):
        BacktestPicks(YearlyPredictionReader(FakePredictionStore(tmp_path)), FakePickRule, (TicketType.TRIO,)).candidates(1.0)


def test_券種ごとの表と年ごとの表と期間ごとの表() -> None:
    groups = PickGroups(("ワイド", "馬連", "3連複"))
    summary = TicketSummaryTable(_universe(), groups).table(_picks(), "決まり")
    assert [row[0] for row in summary.rows] == ["ワイド", "馬連", "3連複", TOTAL]
    # ワイドは 4レース（全 20レースの 20.0%）・6点（1レース 1.5点）・的中 1（買ったレースの 25.0%）・配当の中央 12.0倍・回収率 200.0%
    assert summary.rows[0][:9] == ["ワイド", "4", "20.0%", "1.5", "6", "1", "25.0%", "12.0", "200.0%"]
    assert summary.rows[1][:9] == ["馬連", "4", "20.0%", "1.0", "4", "0", "0.0%", "-", "0.0%"]
    assert summary.rows[2] == ["3連複", "0", "0.0%", "-", "0", "0", "-", "-", "-", "-"]   # 買った点の無い券種は 0 の行
    assert summary.rows[3][:9] == [TOTAL, "6", "30.0%", "1.7", "10", "1", "16.7%", "12.0", "120.0%"]
    assert "〜" in summary.rows[3][9] and summary.note == "決まり"
    years = YearTable(groups).table(_picks(), [2022, 2023], "")
    assert years.columns == ["券種", "2022年", "2023年"]
    assert years.rows == [["ワイド", "400.0%（1）", "0.0%（0）"], ["馬連", "0.0%（0）", "0.0%（0）"], ["3連複", "-（0）", "-（0）"],
                          [TOTAL, "240.0%（1）", "0.0%（0）"]]
    periods = PeriodTable(groups, SearchVerifyPeriods(2022)).table(_picks(), "")
    assert periods.columns[1:] == ["探す期間（〜2022年）の点数", "探す期間（〜2022年）の的中数", "探す期間（〜2022年）の回収率",
                                   "確かめる期間（2023年〜）の点数", "確かめる期間（2023年〜）の的中数", "確かめる期間（2023年〜）の回収率"]
    assert periods.rows[0] == ["ワイド", "3", "1", "400.0%", "3", "0", "0.0%"]
    assert periods.rows[3] == [TOTAL, "5", "1", "240.0%", "5", "0", "0.0%"]


def test_運用の目安は_買い目の無い開催日も数えた1開催日あたりと_期間の長さで割った1年あたり() -> None:
    table = OperationTable(_universe(), PickGroups(("ワイド", "馬連"))).table(_picks(), "")
    total = dict(zip(table.columns, table.rows[2]))
    # 5開催日・37日（37 ÷ 365.25 年）。6レース・10点・投資 1,000円・収支 +200円・的中 1本（当たった開催日は 1日）
    assert total["券種"] == TOTAL and total["1開催日の買うレース"] == "1.2" and total["1開催日の点数"] == "2.0" and total["1開催日の金額"] == "200円"
    years = 37 / 365.25
    assert total["1年の投資"] == f"{1000 / years:,.0f}円" and total["1年の収支"] == f"{200 / years:+,.0f}円"
    assert total["いちばん深い落ち込み"] == "500円" and total["外れが続いた最長のレース数"] == "3"
    assert total["高配当が1本以上当たった開催日の割合"] == "20.0%" and total["1開催日の的中の平均"] == "0.20"
    quinella = dict(zip(table.columns, table.rows[1]))
    assert quinella["いちばん深い落ち込み"] == "400円" and quinella["外れが続いた最長のレース数"] == "4" and quinella["1年の収支"].startswith("-")


def test_線の感度の表は_期待値の線と上限の点数ごとに選び直した成績を並べる(tmp_path: Path) -> None:
    backtest = _backtest(tmp_path)
    table = SensitivityTable(backtest, PickGroups(("ワイド", "馬連")), SearchVerifyPeriods(2022)).table(backtest.candidates(1.0), "")
    assert len(table.rows) == 4 * 4 * 3   # 線 4つ × 上限 4つ ×（券種 2つ + 合計）
    by_key = {(row[0], row[1], row[2]): row[3:] for row in table.rows}
    # 線 1.00・上限なし: ワイドは 0102・0103・0104（2022年。払戻 1,500）と 0506（2023年）の 4点
    assert by_key[("1.00", "なし", "ワイド")] == ["4", "1", "500.0%", "0.0%", "375.0%"]
    # 線 1.05 では 0104（期待値 1.02）が落ちる。上限 1点では、2022年は確率のいちばん高い 0102（外れ）だけが残る
    assert by_key[("1.05", "なし", "ワイド")] == ["3", "1", "750.0%", "0.0%", "500.0%"]
    assert by_key[("1.05", "3", "合計")] == ["4", "2", "750.0%", "2000.0%", "1375.0%"]
    assert by_key[("1.10", "なし", "合計")] == ["4", "2", "750.0%", "2000.0%", "1375.0%"]
    assert by_key[("1.00", "3", "ワイド")][0] == "4"
