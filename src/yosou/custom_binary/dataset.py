"""全頭で特徴量を作り、最後に人気範囲で絞る。元DBの取得処理は共通部品を使う。"""

import pandas as pd

from yosou.shared.dataset import (
    FlatRunnerFilter, HistoryRecordsLoader, PredictionData, RaceRecordsLoader, TrainingData,
)
from yosou.shared.dataset import column_names as columns
from yosou.shared.feature import EntryColumns, FeatureCatalog
from yosou.shared.feature.value_types import as_numbers
from yosou.shared.repository import TargetScope

from .extra_data.extra_data_loader import SOURCES, ExtraDataLoader, race_relation
from .feature.builder import SelectedFeatureBuilder
from .feature.registry import FeatureRegistry
from .odds_baseline import OddsBaseline
from .settings import ModelSettings, PopularityRange


IDS = EntryColumns({
    columns.RACE_ID: "race_id", columns.RACE_DATE: "race_date", columns.HORSE_ID: "horse_id",
    columns.HORSE_NO: "horse_no", columns.HORSE_NAME: "horse_name",
})
# 回収率の計算に使う。モデルには渡さない。
EVALUATION = EntryColumns({
    columns.FINISH: "finish", columns.POPULARITY: "popularity", columns.WIN_ODDS: "win_odds",
    columns.WIN_PAYOUT: "win_payout", columns.PLACE_PAYOUT: "place_payout", columns.PLACE_ODDS_LOW: "place_odds_low",
    columns.FIELD_SIZE: "field_size",
})
USED_POPULARITY = "使用した人気"
#: 予測のときの期待値の材料（その時点のオッズと頭数）。モデルには渡さない。
MARKET = EntryColumns({"単勝オッズ": "win_odds", "複勝オッズ（最低）": "place_odds_low"})
MARKET_FIELD_SIZE = "出走頭数"
MARKET_WHOLE_FIELD = "全頭が対象"

# 過去走の欠損と、今回の未発表情報は区別する。依存項目にも同じ確認を適用する。
ANNOUNCED_COLUMNS = {
    "枠番": "frame_no", "馬番": "horse_no", "馬体重": "body_weight", "馬体重の増減": "body_weight",
    "単勝オッズ": "win_odds", "オッズから見た勝率": "win_odds", "オッズから見た3着以内率": "win_odds",
    "人気順位": "popularity",
}
GOING_FEATURES = {
    "馬場状態", "同じ芝ダ・馬場状態での通算の出走数", "同じ芝ダ・馬場状態での通算の3着以内の数",
}


def popularity_mask(rows: pd.DataFrame, bounds: PopularityRange) -> pd.Series:
    if not bounds.bounded:
        return pd.Series(True, index=rows.index)
    popularity = as_numbers(rows["popularity"])
    invalid = popularity.isna() | (popularity < 1) | (popularity % 1 != 0)
    if invalid.any():
        raise ValueError(f"人気範囲の判定に必要な人気が不明・不正です（{int(invalid.sum())}頭）。予想時は--popsで指定してください")
    kept = pd.Series(True, index=rows.index)
    if bounds.minimum is not None:
        kept &= popularity >= bounds.minimum
    if bounds.maximum is not None:
        kept &= popularity <= bounds.maximum
    return kept


def targets(rows: pd.DataFrame, target: str) -> pd.DataFrame:
    finish = as_numbers(rows["finish"])
    top3 = finish.between(1, 3)
    labels = {"馬券内": top3, "馬券外": ~top3, "勝利": finish.eq(1)}
    return pd.DataFrame({target: labels[target].astype(int)}, index=rows.index)


def select_training_data(rows: pd.DataFrame, frame: pd.DataFrame, settings: ModelSettings,
                         catalog: FeatureCatalog) -> TrainingData:
    """全頭で作った特徴量の表から、人気範囲と条件に当てはまる馬の学習データを作る。

    探索では全特徴量の表を1回だけ作り、設定ごとにここで絞る。``frame`` は選んだ特徴量と条件の列を含む表。
    オッズの基準は、絞る前の全頭（同じレースの全馬のオッズ）で作る。
    """
    kept = rows[popularity_mask(rows, settings.popularity) & settings.conditions.mask(frame)]
    baseline = OddsBaseline(settings.target).build(rows).at(kept.index) if settings.odds_baseline else None
    return TrainingData(
        IDS.select(kept), frame.loc[kept.index, list(settings.selected)], targets(kept, settings.target),
        EVALUATION.select(kept), catalog, settings.target, baseline=baseline,
    )


