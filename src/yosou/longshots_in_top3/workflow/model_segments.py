"""この予想の、学習データの分け方。"""

from __future__ import annotations

from yosou.shared.workflow import ModelSegments

from ..dataset import LONGSHOT_ZONE, LongshotZone

#: 中穴と大穴を分けて学ぶ（既存モデルの修正計画の 1「穴馬の3着以内」）。全体で確率の高い馬を選ぶと、もともと来やすい
#: 中穴が選ばれやすいので、区分ごとに別のモデルにして、それぞれの中で候補を選べるようにする。
#: モデルは ``<置き場所>/mid/<時点>/``（中穴）と ``<置き場所>/big/<時点>/``（大穴）に置く。
SEGMENTS = ModelSegments(LONGSHOT_ZONE, {LongshotZone.MID.label: "mid", LongshotZone.BIG.label: "big"})
