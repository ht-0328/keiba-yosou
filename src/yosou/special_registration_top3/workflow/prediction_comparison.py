"""この予想と中央の木曜のモデルの予測を、同じレース・同じ馬で比べる。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from yosou.shared.dataset import HORSE_ID, RACE_ID
from yosou.shared.evaluation import ENSEMBLE_NAME
from yosou.shared.workflow.backtest_workflow import PREDICTION_COLUMNS

from .special_race_evaluation import WINDOW, SpecialRaceRows

#: 予測の表の列（レースID・馬ID・平均の確率・期間）と、テスト期間の行の印。
_RACE, _HORSE, _PROBABILITY, _PERIOD = PREDICTION_COLUMNS[0], PREDICTION_COLUMNS[2], PREDICTION_COLUMNS[4], PREDICTION_COLUMNS[6]
_TEST = "テスト"
#: 比べの表の列。
ROWS = "行数"
OURS_LOG_LOSS, THEIRS_LOG_LOSS, LOG_LOSS_GAP = "この予想のログ損失", "木曜のログ損失", "差（この予想 − 木曜）"
OURS_AUC, THEIRS_AUC = "この予想の AUC", "木曜の AUC"
COMPARISON_COLUMNS: tuple[str, ...] = (WINDOW, ROWS, OURS_LOG_LOSS, THEIRS_LOG_LOSS, LOG_LOSS_GAP, OURS_AUC, THEIRS_AUC)
_WHOLE = "全期間"
_EPSILON = 1e-6


class PredictionComparison:
    """この予想の特別競走の行の確率と、中央の木曜のモデルの予測の表（研究「既存モデルの改善」の7つの区切りの形）を、レースID と馬ID で
    突き合わせ、両方にある行だけで、区切りごと・全期間のログ損失と AUC を並べる（設計書 16 の 3）。

    木曜のモデルは材料が多いので、これより良いことは求めない。差は「木曜に出し直す価値がどれだけあるか」の目安（参考）。
    """

    def compare(self, ours: SpecialRaceRows, theirs: pd.DataFrame) -> pd.DataFrame:
        """列は ``COMPARISON_COLUMNS``。突き合わせられる行が無ければ空の表。"""
        if _PERIOD in theirs.columns:
            theirs = theirs[theirs[_PERIOD] == _TEST]
        mine = pd.DataFrame({
            _RACE: ours.data.ids[RACE_ID].astype(str).to_numpy(), _HORSE: ours.data.ids[HORSE_ID].astype(str).to_numpy(),
            WINDOW: self._windows_of(ours), "ours": ours.probabilities[ENSEMBLE_NAME], "label": ours.data.label.to_numpy(dtype=float),
        })
        others = theirs.assign(**{_RACE: theirs[_RACE].astype(str), _HORSE: theirs[_HORSE].astype(str)})
        others = others.drop_duplicates([_RACE, _HORSE])[[_RACE, _HORSE, _PROBABILITY]].rename(columns={_PROBABILITY: "theirs"})
        merged = mine.merge(others, on=[_RACE, _HORSE], how="inner").dropna(subset=["ours", "theirs"])
        if merged.empty:
            return pd.DataFrame(columns=list(COMPARISON_COLUMNS))
        groups = [(name, part) for name, part in merged.groupby(WINDOW, sort=False)]
        if len(groups) > 1:
            groups.append((_WHOLE, merged))
        return pd.DataFrame([self._row(name, part) for name, part in groups], columns=list(COMPARISON_COLUMNS))

    def _windows_of(self, ours: SpecialRaceRows) -> np.ndarray:
        """行ごとの区切りの名前（評価用の列に無ければ、全部「全期間」）。"""
        if WINDOW in ours.data.evaluation.columns:
            return ours.data.evaluation[WINDOW].to_numpy()
        return np.full(len(ours.data), _WHOLE, dtype=object)

    def _row(self, name: str, part: pd.DataFrame) -> list[object]:
        label = part["label"].to_numpy()
        ours = part["ours"].clip(_EPSILON, 1 - _EPSILON).to_numpy()
        theirs = part["theirs"].clip(_EPSILON, 1 - _EPSILON).to_numpy()
        ours_loss, theirs_loss = log_loss(label, ours, labels=[0, 1]), log_loss(label, theirs, labels=[0, 1])
        has_both = 0 < label.sum() < len(label)
        return [name, len(part), ours_loss, theirs_loss, ours_loss - theirs_loss,
                roc_auc_score(label, ours) if has_both else float("nan"), roc_auc_score(label, theirs) if has_both else float("nan")]