class CustomDataset:
    def __init__(self, con, settings: ModelSettings, registry: FeatureRegistry) -> None:
        self.settings = settings
        self.builder = SelectedFeatureBuilder(registry, settings.selected, settings.timing, settings.conditions.names)
        self.history = HistoryRecordsLoader(con)
        self.races = RaceRecordsLoader(con)
        self.extra = ExtraDataLoader(con)

    def training(self) -> TrainingData:
        records = self.history.load(self.settings.period.warmup_first_day)
        rows = FlatRunnerFilter().apply(records.entries)
        rows = rows[rows["race_date"] >= pd.Timestamp(self.settings.period.train_first_day)]
        # 確定成績を読むが、正常出走で着順不明の行は負例にしない。
        resolved = as_numbers(rows["finish"]).ge(1) | rows["abnormal"].isin(["4", "5"])
        rows = rows[resolved]
        if rows.empty:
            raise ValueError("学習に使える確定成績がありません")
        rows = self.extra.attach(rows, TargetScope.since(self.settings.period.train_first_day).relation, self.builder.sources)
        frame = self.builder.build(records.with_entries(rows))
        return select_training_data(rows, frame, self.settings, self.builder.catalog)

    def prediction(self, race_id: str, popularity=None, odds=None) -> PredictionData:
        records = self.races.load(race_id, popularity, odds)
        if (records.entries["surface"] == "障害").any():
            raise ValueError("障害レースはこのモデルの対象外です")
        rows = FlatRunnerFilter().apply(records.entries)
        rows = self.extra.attach(rows, race_relation(race_id), self.builder.sources)
        kept = rows[popularity_mask(rows, self.settings.popularity)]
        if not kept.empty:
            self._check_announced(rows)
            frame = self.builder.build(records.with_entries(rows))
            kept = kept[self.settings.conditions.mask(frame.loc[kept.index])]
        ids = IDS.select(kept).assign(**{USED_POPULARITY: kept["popularity"]})
        # 3着以内の確率を頭数にそろえ直せるのは、同じレースの全頭が対象のときだけ。
        market = MARKET.select(kept).assign(**{MARKET_FIELD_SIZE: len(rows), MARKET_WHOLE_FIELD: len(kept) == len(rows)})
        baseline = None
        if kept.empty:
            features = pd.DataFrame(index=kept.index, columns=list(self.settings.selected))
        else:
            features = frame.loc[kept.index, list(self.settings.selected)]
            if self.settings.odds_baseline:
                baseline = OddsBaseline(self.settings.target).build(rows).at(kept.index)
        return PredictionData(ids, features, self.settings.timing, self.builder.catalog, baseline, market)

    def _check_announced(self, rows: pd.DataFrame) -> None:
        for source in self.builder.sources:
            missing = [column for column in SOURCES[source].columns if rows[column].isna().all()]
            if missing:
                raise ValueError(
                    f"{source}が未取得です（{', '.join(missing)}）。発売中のレースの券種オッズは、"
                    "jvdata-storeで全賭式のオッズを取り込んでから予想してください"
                )
        if self.settings.odds_baseline and (as_numbers(rows["win_odds"]).isna() | as_numbers(rows["win_odds"]).le(0)).any():
            raise ValueError("odds_baselineに必要な単勝オッズが未取得です。速報を取り込むか--oddsで全頭分を指定してください")
        for name in self.builder.order:
            if name in ANNOUNCED_COLUMNS:
                values = as_numbers(rows[ANNOUNCED_COLUMNS[name]])
                if (values.isna() | values.le(0)).any():
                    raise ValueError(
                        f"{name}に必要な情報が未取得です。発表後にjvdata-storeで速報を取り込むか、"
                        "人気・オッズなら--pops・--oddsを指定してください"
                    )
            if name in GOING_FEATURES and not rows["condition"].isin(["良", "稍重", "重", "不良"]).all():
                raise ValueError(f"{name}に必要な馬場状態が未取得です。jvdata-storeで速報を取り込んでください")
