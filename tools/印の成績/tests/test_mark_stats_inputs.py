"""PredictionFile（予測の読み込み）・FavoriteDangerJudge（危険の線）・BacktestMarker（印付け）・RaceResults（結果の読み出し）のテスト。

値は架空。DB は合成DB だけを使う。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from 共通 import facts
from yosou.shared.feature.odds import TOP3_RATE

from 印の成績.backtest_marker import BacktestMarker
from 印の成績.favorite_danger_judge import FavoriteDangerJudge
from 印の成績.prediction_file import PredictionFile
from 印の成績.race_results import RaceResults
from 印の成績.win_value_attacher import WinValueAttacher


def _prediction_rows(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{"レースID": row["race"], "開催日": pd.Timestamp("2025-01-05"), "馬ID": row["horse"], "馬番": row.get("no", 1),
                          "LightGBM": row["p"], "CatBoost": row["p"], "確率": row["p"], "区切り": row.get("fold", "2025年前半"),
                          "期間": row.get("period", "テスト"), "区分": row.get("segment", "全体")} for row in rows])


def test_予測のファイルを名前かパスで読む(tmp_path: Path) -> None:
    folder = tmp_path / "predictions"
    (folder / "form").mkdir(parents=True)
    _prediction_rows([{"race": 1, "horse": 10, "p": 0.3}]).to_pickle(folder / "form" / "new.pkl")
    by_name = PredictionFile("form/new", folder)
    loaded = by_name.load()
    assert loaded.loc[0, "race_id"] == "1" and loaded.loc[0, "probability"] == 0.3 and loaded.loc[0, "period"] == "テスト"
    assert by_name.label() == "form_new"
    assert PredictionFile(str(folder / "form" / "new.pkl")).path == folder / "form" / "new.pkl"
    with pytest.raises(FileNotFoundError):
        PredictionFile("form/none", folder).load()


def test_危険の線は区切りの検証期間で決め1番人気だけを危険にする() -> None:
    rows = []
    for band in ("1番人気", "2〜3番人気"):
        for i in range(60):
            # 検証期間: 危険度が高い（予想 0.6）馬ほど負ける。テスト期間: 2頭
            high = i < 40
            rows.append({"race": f"V{band}{i}", "horse": f"h{i}", "p": 0.6 if high else 0.2, "segment": band, "period": "検証"})
        rows.append({"race": f"T{band}", "horse": "t1", "p": 0.6, "segment": band})
    table = _prediction_rows(rows).rename(columns={"レースID": "race_id", "開催日": "race_date", "馬ID": "horse_id", "馬番": "horse_no",
                                                    "確率": "probability", "区切り": "fold", "期間": "period", "区分": "segment"})
    table = table.astype({"race_id": str, "horse_id": str})
    finish = [5.0 if (row["p"] == 0.6 and row.get("period") == "検証") else 1.0 for row in rows]
    places = table[["race_id", "horse_id"]].assign(finish=finish, **{TOP3_RATE: 0.7})
    dangers, lines = FavoriteDangerJudge().judge(table, places)
    assert set(dangers["race_id"]) == {"T1番人気", "T2〜3番人気"}
    # 危険度は 0.6 − (1 − 0.7) = 0.3 と −0.1。線の候補（0〜0.2）のどれでも同じ40頭を拾うので、いちばん低い 0.0 になる
    assert lines["2025年前半"]["1番人気"] == pytest.approx(0.0)
    flagged = dangers.set_index("race_id")["is_danger"]
    assert bool(flagged["T1番人気"]) and not bool(flagged["T2〜3番人気"])  # 2〜3番人気は印に使わない


def test_テスト期間の行に単勝の期待値を付ける() -> None:
    rows = [{"race": "V", "horse": "v1", "no": 1, "p": 0.3, "period": "検証"},
            {"race": "T", "horse": "t1", "no": 1, "p": 0.3}, {"race": "T", "horse": "t2", "no": 2, "p": 0.1}]
    table = _prediction_rows(rows).rename(columns={"レースID": "race_id", "開催日": "race_date", "馬ID": "horse_id", "馬番": "horse_no",
                                                    "確率": "probability", "区切り": "fold", "期間": "period", "区分": "segment"})
    table = table.astype({"race_id": str, "horse_id": str})
    places = table[["race_id", "horse_id"]].assign(win_odds=[5.0, 5.0, 15.0])
    wins = WinValueAttacher().attach(table, places)
    by_horse = wins.set_index("horse_id")
    assert set(wins["race_id"]) == {"T"}  # 検証期間の行は返さない
    assert by_horse.loc["t1", "win_value"] == pytest.approx(1.5) and by_horse.loc["t1", "win_probability"] == pytest.approx(0.3)
    assert by_horse.loc["t2", "win_value"] == pytest.approx(1.5)  # 0.1 × 15


def test_確定オッズから市場の見立てを出して印を付ける() -> None:
    predictions = pd.DataFrame({"race_id": ["R"] * 4, "race_date": pd.Timestamp("2025-01-05"), "horse_id": ["a", "b", "c", "d"],
                                "probability": [0.7, 0.5, 0.3, 0.1], "fold": "2025年前半"})
    results = pd.DataFrame({"race_id": ["R"] * 4, "horse_id": ["a", "b", "c", "d"], "horse_no": [1, 2, 3, 4],
                            "finish": [2.0, 1.0, 3.0, 4.0], "win_odds": [2.0, 3.0, 6.0, 20.0], "popularity": [1.0, 2.0, 3.0, 4.0],
                            "win_payout": [0, 300, 0, 0], "place_payout": [120, 150, 200, 0], "field_size": [4] * 4,
                            "place_odds_low": [1.1, 1.3, 1.8, 4.0], "place_odds_high": [1.3, 1.6, 2.4, 6.0]})
    dangers = pd.DataFrame({"race_id": ["R"], "horse_id": ["a"], "favorite_band": ["1番人気"], "out_probability": [0.5],
                            "market_out": [0.2], "danger_score": [0.3], "danger_line": [0.1], "is_danger": [True]})
    marker = BacktestMarker(None)
    marked = marker.mark(predictions, marker.places(results), dangers).set_index("horse_id")
    assert marked.loc["a", "mark"] == "消" and marked.loc["b", "mark"] == "◎"
    assert marked.loc["b", "finish"] == 1.0 and marked.loc["b", "win_payout"] == 300
    assert marked["market_top3"].sum() == pytest.approx(3.0)
    assert marked["place_value"].isna().all()  # 見込みの倍率が無ければ期待値は出さない
    assert marked["expectation"].isna().all()  # 1着の予想が無ければ期待度は付かない
    # 1着の予想があれば、◎ は単勝の期待値の1位（c: 0.2 × 6.0 = 1.2）で、期待度は 1.00 以上なので「高」
    wins = pd.DataFrame({"race_id": ["R"] * 4, "horse_id": ["a", "b", "c", "d"], "win_probability": [0.5, 0.3, 0.2, 0.02],
                         "win_value": [1.0, 0.9, 1.2, 0.4]})
    marked = marker.mark(predictions, marker.places(results), dangers, wins).set_index("horse_id")
    assert marked.loc["c", "mark"] == "◎" and marked.loc["b", "mark"] == "○"
    assert (marked["expectation"] == "高").all()
    low = marker.mark(predictions, marker.places(results), dangers, wins.assign(win_value=[0.5, 0.9, 0.8, 0.4])).set_index("horse_id")
    assert low.loc["b", "mark"] == "◎" and (low["expectation"] == "低").all()
    # 木曜（オッズが無い）は、期待値も危険な人気馬も使わず、◎ は1着になる確率の1位（a）。期待度は付かない。成績の人気・払戻は確定の値のまま
    thursday = BacktestMarker(None, odds_known=False).mark(predictions, marker.places(results), dangers, wins).set_index("horse_id")
    assert thursday.loc["a", "mark"] == "◎" and "1着になる確率がレース内1位" in thursday.loc["a", "mark_reason"]
    assert thursday["expectation"].isna().all() and not thursday["is_danger"].any()
    assert thursday.loc["a", "popularity"] == 1.0 and thursday.loc["b", "win_payout"] == 300


def test_合成DBから出走の結果を読む(synth_db: Path) -> None:
    con = duckdb.connect(str(synth_db), read_only=True)
    facts.ensure_facts(con)
    race_ids = con.execute(f"SELECT DISTINCT race_id FROM {facts.FACTS_TABLE} WHERE ran").df()["race_id"]
    results = RaceResults().read(con, race_ids)
    assert set(results["race_id"]) == set(race_ids.astype(str))
    assert {"finish", "win_odds", "popularity", "win_payout", "place_payout", "place_odds_low"} <= set(results.columns)
    assert np.isin(results["race_id"].unique(), race_ids.astype(str)).all()
