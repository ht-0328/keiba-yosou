"""傾向の組: 既存の4つの予想を、展開の予想の材料にする（設計書 01 の「流れ」・04 の「tendency/」）。

「このメンバーで、この馬は 3着以内に入りそうか」「人気馬が危ないか」「穴馬が来そうか」「レースが荒れそうか」を
既存の予想のモデルで出し、その傾向に合う展開（前半・後半）と着順を予想するために、前半・後半・着順の予想の特徴量（V）に入れる。
既存の予想は、それぞれの予想の学習データ・特徴量・目的変数・基準・区分をそのまま使い、期間だけを年ごとに変えて学習し直す。

| 名前 | 仕事 |
|---|---|
| ``TendencySource``・``TendencySpec`` | 材料にする既存の4つの予想と、その決めごと（学習データの作り方・時点・単位） |
| ``TendencyUnit`` | 既存の予想が別々に学ぶ1つのモデル（区分・券種ごと）の決めごとと、学習・予測 |
| ``TendencyOutput``・``ProbabilityOutput``・``UpsetOutput`` | 確率を、傾向の組の予測の列にする決まり |
| ``UnitTableCombiner`` | 単位ごとの予測の表を、1つの既存の予想の表にまとめる |
| ``TendencyDatasets`` | 既存の予想ごとの学習データの束 |
| ``TendencyFitter`` | 既存の予想を、決めた期間で学習し、予測する年を予測する |
| ``TendencyModelStore`` | 既存の予想の、単位ごと・時点ごとの学習済みモデルを読み書きする |
| ``TendencyForecaster`` | 1レースを、保存した既存の予想のモデルで予測する |
"""

from .probability_output import ProbabilityOutput
from .tendency_datasets import TendencyDatasets
from .tendency_fitter import TendencyFitter, TendencySink
from .tendency_forecaster import TendencyForecaster
from .tendency_model_store import TENDENCY_FOLDER, TendencyModelStore
from .tendency_output import TendencyOutput
from .tendency_source import TendencySource, TendencySpec
from .tendency_unit import TendencyUnit
from .unit_table_combiner import UnitTableCombiner
from .upset_output import UpsetOutput

__all__ = [
    "TendencySource", "TendencySpec", "TendencyUnit", "TendencyOutput", "ProbabilityOutput", "UpsetOutput",
    "UnitTableCombiner", "TendencyDatasets", "TendencyFitter", "TendencySink", "TendencyModelStore", "TendencyForecaster", "TENDENCY_FOLDER",
]
