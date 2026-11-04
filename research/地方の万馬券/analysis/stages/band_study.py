"""②危険な人気馬・③穴馬を学び、テスト期間を予測して、精度の表と予測の表を書く。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from yosou.local_form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH
from yosou.shared.dataset import PeriodSplitter, TrainingData, TrainingPeriod
from yosou.shared.dataset.column_names import FINISH, HORSE_ID, HORSE_NO, PLACE_PAYOUT, POPULARITY, RACE_DATE, RACE_ID, WIN_ODDS
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES, EnsembleModel
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow

from . import band_precision as cols
from .band_data import BandData
from .band_precision import DangerPrecision, LongshotPrecision
from .markdown_table import markdown_table
from .training_data_cache import LocalTrainingDataCache

#: 段の名前。
DANGER, LONGSHOT = "危険な人気馬", "穴馬"
STAGES: tuple[str, ...] = (DANGER, LONGSHOT)
#: ①の当日の予測の表（backtest が書いた pkl）の列。
_FORM_RACE, _FORM_HORSE_NO, _FORM_PROBABILITY = "レースID", "馬番", "確率"
#: 学ぶ時点（当日だけ。当日の馬場傾向 U と券種の支持 N を使う）。
TIMING = PredictionTiming.RACE_DAY


@dataclass(frozen=True)
class BandStudySettings:
    """``stage`` は ``DANGER`` か ``LONGSHOT``。``form_predictions`` は①の当日の予測の pkl（決め方「①の差」に使う）。
    ``cache_dir`` は①の学習データの pickle、``models_dir`` はこの段のモデルの置き場所。"""

    stage: str
    period: TrainingPeriod
    db: Path | None
    form_predictions: Path
    cache_dir: Path
    models_dir: Path

    @property
    def report_name(self) -> str:
        return f"{self.stage}の精度"


class BandStudy:
    """①の学習データ（U つき）から帯の学習データを作り、当日のモデル（LightGBM と CatBoost の平均）を学んでテスト期間を予測し、
    年ごとの当たり具合（ログ損失・AUC。市場の確率と比べる）と、消・穴の決め方ごとの精度の表を Markdown に、予測の表を pkl に書く。"""

    def __init__(self, settings: BandStudySettings) -> None:
        self._settings = settings

    def run(self, out_dir: Path) -> Path:
        s = self._settings
        data = LocalTrainingDataCache(s.cache_dir).load_or_build(s.db, s.period)
        band = BandData().favorites(data) if s.stage == DANGER else BandData().longshots(data)
        repository = ModelRepository(Path(s.models_dir) / s.stage, MEMBER_TYPES)
        TrainingWorkflow(None, s.period, repository, (TIMING,), DEFAULT_SETTINGS_PATH).train(band, None)
        predictions = self._predict(band, repository)
        out_dir = Path(out_dir)
        (out_dir / "predictions").mkdir(parents=True, exist_ok=True)
        predictions.to_pickle(out_dir / "predictions" / f"{s.stage}.pkl")
        path = out_dir / f"{s.report_name}.md"
        path.write_text(self._report(predictions), encoding="utf-8")
        return path

    def _predict(self, band: TrainingData, repository: ModelRepository) -> pd.DataFrame:
        """テスト期間の行の予測の表（``PREDICTION_COLUMNS``）。"""
        test = PeriodSplitter(self._settings.period).split(band).test.for_timing(TIMING)
        ensemble = EnsembleModel(repository.load(TIMING))
        probability = ensemble.combine(ensemble.predict_members(test))
        market = test.baseline.probabilities().to_numpy() if test.baseline is not None else np.full(len(test), np.nan)
        is_danger = self._settings.stage == DANGER
        table = pd.DataFrame({
            cols.RACE_ID: test.ids[RACE_ID].astype(str).to_numpy(), cols.RACE_DATE: pd.to_datetime(test.ids[RACE_DATE]).to_numpy(),
            cols.HORSE_ID: test.ids[HORSE_ID].astype(str).to_numpy(), cols.HORSE_NO: pd.to_numeric(test.ids[HORSE_NO], errors="coerce").to_numpy(),
            cols.POPULARITY: pd.to_numeric(test.evaluation[POPULARITY], errors="coerce").to_numpy(),
            cols.FINISH: pd.to_numeric(test.evaluation[FINISH], errors="coerce").to_numpy(),
            cols.PLACE_PAYOUT: pd.to_numeric(test.evaluation[PLACE_PAYOUT], errors="coerce").to_numpy(),
            cols.WIN_ODDS: pd.to_numeric(test.evaluation[WIN_ODDS], errors="coerce").to_numpy(),
            cols.P_MODEL: np.asarray(probability, dtype="float64"), cols.P_MARKET: market,
            "_label": test.label.to_numpy().astype(int),
        })
        table[cols.MARKET_TOP3] = 1.0 - table[cols.P_MARKET] if is_danger else table[cols.P_MARKET]
        form = pd.read_pickle(self._settings.form_predictions)
        form = pd.DataFrame({cols.RACE_ID: form[_FORM_RACE].astype(str), cols.HORSE_NO: pd.to_numeric(form[_FORM_HORSE_NO], errors="coerce"),
                             cols.P3_FORM: pd.to_numeric(form[_FORM_PROBABILITY], errors="coerce")}).drop_duplicates([cols.RACE_ID, cols.HORSE_NO])
        return table.merge(form, on=[cols.RACE_ID, cols.HORSE_NO], how="left")[[*cols.PREDICTION_COLUMNS, "_label"]]

    def _report(self, predictions: pd.DataFrame) -> str:
        s = self._settings
        precision = DangerPrecision().table(predictions) if s.stage == DANGER else LongshotPrecision().table(predictions)
        what = "消（1レース1頭）" if s.stage == DANGER else "穴（中穴 4〜7番人気・大穴 8番人気以下から3頭まで）"
        return "\n\n".join([
            f"# 地方の万馬券: {s.report_name}",
            f"学習 {s.period.train_first_day}〜（検証 {s.period.valid_first_day}〜）、テスト {s.period.test_first_day}〜。当日のモデル（①と同じ材料 ＋ 当日の馬場傾向 U）。",
            "### 1. 当たり具合（年ごと。モデルの確率と、オッズから見た確率）", markdown_table(self._accuracy(predictions)),
            f"### 2. {what}の決め方ごとの精度（年ごと）", markdown_table(precision),
            "「①の差」は全頭の予想①の3着以内の確率と市場の3着以内率の差、「②③の差」はこの段のモデルの確率と、オッズから見た同じ確率の差。"
            "複勝回収率は 1点 100円で買ったときの払戻 ÷ 投資。",
        ]) + "\n"

    def _accuracy(self, predictions: pd.DataFrame) -> pd.DataFrame:
        rows = []
        year = pd.to_datetime(predictions[cols.RACE_DATE]).dt.year
        for y, part in predictions.groupby(year, sort=True):
            label = part["_label"].to_numpy()
            rows.append({cols.YEAR: int(y), "行数": len(part), "ログ損失（モデル）": self._log_loss(label, part[cols.P_MODEL]),
                         "ログ損失（オッズ）": self._log_loss(label, part[cols.P_MARKET]),
                         "AUC（モデル）": self._auc(label, part[cols.P_MODEL]), "AUC（オッズ）": self._auc(label, part[cols.P_MARKET])})
        return pd.DataFrame(rows)

    def _log_loss(self, label: np.ndarray, probability: pd.Series) -> float:
        p = probability.to_numpy(dtype="float64")
        ok = ~np.isnan(p)
        return float(log_loss(label[ok], np.clip(p[ok], 1e-6, 1 - 1e-6), labels=[0, 1])) if ok.any() and len(set(label[ok])) > 1 else float("nan")

    def _auc(self, label: np.ndarray, probability: pd.Series) -> float:
        p = probability.to_numpy(dtype="float64")
        ok = ~np.isnan(p)
        return float(roc_auc_score(label[ok], p[ok])) if ok.any() and len(set(label[ok])) > 1 else float("nan")
