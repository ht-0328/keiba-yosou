"""絞り込み（2モデル一致・3連単の支持）・場面の帯・オッズの動きと、それを読む部品のテスト（研究「回収率100超の施策」）。

値は架空。DB は合成DB だけを使う。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from 共通 import keys
from 合成DB import synth

from 印の成績.backtest_marker import BacktestMarker
from 今週の予想.filter_columns import AGREEMENT, ODDS_MOVE, POOL_BACKED, POOL_SUPPORT, POOL_WIN
from 今週の予想.mark_tickets import RULE, VALUE, MarkTickets
from 印の成績.movement_report import ALL_LABEL, MovementReport
from 印の成績.odds_snapshot_repository import OddsSnapshotRepository
from 印の成績.pool_win_reader import PoolWinReader
from 印の成績.prediction_file import PredictionFile
from 印の成績.race_filters import ALL_RACES, HIGH_AGREE, HIGH_AGREE_POOL, HIGH_DISAGREE, HIGH_POOL, HIGH_RACES, RaceFilter
from 印の成績.race_scene_repository import RaceSceneRepository
from 印の成績.scene_bands import CLASS_AXIS, FIELD_AXIS, POOL_AXIS, SURFACE_AXIS, VENUE_AXIS, SceneBands
from 印の成績.scene_report import SceneReport
from 印の成績.ticket_payouts import ODDS, PAYOUT
from 今週の予想.ticket_rules import PLACE_AGREE_LABEL, PLACE_LABEL
from 今週の予想.torigami_filter import DROPPED
from 印の成績.win_pool_size_repository import WIN_POOL, WinPoolSizeRepository
from 印の成績.win_value_attacher import WinValueAttacher


def _prediction_rows(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{"レースID": row["race"], "開催日": pd.Timestamp("2025-01-05"), "馬ID": row["horse"], "馬番": row.get("no", 1),
                          "LightGBM": row.get("lgb", row["p"]), "CatBoost": row.get("cat", row["p"]), "確率": row["p"],
                          "区切り": "2025年前半", "期間": row.get("period", "テスト"), "区分": "全体"} for row in rows])


def test_予測の読み込みはモデルごとの確率も残す(tmp_path: Path) -> None:
    folder = tmp_path / "predictions"
    (folder / "form").mkdir(parents=True)
    _prediction_rows([{"race": 1, "horse": 10, "p": 0.3, "lgb": 0.25, "cat": 0.35}]).to_pickle(folder / "form" / "new.pkl")
    loaded = PredictionFile("form/new", folder).load()
    assert loaded.loc[0, "probability_lightgbm"] == 0.25 and loaded.loc[0, "probability_catboost"] == 0.35
    # モデルごとの列の無い古いファイルも読める
    _prediction_rows([{"race": 1, "horse": 10, "p": 0.3}]).drop(columns=["LightGBM", "CatBoost"]).to_pickle(folder / "form" / "old.pkl")
    assert "probability_lightgbm" not in PredictionFile("form/old", folder).load().columns


def test_単勝の期待値はモデルごとにも付ける() -> None:
    table = PredictionFile.__new__(PredictionFile)  # noqa: F841  読み込みは上のテストで確かめているので、表を直に作る
    rows = _prediction_rows([{"race": "T", "horse": "t1", "no": 1, "p": 0.3, "lgb": 0.2, "cat": 0.4}])
    rows = rows.rename(columns={"レースID": "race_id", "開催日": "race_date", "馬ID": "horse_id", "馬番": "horse_no", "確率": "probability",
                                "LightGBM": "probability_lightgbm", "CatBoost": "probability_catboost", "区切り": "fold", "期間": "period",
                                "区分": "segment"}).astype({"race_id": str, "horse_id": str})
    wins = WinValueAttacher().attach(rows, rows[["race_id", "horse_id"]].assign(win_odds=5.0)).iloc[0]
    assert wins["win_value"] == pytest.approx(1.5)
    assert wins["win_value_lightgbm"] == pytest.approx(1.0) and wins["win_value_catboost"] == pytest.approx(2.0)
    assert wins["win_probability_catboost"] == pytest.approx(0.4)


def _results() -> pd.DataFrame:
    return pd.DataFrame({"race_id": ["R"] * 4, "horse_id": ["a", "b", "c", "d"], "horse_no": [1, 2, 3, 4],
                         "finish": [2.0, 1.0, 3.0, 4.0], "win_odds": [2.0, 3.0, 6.0, 20.0], "popularity": [1.0, 2.0, 3.0, 4.0],
                         "win_payout": [0, 300, 0, 0], "place_payout": [120, 150, 200, 0], "field_size": [4] * 4,
                         "place_odds_low": [1.1, 1.3, 1.8, 4.0], "place_odds_high": [1.3, 1.6, 2.4, 6.0]})


def test_二重丸の期待値が2つのモデルでも線以上なら2モデル一致で3連単の支持も付ける() -> None:
    predictions = pd.DataFrame({"race_id": ["R"] * 4, "race_date": pd.Timestamp("2025-01-05"), "horse_id": ["a", "b", "c", "d"],
                                "probability": [0.7, 0.5, 0.3, 0.1], "probability_lightgbm": [0.7, 0.5, 0.3, 0.1],
                                "probability_catboost": [0.7, 0.5, 0.3, 0.1], "fold": "2025年前半"})
    dangers = pd.DataFrame(columns=["race_id", "horse_id", "is_danger"])
    marker = BacktestMarker(None)
    places = marker.places(_results())
    # ◎ は c（期待値 1.2）。LightGBM では 1.3、CatBoost では 1.1 → どちらも 1.00 以上なので一致
    wins = pd.DataFrame({"race_id": ["R"] * 4, "horse_id": ["a", "b", "c", "d"], "win_probability": [0.5, 0.3, 0.2, 0.02],
                         "win_value": [1.0, 0.9, 1.2, 0.4], "win_value_lightgbm": [1.0, 0.9, 1.3, 0.4], "win_value_catboost": [1.0, 0.9, 1.1, 0.4]})
    # 3連単から見た勝率: c は単勝から見た勝率より高い（支持あり）
    market_win = places.set_index("horse_id")["オッズから見た勝率"]
    pools = pd.DataFrame({"race_id": ["R"] * 4, "horse_no": [1, 2, 3, 4],
                          POOL_WIN: [market_win["a"] * 0.9, market_win["b"], market_win["c"] * 1.3, market_win["d"] * 0.5]})
    movements = pd.DataFrame({"race_id": ["R", "R"], "horse_no": [3, 4], "odds_evening": [8.0, 20.0], "odds_morning": [6.0, 25.0]})
    marked = marker.mark(predictions, places, dangers, wins, pools, movements).set_index("horse_id")
    assert marked.loc["c", "mark"] == "◎" and marked[AGREEMENT].all() and marked[POOL_BACKED].all()
    assert marked.loc["c", POOL_SUPPORT] == pytest.approx(1.3) and marked.loc["a", POOL_SUPPORT] == pytest.approx(0.9)
    assert marked.loc["c", "place_value_lightgbm"].__class__ is float or np.isnan(marked.loc["c", "place_value_lightgbm"])  # 見込みの倍率が無い
    assert marked.loc["c", ODDS_MOVE] == pytest.approx(np.log(6.0 / 8.0)) and np.isnan(marked.loc["a", ODDS_MOVE])
    # CatBoost の期待値が線より下なら不一致。3連単の支持が無ければ支持なし
    low = wins.assign(win_value_catboost=[1.0, 0.9, 0.95, 0.4])
    weak = pools.assign(**{POOL_WIN: [market_win["a"], market_win["b"], market_win["c"] * 0.8, market_win["d"]]})
    marked = marker.mark(predictions, places, dangers, low, weak, None).set_index("horse_id")
    assert not marked[AGREEMENT].any() and not marked[POOL_BACKED].any() and marked[ODDS_MOVE].isna().all()
    # モデルごとの列が無ければ一致にならない。3連単の確率が無ければ支持なし。木曜は旗を立てない
    marked = marker.mark(predictions.drop(columns=["probability_lightgbm", "probability_catboost"]), places, dangers,
                         wins.drop(columns=["win_value_lightgbm", "win_value_catboost"])).set_index("horse_id")
    assert not marked[AGREEMENT].any() and not marked[POOL_BACKED].any() and marked[POOL_WIN].isna().all()
    thursday = BacktestMarker(None, odds_known=False).mark(predictions, places, dangers, wins, pools, movements)
    assert not thursday[AGREEMENT].any() and not thursday[POOL_BACKED].any() and thursday[ODDS_MOVE].isna().all()


def test_レースの絞り込みは期待度と旗で選び無い旗は偽とみなす() -> None:
    frame = pd.DataFrame({"expectation": ["高", "高", "高", "低"], AGREEMENT: [True, True, False, True], POOL_BACKED: [True, False, True, True]})
    assert ALL_RACES.select(frame).tolist() == [True] * 4
    assert HIGH_RACES.select(frame).tolist() == [True, True, True, False]
    assert HIGH_AGREE.select(frame).tolist() == [True, True, False, False]
    assert HIGH_DISAGREE.select(frame).tolist() == [False, False, True, False]
    assert HIGH_POOL.select(frame).tolist() == [True, False, True, False]
    assert HIGH_AGREE_POOL.select(frame).tolist() == [True, False, False, False]
    assert not HIGH_AGREE.select(frame.drop(columns=[AGREEMENT])).any()
    assert RaceFilter("x", high_only=True, off_flags=("missing",)).select(frame).tolist() == [True, True, True, False]


def _marked_race_with_members() -> pd.DataFrame:
    """9頭。◎3・○1・▲5・△2,4,6・☆8・注9・消7。市場の見立ては 3着以内 0.5・1着 0.1。CatBoost だけ 8番を低く見る。"""
    marks = {3: "◎", 1: "○", 5: "▲", 2: "△", 4: "△", 6: "△", 8: "☆", 9: "注", 7: "消"}
    top3 = {3: 1.2, 1: 1.1, 5: 1.0, 2: 0.9, 4: 1.0, 6: 0.8, 8: 1.5, 9: 1.0, 7: 0.7}
    win = {3: 1.5, 1: 1.0, 5: 1.0, 2: 1.0, 4: 1.0, 6: 1.0, 8: 1.2, 9: 1.0, 7: 1.0}
    values = {3: 1.30, 8: 1.40, 1: 0.9, 5: 0.8, 2: 1.0, 4: 1.1, 6: 0.7, 9: 1.2, 7: 0.5}
    order = sorted(marks, key=lambda no: -top3[no])
    cat_top3 = {no: (0.5 if no == 8 else top3[no]) for no in marks}
    return pd.DataFrame({
        "race_id": "R", "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半", "expectation": "高", AGREEMENT: True, POOL_BACKED: False,
        "horse_no": order, "mark": [marks[no] for no in order], "place_value": [values[no] for no in order],
        "place_value_lightgbm": [values[no] for no in order], "place_value_catboost": [values[no] - (0.5 if no == 8 else 0.0) for no in order],
        "probability": [0.5 * top3[no] for no in order], "market_top3": 0.5,
        "probability_lightgbm": [0.5 * top3[no] for no in order], "probability_catboost": [0.5 * cat_top3[no] for no in order],
        "win_probability": [0.1 * win[no] for no in order], "market_win": 0.1,
        "win_probability_lightgbm": [0.1 * win[no] for no in order], "win_probability_catboost": [0.1 * win[no] for no in order],
        "axis": [no == 1 for no in order],
    })


def test_2モデル一致の買い目はモデルごとの期待値も線以上の組だけ() -> None:
    tickets = MarkTickets().build(_marked_race_with_members())
    by_rule = {label: group for label, group in tickets.groupby(RULE)}
    assert sorted(by_rule[PLACE_LABEL]["combo"]) == ["03", "08"]
    assert sorted(by_rule[PLACE_AGREE_LABEL]["combo"]) == ["03"]  # 8番は CatBoost の期待値が線より下
    priced = by_rule["3連単（◎軸・マルチ・期待値 1.0 以上）"]
    agreed = by_rule["3連単（◎軸・マルチ・期待値 1.0 以上・2モデル一致）"]
    assert 0 < len(agreed) < len(priced)
    # 8番が2着・3着の組は CatBoost の3着以内の比が落ちて外れる（1着の位置は1着の比を使うので、8番が1着の組は残る）
    assert not (agreed["combo"].str[2:4].eq("08") | agreed["combo"].str[4:6].eq("08")).any()
    assert priced["combo"].str[2:4].eq("08").any()
    assert (agreed[VALUE] >= 1.0).all() and set(agreed["combo"]) <= set(priced["combo"])
    # 3連複の期待値 1.0 以上の組は全部 8番を含むので、2モデル一致の行は 0点（行そのものが出ない）
    assert "3連複（◎軸・流し・期待値 1.0 以上・2モデル一致）" not in by_rule and "3連複（◎軸・流し・期待値 1.0 以上）" in by_rule
    assert tickets[AGREEMENT].all() and not tickets[POOL_BACKED].any()
    # モデルごとの列が無ければ、2モデル一致の行は 0点
    plain = MarkTickets().build(_marked_race_with_members().drop(columns=[c for c in _marked_race_with_members().columns if c.endswith(("_lightgbm", "_catboost"))]))
    assert PLACE_AGREE_LABEL not in set(plain[RULE]) and not plain[RULE].str.endswith("2モデル一致）").any()


def test_場面の帯はクラス競馬場頭数売上芝ダで分ける() -> None:
    scenes = pd.DataFrame({"race_id": ["A", "B", "C", "D"], "venue": ["東京", "小倉", "中山", None], "surface": ["芝", "ダート", "芝", "芝"],
                           "distance_m": [1600, 1200, 2000, 1800], "class_name": ["未勝利", "1勝クラス", "G1", "オープン"],
                           "class_order": [2, 3, 10, 6], "field_size": [10, 16, 18, 12]})
    pools = pd.DataFrame({"race_id": ["A", "B", "C"], WIN_POOL: [100.0, 300.0, 900.0]})
    bands = SceneBands().build(scenes, pools).set_index("race_id")
    assert bands[CLASS_AXIS].tolist() == ["新馬・未勝利", "1勝クラス", "重賞", "オープン・L"]
    assert bands[VENUE_AXIS].tolist() == ["主場", "ローカル", "主場", "不明"]
    assert bands[FIELD_AXIS].tolist() == ["〜10頭", "16頭〜", "16頭〜", "11〜15頭"]
    assert bands[POOL_AXIS].tolist() == ["下位 25%", "50〜75%", "上位 25%", "不明"]
    assert bands[SURFACE_AXIS].tolist() == ["芝", "ダート", "芝", "芝"]


def test_場面ごとの表は帯ごとに二重丸の成績と上乗せを出す() -> None:
    marked = pd.DataFrame({
        "race_id": ["A", "A", "B", "B"], "race_date": pd.Timestamp("2025-01-05"), "mark": ["◎", "消", "◎", "消"],
        "expectation": ["高", "高", "低", "低"], "finish": [1.0, 2.0, 3.0, 1.0], "win_payout": [500, 0, 0, 0],
        "probability": [0.8, 0.3, 0.6, 0.4], "market_top3": [0.6, 0.2, 0.6, 0.4], "win_probability": [0.5, 0.1, 0.2, 0.3],
        "market_win": [0.4, 0.2, 0.3, 0.3],
    })
    tickets = pd.DataFrame({"race_id": ["A", "B"], RULE: [PLACE_LABEL, PLACE_LABEL], DROPPED: ["", ""], PAYOUT: [200.0, 0.0], ODDS: [2.0, 3.0]})
    bands = pd.DataFrame({"race_id": ["A", "B"], CLASS_AXIS: ["重賞", "重賞"], VENUE_AXIS: ["主場", "ローカル"], FIELD_AXIS: ["16頭〜", "16頭〜"],
                          POOL_AXIS: ["上位 25%", "下位 25%"], SURFACE_AXIS: ["芝", "芝"]})
    table = SceneReport().table(marked, tickets, bands)
    assert table.title.startswith("10.")
    rows = {(row[0], row[1]): row for row in table.rows}
    assert rows[(CLASS_AXIS, "重賞")][2:4] == ["2", "250.0%"]  # ◎ 2頭で払戻 500円
    assert rows[(VENUE_AXIS, "主場")][5:7] == ["1", "500.0%"] and rows[(VENUE_AXIS, "ローカル")][5] == "0"
    assert rows[(VENUE_AXIS, "主場")][8:10] == ["1", "200.0%"]
    assert float(rows[(VENUE_AXIS, "主場")][10]) > 0  # A はモデルのほうが市場より正しい（1着の馬に 0.8）
    assert (VENUE_AXIS, "不明") not in rows


def test_オッズの動きの表は動きの分かる二重丸だけを帯で分ける() -> None:
    marked = pd.DataFrame({
        "race_id": ["A", "B", "C", "D"], "race_date": pd.Timestamp("2025-01-05"), "mark": "◎", "expectation": ["高", "高", "低", "高"],
        "finish": [1.0, 4.0, 2.0, 1.0], "win_payout": [600, 0, 0, 300], "place_payout": [200, 0, 150, 120], ODDS_MOVE: [-0.5, 0.0, 0.2, np.nan],
    })
    table = MovementReport().table(marked)
    assert table.title.startswith("11.")
    rows = {row[0]: row for row in table.rows}
    assert rows["大きく売れた（−30%超）"][1:5] == ["1", "1-0-0-0", "100.0%", "600.0%"]
    assert rows["ほぼ変わらず（±10%）"][1] == "1" and rows["売れず（+10〜30%）"][6] == "0"
    assert rows[ALL_LABEL][1] == "3" and rows[ALL_LABEL][6] == "2"
    assert "3（75.0%" in table.note
    assert MovementReport().table(marked.drop(columns=[ODDS_MOVE])).rows == []


def _odds_sample() -> tuple[synth.Sample, str]:
    sample = synth.simple_race()
    ra = sample.ra[0]
    race_id = "".join(ra[column] for column in keys.RACE_KEY)
    # 3連単の確定オッズ: 1着 4番の組と 2番・1番の組
    sample.odds.append(("o6", synth.odds_header(ra, "o6")))
    for seq, (combo, tenths) in enumerate((("040203", 12345), ("020403", 2000), ("010203", 500)), start=1):
        sample.odds.append(("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", combo, tenths, seq=seq)))
    # 単勝の時系列オッズ: 前日 23:00・当日 9:00（朝）・当日 12:00（朝より後。使わない）と、確定の断面（票数合計）
    for announced, odds in (("04052300", {1: 20, 2: 45, 4: 150}), ("04060900", {1: 25, 2: 40, 4: 120}), ("04061200", {1: 30, 2: 30, 4: 100})):
        sample.odds.append(("o1", synth.odds_header(ra, "o1", stage="1", announced=announced)))
        for seq, (no, tenths) in enumerate(odds.items(), start=1):
            sample.odds.append(("o1__単勝オッズ", synth.odds_row(ra, "o1__単勝オッズ", f"{no:02d}", tenths, seq=seq, announced=announced)))
    sample.odds.append(("o1", synth.odds_header(ra, "o1", win_votes="123456")))
    return sample, race_id


def test_合成DBから3連単の勝率とオッズの動きと場面と売上を読む(tmp_path: Path) -> None:
    sample, race_id = _odds_sample()
    con = duckdb.connect(str(synth.build_db(tmp_path / "filters.duckdb", sample)), read_only=True)
    race_ids = pd.Series([race_id])
    pools = PoolWinReader().read(con, race_ids).set_index("horse_no")
    total = 1 / 1234.5 + 1 / 200.0 + 1 / 50.0
    assert pools.loc[4, POOL_WIN] == pytest.approx((1 / 1234.5) / total) and pools.loc[1, POOL_WIN] == pytest.approx((1 / 50.0) / total)
    assert set(pools.index) == {1, 2, 4} and pools["race_id"].eq(race_id).all()
    snapshots = OddsSnapshotRepository().read(con, race_ids).set_index("horse_no")
    assert snapshots.loc[1, "odds_evening"] == pytest.approx(2.0) and snapshots.loc[1, "odds_morning"] == pytest.approx(2.5)
    assert snapshots.loc[4, "odds_morning"] == pytest.approx(12.0)  # 12:00 の断面は使わない
    scenes = RaceSceneRepository().read(con, race_ids)
    assert len(scenes) == 1 and scenes.loc[0, "venue"] == "東京" and scenes.loc[0, "field_size"] == 5
    assert {"surface", "distance_m", "class_name", "class_order"} <= set(scenes.columns)
    sizes = WinPoolSizeRepository().read(con, race_ids)
    assert sizes.loc[0, WIN_POOL] == pytest.approx(123456.0)
    # 時系列の無いレースは行が無い
    assert OddsSnapshotRepository().read(con, pd.Series(["2024040605010102"])).empty
    # 3連単は対象のレースの開催年の行だけ読む（年が合わなければ何も返らない）
    from yosou.shared.repository import POOLS, FirstHorsePoolRepository
    con.execute("CREATE OR REPLACE TEMP TABLE pool_years_wanted AS SELECT ? AS race_id", [race_id])
    assert FirstHorsePoolRepository(con).read(POOLS[0], "pool_years_wanted", years=("2024",))["horse_no"].nunique() == 3
    assert FirstHorsePoolRepository(con).read(POOLS[0], "pool_years_wanted", years=("2023",)).empty
