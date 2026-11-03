"""危険度の線を「検証期間の上位 x%」にして、テスト期間の消を決める。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.danger_picker import DangerPicker

from .calibrated_window_trainer import ODDS_ONLY_COLUMN

#: 予測の表の列（研究「既存モデルの改善」の walk_forward が書く名前）。
_RACE, _HORSE, _PROBABILITY, _FOLD, _PART, _SEGMENT = "レースID", "馬ID", "確率", "区切り", "期間", "区分"
_VALID, _TEST = "検証", "テスト"


class StrictDangerFlags:
    """区切りごと・人気帯ごとに、検証期間の危険度の上位 ``share`` に入る値を線にして、テスト期間の消を決める。

    今の線の決め方（``DangerThreshold``）は、差 × √頭数をいちばん大きくする線を選ぶので、頭数の多い低い線になりやすく、
    危険度のそれほど高くない人気馬まで消になる。ここでは「モデルが本当に危ないと見た上の方だけ」を消にする。
    危険度は「予想の4着以下の確率 − オッズだけのモデルの確率」。消は今週の予想と同じ ``DangerPicker`` が1レース1頭だけ選ぶ
    （1番人気が線以上ならその馬、そうでなければ 2〜5番人気で線をいちばん大きく超えた馬）。
    戻り値は道具「印の成績」の ``--danger-flags`` に渡す表（列 race_id・horse_id・favorite_band・is_danger）。
    """

    def __init__(self, share: float) -> None:
        if not 0 < share < 1:
            raise ValueError(f"上位の割合は 0 より大きく 1 より小さい値にしてください: {share}")
        self._share = share

    def build(self, predictions: pd.DataFrame) -> pd.DataFrame:
        scored = predictions.assign(danger=predictions[_PROBABILITY] - predictions[ODDS_ONLY_COLUMN])
        valid = scored[scored[_PART] == _VALID]
        lines = valid.groupby([_FOLD, _SEGMENT])["danger"].quantile(1 - self._share).rename("line")
        test = scored[scored[_PART] == _TEST].join(lines, on=[_FOLD, _SEGMENT])
        picker = DangerPicker()
        picked = [picker.pick(race[_SEGMENT], race["danger"], race["line"]) for _, race in test.groupby(_RACE, sort=False)]
        flags = pd.concat(picked).reindex(test.index, fill_value=False) if picked else pd.Series(dtype=bool)
        return pd.DataFrame({"race_id": test[_RACE].astype(str), "horse_id": test[_HORSE].astype(str),
                             "favorite_band": test[_SEGMENT].astype(str), "is_danger": flags.astype(bool)})
