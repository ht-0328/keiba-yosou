"""トラックバイアス: 当日の先に終わったレースで「市場の見立てより来た馬が、内か外か・前か後ろか」を数え、馬ごとの補正にする
（設計書「買うレースと買い目を決める」06 の 1）。

終わったレースごとに、残差（3着以内 − 市場から見た3着以内率）と内らしさ・前らしさの傾き（内の傾き・前の傾き）を出す。
対象のレースには、その日の先に終わった同じ馬場（競馬場 × 芝ダ × 内外回り）のレースの傾き（前の日のレースは 0.5 本）を、
過去の傾き（同じ馬場 × 開催の何日目 × 馬場状態の平均。件数の少ない日はこちらに寄せる）と混ぜて「使う傾き」にし、
馬ごとに B = 使う内の傾き × 内らしさ + 使う前の傾き × 予想の前らしさ（展開の予想④）を出す。B は3着以内の確率のポイント。
全頭の予想の特徴量（まとまり U。5個）として足す。

| 名前 | 仕事 |
|---|---|
| ``BiasRunRepository`` | 傾きの元になる、中央・平地の全出走（馬番・頭数・4コーナーの順位・単勝オッズ・着順）を読む |
| ``RaceEntryRepository`` | これから走る1レースの鍵と条件と出走馬（馬番・頭数）を読む |
| ``Positions`` | 馬番と頭数から内らしさ、位置から前らしさを出す |
| ``RaceSlopes`` | 終わったレースごとに、内の傾きと前の傾きを出す |
| ``PriorSlopeTableBuilder``・``PriorSlopeTable`` | 過去の傾きの表（同じ馬場 × 開催の何日目 × 馬場状態）を作る・引く |
| ``PriorSlopeTableRepository`` | レースごとの傾きと過去の傾きの表の pickle のファイルと元DB の印（``stamp.json``）を書く・読む（``repository/``） |
| ``PriorSlopeTableStore`` | レースごとの傾きと過去の傾きの表を ``reports/トラックバイアス/cache/`` にとっておき、元DB が変わったら作り直す |
| ``DaySlopes`` | 対象のレースごとに、当日の先に終わったレースと前の日のレースから当日の傾きとレース数を出す |
| ``UsedSlopes`` | 当日の傾きと過去の傾きを、レース数で混ぜる |
| ``BiasCorrection`` | 使う傾きと馬の位置から、馬ごとの補正 B（内の分・前の分・和）を出す |
| ``BiasJudge`` | B を線（±0.02）でバイアス向き・バイアス逆に分ける（出馬表の表示と、危険な人気馬の理由） |
| ``MemoizedPaceForecast`` | 同じレース・時点の展開の予測を1回だけ動かして使い回す |
| ``RaceBiasSource`` | これから走る1レースのバイアスの補正の表を作る（道具と、全頭の予想の予測の流れが使う） |
| ``RaceBiasAttacher`` | 1レースの補正の表を予測用データに足す関数の形（全頭の予想の予測の流れに渡す） |
| ``YearlyBias`` | 過去の出走に、年ごとに「その年より前のレースだけで作った過去の傾きの表」と先に終わったレースの傾きで補正を付ける（リークを防ぐ） |
| ``BiasHistory`` | 年ごとの確かめの展開の予測を読んで ``YearlyBias`` に渡す（研究と学習用） |
| ``BiasAttachment`` | 学習データ・予測用データに U の5列を足す |
| ``TrackBiasFreeData`` | 学習データ・予測用データから U を外す |
| ``TRACK_BIAS_FEATURES`` | トラックバイアスの補正を予想の特徴量にするときの一覧（まとまり U。5個） |
"""

from .bias_attachment import BiasAttachment
from .bias_correction import BiasCorrection
from .bias_free_data import TrackBiasFreeData
from .bias_history import BiasHistory
from .bias_judge import DEFAULT_LINE, BiasJudge
from .day_slopes import DaySlopes
from .features import TRACK_BIAS_FEATURES, TRACK_BIAS_NAMES
from .memoized_pace_forecast import MemoizedPaceForecast
from .positions import Positions
from .prior_slope_table import PriorSlopeTable
from .prior_slope_table_builder import POOL_WEIGHT, PriorSlopeTableBuilder
from .prior_slope_table_store import DEFAULT_CACHE_FOLDER, PriorSlopeTableStore, bias_cache_folder_beside
from .race_bias_attacher import RaceBiasAttacher
from .race_bias_source import RaceBiasSource
from .race_slopes import RaceSlopes
from .repository import BiasRunRepository, PriorSlopeTableRepository, RaceEntryRepository
from .used_slopes import PRIOR_WEIGHT, UsedSlopes
from .yearly_bias import YearlyBias

__all__ = [
    "BiasRunRepository", "RaceEntryRepository", "Positions", "RaceSlopes", "PriorSlopeTableBuilder", "PriorSlopeTable",
    "PriorSlopeTableRepository", "PriorSlopeTableStore", "DaySlopes", "UsedSlopes", "BiasCorrection", "BiasJudge", "MemoizedPaceForecast", "RaceBiasSource",
    "RaceBiasAttacher", "YearlyBias", "BiasHistory", "BiasAttachment", "TrackBiasFreeData", "TRACK_BIAS_FEATURES", "TRACK_BIAS_NAMES",
    "DEFAULT_LINE", "POOL_WEIGHT", "PRIOR_WEIGHT", "DEFAULT_CACHE_FOLDER", "bias_cache_folder_beside",
]
