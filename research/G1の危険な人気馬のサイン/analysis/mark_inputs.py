"""道具「印の成績」に渡す、G1だけの全頭の予測と、人気帯を付けた人気馬の予測を書く。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND
from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData

from 既存モデルの改善.analysis.walk_forward import SEGMENT, PredictionStore

from .g1_favorites import G1_GRADE
from .sign_training_table import GRADE
from .sign_variants import TABLE_NAME

#: 全頭の予想の予測（研究「既存モデルの改善」の入口⑨。全レースで学んだ今の材料・当日・1年ずつの区切りの、重賞の行）。
FORM_TABLE, FORM_KEY = "form_race_day", "general-race_day-stakes"
#: 書く場所（``<predictions>/`` の下）と、全頭の予想の G1 の行のファイル名。
MARKS_FOLDER = "印の成績の入力"
FORM_G1_KEY = "general-race_day-g1"
_KEY = [RACE_ID, HORSE_ID]


class MarkInputs:
    """``signs_root``（この研究の予測の置き場所）と ``form_root``（研究「既存モデルの改善」の予測の置き場所）から、
    道具「印の成績」の ``--form``・``--danger`` に渡すファイルを ``<signs_root>/印の成績の入力/`` に書く。

    - 全頭の予想: 重賞の行の予測から、G1 の行だけを残す（G1 のレースだけに印を付けるため）。
    - 人気馬の予想: 区分の列を、その馬の人気帯にする。人気帯で分けずに学んだ作り方（G1だけ・重賞）は区分が「全体」なので、
      道具が人気帯ごとに危険の線を決め、1番人気を優先して消を選べるように直す。
    """

    def __init__(self, signs_root: Path, form_root: Path) -> None:
        self._signs = PredictionStore(signs_root)
        self._form = PredictionStore(form_root)
        self._folder = Path(signs_root) / MARKS_FOLDER

    def write(self, data: TrainingData, keys: Sequence[str]) -> list[Path]:
        written = [self._write_form(data)]
        bands = pd.DataFrame({RACE_ID: data.ids[RACE_ID].astype(str), HORSE_ID: data.ids[HORSE_ID].astype(str),
                              "band": data.evaluation[FAVORITE_BAND]})
        for key in keys:
            if not self._signs.exists(TABLE_NAME, key):
                continue
            frame = self._signs.read(TABLE_NAME, key).astype({RACE_ID: str, HORSE_ID: str})
            banded = frame.merge(bands, on=_KEY, how="left")
            written.append(self._save("danger", key, banded.assign(**{SEGMENT: banded["band"]}).drop(columns="band")))
        return written

    def _write_form(self, data: TrainingData) -> Path:
        g1 = data.evaluation[GRADE].eq(G1_GRADE)
        races = set(data.ids.loc[g1, RACE_ID].astype(str))
        form = self._form.read(FORM_TABLE, FORM_KEY)
        return self._save("form", FORM_G1_KEY, form[form[RACE_ID].astype(str).isin(races)])

    def _save(self, folder: str, key: str, frame: pd.DataFrame) -> Path:
        path = self._folder / folder / f"{key}.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.reset_index(drop=True).to_pickle(path)
        return path
