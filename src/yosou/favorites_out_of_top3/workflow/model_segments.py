"""この予想の、学習データの分け方。"""

from __future__ import annotations

from yosou.shared.workflow import ModelSegments

from ..dataset import FAVORITE_BAND, FavoriteBand

#: 1番人気・2〜3番人気・4〜5番人気に分けて学ぶ（既存モデルの修正計画の 1「人気馬の4着以下」）。まとめて学ぶと、
#: 普通に負けやすい4・5番人気ばかりを危険としやすいので、人気帯ごとに別のモデルにする。
#: モデルは ``<置き場所>/<first・second_third・fourth_fifth>/<時点>/`` に置く。
SEGMENTS = ModelSegments(FAVORITE_BAND, {band.label: band.key for band in FavoriteBand})
