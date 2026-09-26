"""設定を固定して学習・予想・テスト評価を行う。"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from 共通 import db
from 共通.render import Table

from yosou.shared.dataset import OddsInput, OddsResolver, PopularityApplier, PopularityInput, TrainingData
from yosou.shared.ml_model import MEMBER_TYPES, EnsembleModel
from yosou.shared.place_value import PlacePriceEstimator
from yosou.shared.repository import AnnouncedOddsRepository

from .dataset import CustomDataset
from .evaluation import HISTORICAL_NOTE, PAYBACK_NOTE, evaluate, fitted_place_price, paybacks, prediction_values
from .feature.registry import FeatureRegistry
from .model_store import ModelStore, PROJECT_ROOT, write_json
from .settings import ModelSettings


def fit(data: TrainingData, settings: ModelSettings) -> tuple[EnsembleModel, TrainingData, TrainingData]:
    """学習期間で学び、検証期間で早期終了を決める。保存はしない（探索で何通りも試すときに使う）。"""
    period = settings.period
    train = data.between(period.train_first_day, period.valid_first_day)
    valid = data.between(period.valid_first_day, period.test_first_day)
    for name, part in (("学習", train), ("検証", valid)):
        if not len(part):
            raise ValueError(f"{name}データが空です。期間・人気範囲・条件を確認してください")
        if part.label.nunique() != 2:
            raise ValueError(f"{name}データの正解が1クラスだけです。期間・人気範囲・条件を広げてください")
    expected = list(settings.selected)
    if list(data.features.columns) != expected:
        raise ValueError("学習データの特徴量が指定と違います")
    if (data.baseline is not None) != settings.odds_baseline:
        raise ValueError("学習データの基準確率（オッズ）の有無が設定のodds_baselineと違います")
    if not train.features.nunique(dropna=False).gt(1).any():
        raise ValueError("学習データの特徴量がすべて同じ値です。変化のある項目を選んでください")
    models = [model_type.from_settings(settings.parameters).fit(train, valid) for model_type in MEMBER_TYPES]
    return EnsembleModel(models), train, valid


def report(ensemble: EnsembleModel, data: TrainingData, target: str, train: TrainingData) -> dict:
    """確率の当たり具合と、その確率で買った回収率。複勝の想定払戻倍率は ``train``（学習期間）の払戻から求める。"""
    probability = ensemble.predict_proba(data) if len(data) else np.array([])
    place_price = fitted_place_price(train)
    return {"scores": evaluate(ensemble, data), "paybacks": paybacks(data, probability, target, place_price)}


def fit_and_save(data: TrainingData, settings: ModelSettings, registry: FeatureRegistry, store: ModelStore) -> dict:
    store.check_new()
    ensemble, train, valid = fit(data, settings)
    validation = report(ensemble, valid, settings.target, train)
    store.save(settings, registry, list(ensemble.members), validation, {"train": len(train), "validation": len(valid)},
               fitted_place_price(train))
    return validation


def train(config: Path, database: Path | None, registry: FeatureRegistry) -> list[Table]:
    settings = ModelSettings.load(config, registry)
    store = ModelStore(PROJECT_ROOT / "reports" / "custom_binary" / settings.name)
    store.check_new()
    with db.open_db(database) as con:
        data = CustomDataset(con, settings, registry).training()
    # 元DBは読み終えたら閉じる。モデルの学習中にDBロックを保持しない。
    validation = fit_and_save(data, settings, registry, store)
    summary = Table(["項目", "値"], [
        ["保存先", str(store.root)], ["目的", settings.target], ["時点", settings.timing.label],
        ["特徴量数", len(settings.selected)], ["特徴量", " / ".join(settings.selected)],
        ["人気範囲", f"{settings.popularity.minimum or 1}〜{settings.popularity.maximum or '上限なし'}"],
        ["条件", settings.conditions.label()],
        ["オッズの基準", "あり" if settings.odds_baseline else "なし"],
    ], title="学習完了")
    # 検証期間は早期終了の判定にも使ったので、未学習の成績は evaluate（テスト期間）で見る。
    note = "検証期間は早期終了の判定に使ったため、成績はやや良く出る。" + HISTORICAL_NOTE
    return [
        summary, Table.from_records(validation["scores"], title="検証期間の成績", note=note),
        Table.from_records(validation["paybacks"], title="検証期間の回収率", note=PAYBACK_NOTE),
    ]


@dataclass(frozen=True)
class LoadedModel:
    """予想に使う、保存したモデル一式（設定・2つのモデルの平均・複勝の想定払戻倍率）。"""

    settings: ModelSettings
    ensemble: EnsembleModel
    place_price: PlacePriceEstimator | None

    @classmethod
    def load(cls, models: Path, registry: FeatureRegistry) -> "LoadedModel":
        store = ModelStore(models)
        settings, ensemble = store.load(registry)
        return cls(settings, ensemble, store.place_price())


def predict(race_id: str, models: Path, database: Path | None, registry: FeatureRegistry,
            pops: list[str] | None = None, odds: list[str] | None = None) -> Table:
    model = LoadedModel.load(models, registry)
    with db.open_db(database) as con:
        return predict_race(con, race_id, model, registry, pops, odds)


def predict_race(con, race_id: str, model: LoadedModel, registry: FeatureRegistry,
                 pops: list[str] | None = None, odds: list[str] | None = None) -> Table:
    """開いた元DB で1レースを予想する。何レースも続けて予想するときは、DB とモデルを1回だけ開いて使い回す。"""
    settings = model.settings
    repository = AnnouncedOddsRepository(con)
    prices = OddsResolver(repository).resolve(race_id, OddsInput.of(odds) if odds is not None else None)
    popularity = PopularityApplier(repository).resolve(
        race_id, PopularityInput.of(pops) if pops is not None else None, prices,
    )
    data = CustomDataset(con, settings, registry).prediction(race_id, popularity, prices)
    probability_name = f"{settings.target}の確率"
    result = data.ids.copy()
    result[probability_name] = model.ensemble.predict_proba(data) if len(data) else []
    if len(data):
        values = prediction_values(result[probability_name].to_numpy(), settings.target, data.market, model.place_price)
        result = result.join(values)
    result = result.sort_values(probability_name, ascending=False, kind="stable")
    # pandasの欠損値を、CSV・JSONでも扱えるNoneへそろえる。
    records = result.astype(object).where(result.notna(), None).to_dict(orient="records")
    return Table.from_records(records, columns=list(result.columns), title="予想" if len(data) else "対象なし", note=(
        f"目的: {settings.target} / 時点: {settings.timing.label} / 特徴量: {len(settings.selected)}項目。"
        "人気は今回取得・指定した値。木曜の想定人気は実際の発売後の人気とは異なります。"
        "期待値は、勝利なら確率×単勝オッズ、馬券内・馬券外なら3着以内の確率×複勝の想定払戻倍率（今のオッズで計算。オッズは締め切りまで動く）。"
    ))


def test_evaluation(models: Path, database: Path | None, registry: FeatureRegistry) -> list[Table]:
    settings, ensemble = ModelStore(models).load(registry)
    with db.open_db(database) as con:
        data = CustomDataset(con, settings, registry).training()
    test = data.between(settings.period.test_first_day, None)
    train = data.between(settings.period.train_first_day, settings.period.valid_first_day)
    result = report(ensemble, test, settings.target, train)
    write_json(models / "test_evaluation.json", {
        "test_from": settings.period.test_first_day.isoformat(), "note": HISTORICAL_NOTE, **result,
    })
    return [
        Table.from_records(result["scores"], title="テスト期間の成績", note=HISTORICAL_NOTE),
        Table.from_records(result["paybacks"], title="テスト期間の回収率", note=PAYBACK_NOTE),
    ]
