"""7つの区切りの予測の出どころ（どの研究の、どのファイルか）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: 予測の表の名前の後ろ（研究「既存モデルの改善」の ``PredictionStore`` と同じ）。
_PREDICTIONS_SUFFIX = ".pkl"


@dataclass(frozen=True)
class PredictionSource:
    """1つの予想の、区切りごとの予測の表の置き場（``<root>/<model>/<key>.pkl``。``PredictionStore`` の形）。"""

    root: Path
    model: str
    key: str

    @property
    def path(self) -> Path:
        return Path(self.root) / self.model / f"{self.key}{_PREDICTIONS_SUFFIX}"


@dataclass(frozen=True)
class MaterialSources:
    """材料表を作るのに読む5つの場所。

    - ``form``: 近走と適性（当日。券種の支持と馬の力の材料入り）の予測。
    - ``form_tables``: その学習データの表のフォルダ（``ids.pkl``・``evaluation.pkl``・``targets.pkl``）。答え・人気・複勝オッズ・払戻はここから取る。
    - ``longshots``・``favorites``・``upset``: 穴馬・人気馬・荒れ具合の予測。
    """

    form: PredictionSource
    form_tables: Path
    longshots: PredictionSource
    favorites: PredictionSource
    upset: PredictionSource

    def describe(self) -> dict[str, str]:
        """記録（materials-meta.json）に残す形。"""
        return {
            "form": str(self.form.path), "form_tables": str(self.form_tables), "longshots": str(self.longshots.path),
            "favorites": str(self.favorites.path), "upset": str(self.upset.path),
        }


def default_sources(reports_root: Path) -> MaterialSources:
    """既定の出どころ（``reports/`` の下。どのコミットで作ったかは ``round3/materials/README.md``）。"""
    reports_root = Path(reports_root)
    port = reports_root / "一番人気を疑う" / "移したあとの確かめ"
    return MaterialSources(
        form=PredictionSource(port / "predictions", "form_pool_ability", "pool-ability-race_day"),
        form_tables=port / "tables" / "form_pool_ability",
        longshots=PredictionSource(reports_root / "穴馬が3着以内に入るかを予想" / "複勝オッズの比べ" / "predictions",
                                   "longshots_in_top3", "place_odds-race_day"),
        favorites=PredictionSource(reports_root / "既存モデルの改善" / "predictions", "favorites_out_of_top3", "people_market"),
        upset=PredictionSource(reports_root / "既存モデルの改善" / "predictions", "upset_level", "current"),
    )
