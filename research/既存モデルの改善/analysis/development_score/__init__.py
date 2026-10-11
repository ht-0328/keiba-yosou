"""展開スコア（まとまり S）を全頭の3着以内の予想に足して、時点ごとに7つの区切りで比べる部品（入口は ``development_score_check.py``）。

元の表は、展開の予想の確かめ（``pace_forecast``）が作った時点ごとの表（P の 20列を持つ）。P のうち先頭・先団・中団・後方・ハイ・スローの確率と、
予想のパッケージの ``yosou.development_score``（表 G はレースの年ごとに、その年より前のレースだけで作る）で展開スコアの 5列を足す。
今の予想の予測は、木曜は展開の予想を足した作り方（本番）、前日は対戦レーティングを足した作り方（本番）、当日は今の作り方。

| 名前 | 仕事 |
|---|---|
| ``ScoreTable``・``SCORE_TABLES`` | S を足す元の表と、時点ごとの足した表の名前 |
| ``ScoreTableBuilder`` | 元の表の P の列と表 G の材料から、S の 5列を足す |
| ``SCORE_COMPARISONS``・``SCORE_VARIANTS`` | 時点と目的変数（3着以内・1着）ごとの比べ方（今の予想と、S を足したもの）。回す作り方も同じ並び |
"""

from .score_table_builder import ScoreTableBuilder
from .score_tables import SCORE_TABLES, ScoreTable, score_table_named
from .score_variants import SCORE_COMPARISONS, SCORE_VARIANTS, ScoreComparisonSpec

__all__ = ["ScoreTableBuilder", "ScoreTable", "SCORE_TABLES", "score_table_named", "SCORE_COMPARISONS", "SCORE_VARIANTS", "ScoreComparisonSpec"]
