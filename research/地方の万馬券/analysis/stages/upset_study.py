"""④荒れ具合を券種ごとに学び、テスト期間の当たり具合と、荒れそうなレースを選ぶ精度の表と予測の表を書く。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from yosou.shared.dataset import PeriodSplitter, TrainingData, TrainingPeriod
from yosou.shared.dataset.column_names import RACE_DATE, RACE_ID, RACE_NO, VENUE
from yosou.shared.evaluation import ClassModelEvaluator
from yosou.shared.feature import FIELD_SIZE as FIELD_SIZE_FEATURE, PredictionTiming
from yosou.shared.ml_model import CLASS_MEMBER_TYPES, EnsembleModel
from yosou.shared.repository import ModelRepository
from yosou.shared.setting import HyperparameterSettings
from yosou.shared.workflow import TrainingWorkflow
from yosou.upset_level.dataset import BetType, UpsetLevel
from yosou.upset_level.feature import odds_shape_features
from yosou.upset_level.setting import DEFAULT_SETTINGS_PATH

from .local_upset_rule import LocalUpsetRule
from .markdown_table import markdown_table
from .market_only_baseline import MarketOnlyBaseline
from .upset_data import LocalRaceTrainingDataCache

#: 段の名前と、学ぶ時点（当日だけ）。
UPSET = "荒れ具合"
TIMING = PredictionTiming.RACE_DAY
#: 市場の割れ方だけの基準に使う列（オッズの形 B の 10個と頭数）。
MARKET_ONLY_NAMES: tuple[str, ...] = (*odds_shape_features.NAMES, FIELD_SIZE_FEATURE)
#: 荒れそうなレースを選ぶ割合（大荒れ以上の確率の上位）。
TOP_SHARES: tuple[float, ...] = (0.05, 0.10, 0.20, 0.30)
#: 予測の表の列（クラスごとの確率の列は ``UpsetLevel.labels()``）。
BIG_OR_MORE, MID_OR_MORE = "大荒れ以上の確率", "中荒れ以上の確率"
YEAR = "年"


@dataclass(frozen=True)
class UpsetStudySettings:
    period: TrainingPeriod
    con_factory: Callable[[], object]
    cache_dir: Path
    models_dir: Path
    bets: tuple[BetType, ...] = tuple(BetType)

    @property
    def report_name(self) -> str:
        return f"{UPSET}の精度"


class UpsetStudy:
    """1行 = 1レースの学習データ（``LocalRaceTrainingDataCache``）で、券種ごとに当日のモデル（LightGBM と CatBoost の平均。4クラス）を学び、
    テスト期間の 年ごとのログ損失・AUC（クラスの割合だけの基準、市場の割れ方だけの基準と並べる）と、
    大荒れ以上の確率の上位 5〜30% のレースで実際に大荒れ以上だった割合（全体との倍率）を Markdown に、予測の表を pkl に書く。"""

    def __init__(self, settings: UpsetStudySettings) -> None:
        self._settings = settings
        self._rule = LocalUpsetRule()

    def run(self, out_dir: Path) -> Path:
        s = self._settings
        data = LocalRaceTrainingDataCache(s.cache_dir, self._rule).load_or_build(s.con_factory, s.period)
        settings = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
        out_dir = Path(out_dir)
        (out_dir / "predictions").mkdir(parents=True, exist_ok=True)
        sections = [f"# 地方の万馬券: {s.report_name}",
                    f"学習 {s.period.train_first_day}〜（検証 {s.period.valid_first_day}〜）、テスト {s.period.test_first_day}〜。当日のモデル。"
                    "線引き: " + "、".join(f"{bet.label} {'/'.join(f'{yen:,}' for yen in self._rule.thresholds_of(bet))}円" for bet in BetType) + "。"]
        for bet in s.bets:
            labeled = data.with_label(bet.column_name)
            repository = ModelRepository(Path(s.models_dir) / UPSET / bet.key, CLASS_MEMBER_TYPES)
            TrainingWorkflow(None, s.period, repository, (TIMING,), DEFAULT_SETTINGS_PATH,
                             member_types=CLASS_MEMBER_TYPES, evaluator=ClassModelEvaluator()).train(labeled, None)
            split = PeriodSplitter(s.period).split(labeled)
            test = split.test.for_timing(TIMING)
            model = EnsembleModel(repository.load(TIMING)).predict_proba(test)
            market_only = MarketOnlyBaseline(settings, MARKET_ONLY_NAMES).fit_predict(
                type(split)(split.train.for_timing(TIMING), split.valid.for_timing(TIMING), test), test)
            shares = self._shares(split.train)
            predictions = self._predictions(test, model)
            predictions.to_pickle(out_dir / "predictions" / f"{UPSET}-{bet.key}.pkl")
            sections += [f"### {bet.label}: 当たり具合（年ごと）", markdown_table(self._accuracy(test, model, market_only, shares)),
                         f"### {bet.label}: 大荒れ以上の確率の上位で選んだレースの精度（年ごと）", markdown_table(self._lift(test, model, market_only))]
        path = out_dir / f"{s.report_name}.md"
        path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
        return path

    def _shares(self, train: TrainingData) -> np.ndarray:
        counts = train.label.astype(int).value_counts()
        values = np.array([counts.get(label, 0) for label in train.class_labels], dtype=float)
        return values / values.sum()

    def _predictions(self, test: TrainingData, model: np.ndarray) -> pd.DataFrame:
        table = pd.DataFrame({
            "race_id": test.ids[RACE_ID].astype(str).to_numpy(), "race_date": pd.to_datetime(test.ids[RACE_DATE]).to_numpy(),
            "venue": test.ids[VENUE].to_numpy() if VENUE in test.ids.columns else None,
            "race_no": test.ids[RACE_NO].to_numpy() if RACE_NO in test.ids.columns else None,
            "label": test.label.to_numpy().astype(int),
        })
        for level in UpsetLevel:
            table[level.label] = model[:, level.value]
        table[MID_OR_MORE] = model[:, UpsetLevel.MID.value:].sum(axis=1)
        table[BIG_OR_MORE] = model[:, UpsetLevel.BIG.value:].sum(axis=1)
        return table

    def _accuracy(self, test: TrainingData, model: np.ndarray, market_only: np.ndarray, shares: np.ndarray) -> pd.DataFrame:
        label = test.label.to_numpy().astype(int)
        year = pd.to_datetime(test.ids[RACE_DATE]).dt.year.to_numpy()
        rows = []
        for y in sorted(set(year)):
            rows_in = year == y
            constant = np.tile(shares, (int(rows_in.sum()), 1))
            rows.append({YEAR: int(y), "レース数": int(rows_in.sum()),
                         "ログ損失（④）": self._log_loss(label[rows_in], model[rows_in]),
                         "ログ損失（市場の割れ方だけ）": self._log_loss(label[rows_in], market_only[rows_in]),
                         "ログ損失（クラスの割合）": self._log_loss(label[rows_in], constant),
                         "AUC 大荒れ以上（④）": self._auc(label[rows_in], model[rows_in], UpsetLevel.BIG.value),
                         "AUC 大荒れ以上（市場の割れ方だけ）": self._auc(label[rows_in], market_only[rows_in], UpsetLevel.BIG.value),
                         "AUC 中荒れ以上（④）": self._auc(label[rows_in], model[rows_in], UpsetLevel.MID.value),
                         "AUC 中荒れ以上（市場の割れ方だけ）": self._auc(label[rows_in], market_only[rows_in], UpsetLevel.MID.value)})
        return pd.DataFrame(rows)

    def _lift(self, test: TrainingData, model: np.ndarray, market_only: np.ndarray) -> pd.DataFrame:
        label = test.label.to_numpy().astype(int)
        year = pd.to_datetime(test.ids[RACE_DATE]).dt.year.to_numpy()
        rows = []
        for y in sorted(set(year)):
            rows_in = year == y
            big = label[rows_in] >= UpsetLevel.BIG.value
            mid = label[rows_in] >= UpsetLevel.MID.value
            for name, proba in (("④", model[rows_in]), ("市場の割れ方だけ", market_only[rows_in])):
                p_big = proba[:, UpsetLevel.BIG.value:].sum(axis=1)
                p_mid = proba[:, UpsetLevel.MID.value:].sum(axis=1)
                for share in TOP_SHARES:
                    count = max(1, int(round(len(p_big) * share)))
                    top_big = np.argsort(-p_big, kind="stable")[:count]
                    top_mid = np.argsort(-p_mid, kind="stable")[:count]
                    rows.append({YEAR: int(y), "予想": name, "上位の割合": share, "レース数": count,
                                 "大荒れ以上の割合（選んだ）": float(big[top_big].mean()), "大荒れ以上の割合（全体）": float(big.mean()),
                                 "倍率（大荒れ以上）": float(big[top_big].mean() / big.mean()) if big.mean() > 0 else np.nan,
                                 "中荒れ以上の割合（選んだ）": float(mid[top_mid].mean()), "中荒れ以上の割合（全体）": float(mid.mean())})
        return pd.DataFrame(rows)

    def _log_loss(self, label: np.ndarray, proba: np.ndarray) -> float:
        return float(log_loss(label, np.clip(proba, 1e-6, 1.0), labels=list(UpsetLevel.class_labels())))

    def _auc(self, label: np.ndarray, proba: np.ndarray, from_class: int) -> float:
        truth = label >= from_class
        if truth.all() or not truth.any():
            return float("nan")
        return float(roc_auc_score(truth, proba[:, from_class:].sum(axis=1)))
