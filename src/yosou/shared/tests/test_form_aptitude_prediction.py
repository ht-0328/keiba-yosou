"""今のモデルの予測の流れの組み立て（``FormAptitudePrediction``）のテスト。

時点ごとに、材料を作る部品のどの材料を使うか（木曜は P と T、前日は S、当日は無し）と、
材料を作る部品を予測のたびに作り直すことを確かめる。モデルは読まない（流れを組み立てるだけ）。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from yosou.shared.feature import PredictionTiming
from yosou.shared.workflow import FormAptitudePrediction, PredictionWorkflow


class RecordingMaterials:
    """呼ばれた材料の名前を覚えるだけの部品（``FormAptitudeMaterials`` を守る）。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def pace(self):
        return self._record("pace")

    def score(self):
        return self._record("score")

    def ability_score(self):
        return self._record("ability_score")

    def bias(self):
        return self._record("bias")

    def weight_discount(self):
        return self._record("weight_discount")

    def _record(self, name: str):
        self.calls.append(name)
        return lambda *args: None


def _calls(tmp_path: Path, timing: PredictionTiming) -> list[str]:
    made: list[RecordingMaterials] = []

    def factory(con: duckdb.DuckDBPyConnection) -> RecordingMaterials:
        made.append(RecordingMaterials())
        return made[-1]

    prediction = FormAptitudePrediction(tmp_path / "models", factory, tmp_path / "figures")
    with duckdb.connect() as con:
        workflow = prediction.workflow(con, timing)
        prediction.workflow(con, timing)
    assert isinstance(workflow, PredictionWorkflow)
    assert len(made) == 2
    return made[0].calls


@pytest.mark.parametrize(("timing", "expected"), [
    (PredictionTiming.THURSDAY, ["pace", "ability_score", "ability_score"]),
    (PredictionTiming.DAY_BEFORE, ["score"]),
    (PredictionTiming.RACE_DAY, []),
])
def test_時点ごとに採用した材料だけを使い_予測のたびに材料の部品を作る(tmp_path: Path, timing: PredictionTiming, expected: list[str]) -> None:
    assert _calls(tmp_path, timing) == expected
