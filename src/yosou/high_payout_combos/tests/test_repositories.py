"""ファイルの読み書き（馬ごとの表・組の表・年ごとの予測）のテスト。値は架空。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from ..repository import ComboTableRepository, HorseTableRepository, PredictionStore, TicketModelRepository
from ..repository.horse_table_columns import STORED_COLUMNS
from . import synthetic_race as race

TRIO, TRIFECTA = TicketType.TRIO, TicketType.TRIFECTA


def test_馬ごとの表は_全部のファイルをつなぎ_決まった列だけ読む(tmp_path: Path) -> None:
    race.horses().assign(expectation="高").to_parquet(tmp_path / "2025-a.parquet")                       # 余分な列はファイルごとに違ってよい
    race.horses("2025010506010102").assign(win_value_band="A").to_parquet(tmp_path / "2025-b.parquet")
    horses = HorseTableRepository(tmp_path).load()
    assert len(horses) == 8 and list(horses.columns) == list(STORED_COLUMNS)
    assert horses["race_id"].map(len).eq(16).all() and horses["race_date"].iloc[0] == pd.Timestamp("2025-01-05")


def test_同じ馬が2つのファイルにあれば誤り(tmp_path: Path) -> None:
    race.horses().to_parquet(tmp_path / "a.parquet")
    race.horses().to_parquet(tmp_path / "b.parquet")
    with pytest.raises(ValueError, match="同じ馬が2行"):
        HorseTableRepository(tmp_path).load()


def test_馬ごとの表が無ければ誤り(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="馬ごとの表がありません"):
        HorseTableRepository(tmp_path).load()


def test_組の表は_月ごとに足して年のファイルに書く(tmp_path: Path) -> None:
    repository = ComboTableRepository(tmp_path / "tables")
    january = pd.DataFrame({"race_id": ["a", "b"], "odds": [10.0, 20.0]})
    february = pd.DataFrame({"race_id": ["c"], "odds": [30.0]})
    with repository.writer(TRIO, 2024) as writer:
        writer.write(january)
        writer.write(february.iloc[0:0])   # 空の表は書かない
        writer.write(february)
    assert writer.row_count == 3 and repository.exists(TRIO, 2024) and repository.years(TRIO) == [2024]
    assert repository.path(TRIO, 2024).name == "trio_2024.parquet"
    assert list(repository.load(TRIO, 2024)["race_id"]) == ["a", "b", "c"]
    assert list(repository.load(TRIO, 2024, columns=["odds"]).columns) == ["odds"]
    assert repository.years(TRIFECTA) == []   # 3連複（trio）の表を、3連単（trifecta）のものと取り違えない


def test_組の表は_途中で誤りが出たら本来の名前にしない(tmp_path: Path) -> None:
    repository = ComboTableRepository(tmp_path)
    with pytest.raises(RuntimeError), repository.writer(TRIO, 2024) as writer:
        writer.write(pd.DataFrame({"race_id": ["a"], "odds": [10.0]}))
        raise RuntimeError("途中で止まった")
    assert not repository.exists(TRIO, 2024) and repository.years(TRIO) == []


def test_1行も書かなければ_組の表のファイルを作らない(tmp_path: Path) -> None:
    repository = ComboTableRepository(tmp_path)
    with repository.writer(TRIO, 2024):
        pass
    assert not repository.exists(TRIO, 2024)
    with pytest.raises(FileNotFoundError, match="組の表がありません"):
        repository.load(TRIO, 2024)


def test_年ごとの予測は_ある年ぶん全部をつないで読む(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "predictions")
    store.save(TRIO, 2025, pd.DataFrame({"race_id": ["c"], "probability": [0.03]}))
    store.save(TRIO, 2024, pd.DataFrame({"race_id": ["a", "b"], "probability": [0.01, 0.02]}))
    assert store.years(TRIO) == [2024, 2025] and store.path(TRIO, 2024).name == "trio_2024.parquet"
    assert list(store.load(TRIO)["race_id"]) == ["a", "b", "c"]   # 古い年から
    with pytest.raises(FileNotFoundError, match="予測がありません"):
        store.load(TRIFECTA)


def test_モデルの無い券種は_無いと答える(tmp_path: Path) -> None:
    assert not TicketModelRepository(tmp_path).has(TRIO)
