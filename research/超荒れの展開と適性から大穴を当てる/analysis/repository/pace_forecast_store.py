"""予想「展開から着順を予想」の年ごとの確かめで残した予測（その年より前だけで学んだもの）を読む。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

#: 前半の組（③ ペースと ① ② 序盤の位置）の、前日の時点の年ごとの予測（``<年>.pkl``。Git の対象外）。
DEFAULT_PACE_FORECASTS = (Path(__file__).resolve().parents[4] / "reports" / "展開から着順を予想" / "out_of_sample" / "early"
                          / "day_before")


@dataclass(frozen=True)
class PaceForecastStore:
    """``<年>.pkl`` は ``{"races": レースごとのペースの確率, "horses": 馬ごとの位置の確率}``（``OutOfSampleRepository`` の形）。

    - ``races()``: race_id・p_slow・p_even・p_high（③ 前半のペースがスロー・平均・ハイになる確率）
    - ``horses()``: race_id・horse_id・p_leader（先頭）・p_front（前から3分の1まで）・p_middle・p_back（後ろ3分の1）
    どれも前日の時点の材料だけで、その年より前のレースだけで学んだ予測。置き場所が無ければ空の表。
    """

    root: Path = DEFAULT_PACE_FORECASTS

    def races(self) -> pd.DataFrame:
        frames = [saved["races"][["レースID", "p_slow", "p_even", "p_high"]] for saved in self._saved()]
        if not frames:
            return pd.DataFrame(columns=["race_id", "p_slow", "p_even", "p_high"])
        return pd.concat(frames, ignore_index=True).rename(columns={"レースID": "race_id"}).astype({"race_id": str})

    def horses(self) -> pd.DataFrame:
        columns = ["レースID", "馬ID", "p_leader", "p_front", "p_middle", "p_back"]
        frames = [saved["horses"][columns] for saved in self._saved()]
        if not frames:
            return pd.DataFrame(columns=["race_id", "horse_id", "p_leader", "p_front", "p_middle", "p_back"])
        frame = pd.concat(frames, ignore_index=True).rename(columns={"レースID": "race_id", "馬ID": "horse_id"})
        return frame.astype({"race_id": str, "horse_id": str})

    def _saved(self) -> list[dict]:
        root = Path(self.root)
        if not root.exists():
            return []
        return [pd.read_pickle(path) for path in sorted(root.glob("*.pkl"))]
