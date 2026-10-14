"""馬体重の表: 増減の帯 × 前走からの間隔 × 馬齢ごとに「実際の3着以内率 − 市場から見た3着以内率」を数え、馬ごとの体重の割引にする
（設計書「買うレースと買い目を決める」06 の 2）。

市場は発表された馬体重を見てオッズを動かすので、「大幅減なら割り引く」と決め打ちすると二重に引く。表を市場との差で作れば、
市場が割り引き足りない分だけが残る。休み明けと若い馬を分けるのは、休み明けの増加や3歳の増加は回復や成長のことが多いため。
全頭の予想の特徴量（まとまり V。1個）として足すほか、出馬表に「体重の割引」を見せ、危険な人気馬の理由にする。

| 名前 | 仕事 |
|---|---|
| ``WeightRunRepository`` | 表の元になる、中央・平地の全出走（増減・前走からの日数・馬齢・単勝オッズ・着順）を読む |
| ``WeightBands`` | 増減・間隔・馬齢を帯に分ける |
| ``WeightRuns`` | 帯・市場から見た3着以内率・実際の3着以内を出走の表にそろえる（表の材料） |
| ``WeightTableBuilder``・``WeightTable`` | 表 W を作る（件数の少ないマスは同じ増減の帯の全体の値に寄せる）・引く |
| ``WeightTableRepository`` | 表 W の pickle のファイルと元DB の印（``stamp.json``）を書く・読む（``repository/``） |
| ``WeightTableStore`` | 表 W を ``reports/馬体重の表/cache/`` にとっておき、元DB が変わったら作り直す |
| ``WeightDiscountColumns`` | 特徴量の表の増減・日数・馬齢から表 W を引いて、体重の割引の列を作る |
| ``WeightJudge`` | W を線（−0.02）で「体重の割引」と判定する |
| ``RaceWeightDiscountAttacher`` | 1レースの予測用データに V を足す関数の形（全頭の予想の予測の流れに渡す） |
| ``YearlyWeightDiscount`` | 学習データに、年ごとに「その年より前のレースだけで作った表 W」で V を付ける（リークを防ぐ） |
| ``WeightDiscountAttachment`` | 学習データ・予測用データに V の列を足す（表 W を渡す） |
| ``WeightDiscountFreeData`` | 学習データ・予測用データから V を外す |
| ``WEIGHT_DISCOUNT_FEATURES`` | 体重の割引を予想の特徴量にするときの一覧（まとまり V。1個） |
"""

from .features import WEIGHT_DISCOUNT_FEATURES, WEIGHT_DISCOUNT_NAMES
from .race_weight_discount_attacher import RaceWeightDiscountAttacher
from .repository import WeightRunRepository, WeightTableRepository
from .weight_bands import WeightBands
from .weight_discount_attachment import WeightDiscountAttachment
from .weight_discount_columns import WeightDiscountColumns
from .weight_discount_free_data import WeightDiscountFreeData
from .weight_judge import DEFAULT_LINE, WeightJudge
from .weight_runs import WeightRuns
from .weight_table import WeightTable
from .weight_table_builder import POOL_WEIGHT, WeightTableBuilder
from .weight_table_store import DEFAULT_CACHE_FOLDER, WeightTableStore, weight_cache_folder_beside
from .yearly_weight_discount import YearlyWeightDiscount

__all__ = [
    "WeightRunRepository", "WeightBands", "WeightRuns", "WeightTableBuilder", "WeightTable", "WeightTableRepository", "WeightTableStore", "WeightDiscountColumns",
    "WeightJudge", "RaceWeightDiscountAttacher", "YearlyWeightDiscount", "WeightDiscountAttachment", "WeightDiscountFreeData",
    "WEIGHT_DISCOUNT_FEATURES", "WEIGHT_DISCOUNT_NAMES", "DEFAULT_LINE", "POOL_WEIGHT", "DEFAULT_CACHE_FOLDER", "weight_cache_folder_beside",
]
