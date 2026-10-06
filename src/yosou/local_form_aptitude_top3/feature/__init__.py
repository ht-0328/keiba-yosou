"""この予想の特徴量の一覧（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまりのクラス）は ``yosou.shared.feature``。ここには、この予想が使う一覧を置く。

| 名前 | 中身 |
|---|---|
| ``LOCAL_BASE_FEATURES`` | 土台の 65個。共通の ``BASE_FEATURES``（71個）から調教（I）の6個を除き、枠番・馬番を出馬表から分かるものにした |
| ``CATALOG`` | この予想の特徴量の一覧（96個 = 土台 65 + J 4 + L 4 + O 7 + N 6 + Q 10）。学習データと予測用データはこの一覧で作り、3着以内のモデルに渡す前に Q を、券種のオッズが無いときに N を外す |
"""

from .feature_catalog import CATALOG, LOCAL_BASE_FEATURES

__all__ = ["CATALOG", "LOCAL_BASE_FEATURES"]
