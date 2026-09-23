"""候補の選び方（1レースの runners から、列に置く馬番を返す）。どれも ``CandidatePicker`` を守る。

| クラス | 仕事 |
|---|---|
| ``CandidatePicker`` | 決まり（インターフェース）。``pick(runners, count, taken)`` で馬番の並びを返す |
| ``FormRankPicker`` | 近走と適性モデルの「3着以内に入る確率」の高い順（``skip`` で上位を飛ばして対抗にする） |
| ``LongshotRankPicker`` | 穴馬モデルの「3着以内に入る確率」の高い順（穴馬だけ。中穴・大穴で絞れる） |
| ``PopularityPicker`` | 人気順位の範囲（1〜3番人気 など）を人気の順に |
| ``MidPopularityByLongshotPicker`` | 人気順位の範囲の中を、穴馬モデルの確率の高い順に |
| ``CombinedPicker`` | いくつかの選び方を順に当てて、1つの列にする |
"""

from .candidate_picker import CandidatePicker
from .combined_picker import CombinedPicker
from .form_rank_picker import FormRankPicker
from .longshot_rank_picker import LongshotRankPicker
from .mid_popularity_by_longshot_picker import MidPopularityByLongshotPicker
from .popularity_picker import PopularityPicker

__all__ = [
    "CandidatePicker", "FormRankPicker", "LongshotRankPicker", "PopularityPicker",
    "MidPopularityByLongshotPicker", "CombinedPicker",
]
