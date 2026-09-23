"""契約: 予測の CSV を書いて読み戻すと、レースID・馬ID が文字列のまま、開催日が日付になる。無いファイルは案内つきの誤り。"""

import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_ID, RACE_DATE, RACE_ID

from 馬券の買い方の検証.analysis.prediction import PredictionFile


def test_round_trip_keeps_ids_as_text_and_dates_as_dates(tmp_path):
    table = pd.DataFrame({
        RACE_ID: ["2025070605010101", "2025070605010102"], RACE_DATE: pd.to_datetime(["2025-07-06", "2025-07-06"]),
        HORSE_ID: ["2019100001", "2019100002"], "馬番": [3, 7], "3着以内に入る確率": [0.612, 0.08],
    })
    file = PredictionFile(tmp_path / "predictions" / "form_aptitude_top3.csv")
    file.write(table)
    loaded = file.read()
    assert list(loaded[RACE_ID]) == ["2025070605010101", "2025070605010102"]
    assert list(loaded[HORSE_ID]) == ["2019100001", "2019100002"]
    assert loaded[RACE_DATE].dtype.kind == "M"
    assert list(loaded["馬番"]) == [3, 7]


def test_race_level_table_without_horse_id(tmp_path):
    table = pd.DataFrame({RACE_ID: ["2025070605010101"], RACE_DATE: pd.to_datetime(["2025-07-06"]), "券種": ["単勝"]})
    file = PredictionFile(tmp_path / "upset_level.csv")
    file.write(table)
    assert list(file.read()["券種"]) == ["単勝"]


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError, match="predict_all"):
        PredictionFile(tmp_path / "nothing.csv").read()
