"""比べる相手の、区切りごとの予測のファイルの置き場所（どれも、その半年より前で学んだモデルの予測）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yosou.shared.feature import PredictionTiming

_REPORTS = Path(__file__).resolve().parents[4] / "reports"
_CURRENT = _REPORTS / "複勝以外の回収率100超" / "predictions-2019から"
_WILD = _REPORTS / "百万馬券を当てる" / "predictions"
_WIN5 = _REPORTS / "WIN5で人気薄の勝ち馬を狙う" / "predictions"

#: 比べる相手の名前。
CURRENT, WILD, WIN5_LONGSHOT = "今のモデル", "荒れる前提のモデル", "WIN5研究の人気薄モデル"
#: 今の消（予想「人気馬が4着以下になるかを予想」）の区切りごとの予測（時点を問わず1つ）。
CURRENT_DANGER = _CURRENT / "favorites_out_of_top3" / "people_market.pkl"


@dataclass(frozen=True)
class ComparisonFiles:
    """時点ごとに、（相手の名前, 目的変数）→ 予測の pkl。無い組（荒れる前提のモデルの前日、WIN5 研究の 3着以内）は入らない。
    荒れる前提のモデルは 2021年からの区切りだけ、WIN5 研究の人気薄モデルは 6番人気以下の行だけ。"""

    timing: PredictionTiming

    def paths(self) -> dict[tuple[str, str], Path]:
        if self.timing == PredictionTiming.RACE_DAY:
            found = {(CURRENT, "top3"): _CURRENT / "dscore_race_day" / "top3-race_day.pkl",
                     (CURRENT, "win"): _CURRENT / "dscore_finish_race_day" / "win-race_day.pkl",
                     (WILD, "top3"): _WILD / "dscore_race_day" / "wild-top3-race_day.pkl",
                     (WILD, "win"): _WILD / "dscore_finish_race_day" / "wild-win-race_day.pkl",
                     (WIN5_LONGSHOT, "win"): _WIN5 / "longshot6-race_day.pkl"}
        else:
            found = {(CURRENT, "top3"): _CURRENT / "dscore_day_before" / "top3-day_before.pkl",
                     (CURRENT, "win"): _CURRENT / "dscore_day_before" / "win-day_before.pkl",
                     (WIN5_LONGSHOT, "win"): _WIN5 / "longshot6-day_before.pkl"}
        return {key: path for key, path in found.items() if path.exists()}
