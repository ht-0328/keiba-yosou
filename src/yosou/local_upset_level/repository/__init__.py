"""データの読み書きのうち、この予想だけのもの。

元DB を読むリポジトリ（出走・1レースの出走馬・払戻・オッズ）は ``yosou.shared.repository``・``yosou.track_bias.repository``、
学習したモデルの読み書きは ``yosou.shared.repository`` の ``ModelRepository``（券種ごとの置き場所は中央の ``model_repositories``）。

| クラス | 仕事 |
|---|---|
| ``PriorSlopeYearStore`` | 「その年の1月1日より前のレースだけで作った過去の傾きの表」を、年ごとに pickle でとっておく。無ければ元DB の全出走から作る |
"""

from .prior_slope_year_store import PriorSlopeYearStore

__all__ = ["PriorSlopeYearStore"]
