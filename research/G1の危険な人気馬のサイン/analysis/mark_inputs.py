"""道具「印の成績」に渡す、範囲ごとの全頭の予測と、人気帯を付けた人気馬の予測を書く。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND
from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData

from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, SEGMENT, PredictionStore

from .race_scope import EVALUATION_SCOPES, RaceScope
from .sign_variants import TABLE_NAME, SignVariant

#: 全頭の予想の予測（研究「既存モデルの改善」の入口⑨。全レースで学んだ今の材料・当日・1年ずつの区切りの、重賞の行）。
FORM_TABLE, FORM_KEY = "form_race_day", "general-race_day-stakes"
#: 書く場所（``<predictions>/`` の下）と、全頭の予想の範囲ごとのファイル名の頭。
MARKS_FOLDER = "印の成績の入力"
FORM_PREFIX = "general-race_day-"
_KEY = [RACE_ID, HORSE_ID]


def form_key(scope: RaceScope) -> str:
    """範囲ごとの全頭の予想のファイル名（例 ``general-race_day-g1``）。"""
    return f"{FORM_PREFIX}{scope.key}"


class MarkInputs:
    """``signs_root``（この研究の予測の置き場所）と ``form_root``（研究「既存モデルの改善」の予測の置き場所）から、
    道具「印の成績」の ``--form``・``--danger`` に渡すファイルを ``<signs_root>/印の成績の入力/`` に書く。

    - 全頭の予想: 範囲（G1・G2とG3）ごとに、その範囲のレースの行だけを残す（その範囲のレースだけに印を付けるため）。
    - 人気馬の予想: 区分の列を、その馬の人気帯にする。人気帯で分けずに学んだ作り方（G1だけ・重賞）は区分が「全体」なので、
      道具が人気帯ごとに危険の線を決め、1番人気を優先して消を選べるように直す。道具は危険の線を検証期間の行で決めるので、
      検証期間の行は、その作り方が学んだ範囲のレースだけにする（G1 で学んだモデルの線は G1 の前の年で決まり、その線のまま
      ほかのレースにも当てる）。テスト期間の行は全部残す。
    """

    def __init__(self, signs_root: Path, form_root: Path) -> None:
        self._signs = PredictionStore(signs_root)
        self._form = PredictionStore(form_root)
        self._folder = Path(signs_root) / MARKS_FOLDER

    def write(self, data: TrainingData, variants: Sequence[SignVariant]) -> list[Path]:
        written = [self._write_form(data, scope) for scope in EVALUATION_SCOPES]
        for variant in variants:
            if not self._signs.exists(TABLE_NAME, variant.key):
                continue
            frame = self._signs.read(TABLE_NAME, variant.key).astype({RACE_ID: str, HORSE_ID: str})
            facts = pd.DataFrame({RACE_ID: data.ids[RACE_ID].astype(str), HORSE_ID: data.ids[HORSE_ID].astype(str),
                                  "band": data.evaluation[FAVORITE_BAND], "trained": variant.scope.rows(data)})
            banded = frame.merge(facts, on=_KEY, how="inner")
            kept = banded[banded[PART].eq(PART_TEST) | banded["trained"]]
            written.append(self._save("danger", variant.key,
                                      kept.assign(**{SEGMENT: kept["band"]}).drop(columns=["band", "trained"])))
        return written

    def _write_form(self, data: TrainingData, scope: RaceScope) -> Path:
        races = set(data.ids.loc[scope.rows(data), RACE_ID].astype(str))
        form = self._form.read(FORM_TABLE, FORM_KEY)
        return self._save("form", form_key(scope), form[form[RACE_ID].astype(str).isin(races)])

    def _save(self, folder: str, key: str, frame: pd.DataFrame) -> Path:
        path = self._folder / folder / f"{key}.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.reset_index(drop=True).to_pickle(path)
        return path
