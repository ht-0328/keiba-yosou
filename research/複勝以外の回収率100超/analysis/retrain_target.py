"""前の年の区切りで学習し直すモデル1つ。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yosou.shared.feature import FeatureCatalog

from 既存モデルの改善.analysis.variants import ModelVariant


@dataclass(frozen=True)
class RetrainTarget:
    """前の年の区切り（``EARLY_WINDOWS``）で学習し直すモデル1つ。

    - ``label``: 表に出す名前（例 前日・3着以内）。
    - ``variant``: 学び方（表の名前・列・基準を使うか・分ける列）。予測は ``<予測の置き場所>/<variant.model>/<variant.key>.pkl`` に書く。
    - ``catalog``: 表（研究「既存モデルの改善」の ``tables/<variant.model>``）の特徴量の一覧。
    - ``win``: 目的変数を1着に持ち替えるか（1着のモデル）。
    - ``settings``: ハイパーパラメータの初期値のファイル。
    - ``production``: 今の本番の、7つの区切りの予測（``reports/<研究>/predictions/<予想>/<作り方>``）。前の年の予測と合わせる相手。
    """

    label: str
    variant: ModelVariant
    catalog: FeatureCatalog
    win: bool
    settings: Path
    production: str

    @property
    def production_key(self) -> tuple[str, str, str]:
        """（研究, 予想, 作り方）。"""
        research, table, key = self.production.split("/")
        return research, table, key

    def production_path(self, reports: Path) -> Path:
        """今の本番の、7つの区切りの予測のファイル。"""
        research, table, key = self.production_key
        return Path(reports) / research / "predictions" / table / f"{key}.pkl"
