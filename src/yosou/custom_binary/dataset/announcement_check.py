"""予測の前に、選んだ特徴量に要る今回の情報（発表・取得済みか）がそろっているかを確かめる。"""

import pandas as pd

from yosou.shared.feature.value_types import as_numbers

from ..extra_data.extra_data_loader import SOURCES
from ..feature.builder import SelectedFeatureBuilder

# 過去走の欠損と、今回の未発表情報は区別する。依存項目にも同じ確認を適用する。
ANNOUNCED_COLUMNS = {
    "枠番": "frame_no", "馬番": "horse_no", "馬体重": "body_weight", "馬体重の増減": "body_weight",
    "単勝オッズ": "win_odds", "オッズから見た勝率": "win_odds", "オッズから見た3着以内率": "win_odds",
    "人気順位": "popularity",
}
GOING_FEATURES = {
    "馬場状態", "同じ芝ダ・馬場状態での通算の出走数", "同じ芝ダ・馬場状態での通算の3着以内の数",
}
#: 馬場状態が発表済みのときの値。
KNOWN_GOINGS = ["良", "稍重", "重", "不良"]


class AnnouncementCheck:
    """足りなければ、取り込み方を案内して ``ValueError`` で止める。確かめるのは次の3つ。

    追加の元データ（券種オッズ）が取り込まれているか。``odds_baseline`` なら全頭の単勝オッズがあるか。
    選んだ特徴量（依存項目・条件を含む）が使う馬番・馬体重・オッズ・人気・馬場状態が発表済みか。
    """

    def __init__(self, builder: SelectedFeatureBuilder, odds_baseline: bool) -> None:
        self._builder = builder
        self._odds_baseline = odds_baseline

    def check(self, rows: pd.DataFrame) -> None:
        for source in self._builder.sources:
            self._check_source(rows, source)
        if self._odds_baseline and (as_numbers(rows["win_odds"]).isna() | as_numbers(rows["win_odds"]).le(0)).any():
            raise ValueError("odds_baselineに必要な単勝オッズが未取得です。速報を取り込むか--oddsで全頭分を指定してください")
        for name in self._builder.order:
            self._check_feature(rows, name)

    def _check_source(self, rows: pd.DataFrame, source: str) -> None:
        missing = [column for column in SOURCES[source].columns if rows[column].isna().all()]
        if missing:
            raise ValueError(
                f"{source}が未取得です（{', '.join(missing)}）。発売中のレースの券種オッズは、"
                "jvdata-storeで全賭式のオッズを取り込んでから予想してください"
            )

    def _check_feature(self, rows: pd.DataFrame, name: str) -> None:
        if name in ANNOUNCED_COLUMNS and self._missing(rows[ANNOUNCED_COLUMNS[name]]):
            raise ValueError(
                f"{name}に必要な情報が未取得です。発表後にjvdata-storeで速報を取り込むか、"
                "人気・オッズなら--pops・--oddsを指定してください"
            )
        if name in GOING_FEATURES and not rows["condition"].isin(KNOWN_GOINGS).all():
            raise ValueError(f"{name}に必要な馬場状態が未取得です。jvdata-storeで速報を取り込んでください")

    def _missing(self, column: pd.Series) -> bool:
        values = as_numbers(column)
        return bool((values.isna() | values.le(0)).any())
