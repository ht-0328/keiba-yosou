"""元の設定ファイルに依存しないモデルの保存。未完了の保存物は読み込まない。"""

from datetime import datetime, timezone
import json
from pathlib import Path

from yosou.shared.ml_model import MEMBER_TYPES, EnsembleModel
from yosou.shared.place_value import PlacePriceEstimator
from yosou.shared.repository import ModelRepository

from ..feature.registry import FeatureRegistry
from ..setting import ModelSettings
from .code_version import CodeVersion


FORMAT_VERSION = 1
MANIFEST = "model.json"
#: 複勝の想定払戻倍率の帯ごとの倍率（学習期間の払戻から求めた値）。予想の期待値に使う。
PLACE_PRICE = "place_price.json"
#: 検証期間の成績（学習のとき）と、テスト期間の成績（evaluate のとき）。
VALIDATION = "validation.json"
TEST_EVALUATION = "test_evaluation.json"


class ModelStore:
    """学習した2つのモデルと、設定・特徴量の形・コードの版・保存形式の版を、1つのフォルダに読み書きする。

    保存物にはクラスの置き場所を埋め込まない（設定は JSON、モデルは共通の ``ModelRepository`` が書く）。
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.repository = ModelRepository(root, MEMBER_TYPES)

    def check_new(self) -> None:
        if self.root.exists():
            raise ValueError(f"保存先は既に存在します。別のnameを指定してください: {self.root}")

    def save(self, settings: ModelSettings, registry: FeatureRegistry, models, validation: list[dict], counts: dict,
             place_price: PlacePriceEstimator | None = None) -> None:
        self.check_new()
        # 排他的な作成で、別プロセスによる同名保存も拒否する。
        try:
            self.root.mkdir(parents=True, exist_ok=False)
        except FileExistsError as error:
            raise ValueError(f"保存先は既に存在します: {self.root}") from error
        self.repository.save(settings.timing, models, settings.parameters)
        self._write_json(self.root / VALIDATION, validation)
        if place_price is not None:
            self._write_json(self.root / PLACE_PRICE, place_price.state())
        # manifestは最後。途中で失敗したフォルダは完成モデルとして扱わない。
        self._write_json(self.root / MANIFEST, {
            "format_version": FORMAT_VERSION, "settings": settings.as_dict(),
            "feature_schema": registry.schema(settings.selected), "code_version": CodeVersion().current(),
            "created_at": datetime.now(timezone.utc).isoformat(), "sample_counts": counts,
        })

    def save_test_evaluation(self, result: dict) -> None:
        """テスト期間の成績を、モデルのフォルダに書く（前に書いたものは置き換える）。"""
        self._write_json(self.root / TEST_EVALUATION, result)

    def place_price(self) -> PlacePriceEstimator | None:
        """学習のときに保存した複勝の想定払戻倍率。保存していない古いモデルは None（最低オッズのまま使う）。"""
        path = self.root / PLACE_PRICE
        if not path.is_file():
            return None
        return PlacePriceEstimator.from_state(json.loads(path.read_text(encoding="utf-8")))

    def load(self, registry: FeatureRegistry) -> tuple[ModelSettings, EnsembleModel]:
        if not (self.root / MANIFEST).is_file():
            raise ValueError(f"完成した学習済みモデルがありません: {self.root}")
        saved = json.loads((self.root / MANIFEST).read_text(encoding="utf-8"))
        if saved.get("format_version") != FORMAT_VERSION:
            raise ValueError("モデルの保存形式バージョンが未対応です")
        settings = ModelSettings.from_saved(saved["settings"], registry)
        if registry.schema(settings.selected) != saved["feature_schema"]:
            raise ValueError("保存した特徴量の型・時点・依存関係が現在の実装と違います。再学習してください")
        return settings, EnsembleModel(self.repository.load(settings.timing))

    def _write_json(self, path: Path, value) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
