"""馬ごとの表（``horses.py``）の、印付け（``HorseMarker``）・列と行の選び方（``HorseTableSelector``）・書き出し（``HorseTableStore``）のテスト。

値は架空。元DB は使わず、元DB から読んだもの（``MarkingInputs``）は合成の表で渡す。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from 高配当の買い目.horse_marker import HorseMarker
from 高配当の買い目.horse_table_columns import EXTRA_COLUMNS, MATERIAL_COLUMNS, REQUIRED_COLUMNS
from 高配当の買い目.horse_table_selector import HorseTableSelector
from 高配当の買い目.marking_inputs import MarkingInputs
from 高配当の買い目.repository.horse_table_store import HorseTableStore

HORSES = ["a", "b", "c", "d"]


def _predictions(race: str, day: str, probabilities: list[float]) -> pd.DataFrame:
    """予測のファイルを読んだ形（``PredictionFile.load``）の、1レース4頭のテスト期間の行。"""
    return pd.DataFrame({"race_id": race, "race_date": pd.Timestamp(day), "horse_id": HORSES, "horse_no": [1, 2, 3, 4],
                         "probability": probabilities, "fold": "2025年前半", "period": "テスト", "segment": "全体"})


def _results(race: str) -> pd.DataFrame:
    return pd.DataFrame({"race_id": race, "horse_id": HORSES, "horse_no": [1, 2, 3, 4], "finish": [2.0, 1.0, 3.0, 4.0],
                         "win_odds": [2.0, 3.0, 6.0, 20.0], "popularity": [1.0, 2.0, 3.0, 4.0], "win_payout": [0, 300, 0, 0],
                         "place_payout": [120, 150, 200, 0], "field_size": 4, "affiliation": "美浦", "runs_before": 5,
                         "place_odds_low": [1.1, 1.3, 1.8, 4.0], "place_odds_high": [1.3, 1.6, 2.4, 6.0]})


def _marked() -> pd.DataFrame:
    """2レース（2025-01-05 の R1 と 2025-02-01 の R2）に印を付けた表。"""
    tested = pd.concat([_predictions("R1", "2025-01-05", [0.7, 0.5, 0.3, 0.1]), _predictions("R2", "2025-02-01", [0.6, 0.5, 0.4, 0.2])])
    wins = pd.concat([_predictions("R1", "2025-01-05", [0.5, 0.3, 0.2, 0.02]), _predictions("R2", "2025-02-01", [0.4, 0.3, 0.2, 0.05])])
    favorites = _predictions("R1", "2025-01-05", [0.3, 0.3, 0.3, 0.3]).iloc[:1].assign(segment="1番人気")
    pools = pd.DataFrame({"race_id": ["R1"] * 4, "horse_no": [1, 2, 3, 4], "pool_win": [0.4, 0.3, 0.2, 0.1]})
    inputs = MarkingInputs(pd.concat([_results("R1"), _results("R2")], ignore_index=True), pools, pd.DataFrame())
    return HorseMarker(None).mark(tested, wins, favorites, inputs)


def test_印を付けた表から_約束の列と残す開催日の行だけを選ぶ() -> None:
    marked = _marked()
    table = HorseTableSelector().select(marked)
    kept_extras = [column for column in EXTRA_COLUMNS if column in marked.columns]
    assert list(table.columns) == [*REQUIRED_COLUMNS, *kept_extras]
    assert set(MATERIAL_COLUMNS) <= set(table.columns) and "mark_reason" not in table.columns and "win_payout" not in table.columns
    assert len(table) == 8 and list(table["race_id"]) == ["R1"] * 4 + ["R2"] * 4 and list(table["horse_no"]) == [1, 2, 3, 4] * 2
    assert table["race_date"].tolist() == [pd.Timestamp("2025-01-05")] * 4 + [pd.Timestamp("2025-02-01")] * 4
    # 印は今週の予想と同じ決め方: R1 は単勝の期待値（1着の確率 × 確定の単勝オッズ）が1位の 3番（0.2 × 6.0）が ◎
    first = table[table["race_id"] == "R1"].set_index("horse_no")
    assert first.loc[3, "mark"] == "◎" and first.loc[3, "win_value"] == pytest.approx(1.2)
    assert first["market_win"].sum() == pytest.approx(1.0) and not first["is_danger"].any()
    # 開催日の範囲で絞る（端の日を含む）
    january = HorseTableSelector(date(2025, 1, 1), date(2025, 1, 5)).select(marked)
    assert set(january["race_id"]) == {"R1"}
    assert set(HorseTableSelector(first_day=date(2025, 1, 6)).select(marked)["race_id"]) == {"R2"}
    assert HorseTableSelector(last_day=date(2024, 12, 31)).select(marked).empty


def test_要る列が無い表と_同じ出走が重なる表は誤りにする() -> None:
    marked = _marked()
    with pytest.raises(ValueError, match="danger_score"):
        HorseTableSelector().select(marked.drop(columns=["danger_score"]))
    with pytest.raises(ValueError, match="同じレース・同じ馬番"):
        HorseTableSelector().select(pd.concat([marked, marked.iloc[:1]]))


def test_既定の名前は最初の年と最後の年で_同じフォルダに同じ出走があれば書かない(tmp_path: Path) -> None:
    table = HorseTableSelector().select(_marked())
    store = HorseTableStore(tmp_path / "horses")
    assert store.default_path(table) == tmp_path / "horses" / "2025-2025.parquet"
    saved = store.save(table, store.default_path(table))
    loaded = pd.read_parquet(saved)
    assert list(loaded.columns) == list(table.columns) and len(loaded) == 8
    assert store.save(table, saved) == saved   # 同じ名前には書き直せる
    with pytest.raises(ValueError, match="2025-2025.parquet"):
        store.save(table, tmp_path / "horses" / "別の名前.parquet")   # 予想のパッケージが読むときに、同じ出走が2つになるのを防ぐ
    assert store.save(table, tmp_path / "ほか" / "確かめ.parquet").is_file()   # 別のフォルダには書ける
    with pytest.raises(ValueError, match="行がありません"):
        store.save(table.iloc[0:0], tmp_path / "空.parquet")
