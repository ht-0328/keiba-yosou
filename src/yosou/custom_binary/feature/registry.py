"""特徴量の登録・依存検査。選んだ列と、計算のために必要な列を区別する。"""

from collections.abc import Iterable
from pathlib import Path

from yosou.shared.feature import Feature, FeatureCatalog, PredictionTiming

from .definition import FeatureDefinition


class FeatureRegistry:
    def __init__(self, definitions: Iterable[FeatureDefinition]) -> None:
        self.definitions: dict[str, FeatureDefinition] = {}
        for definition in definitions:
            if definition.name in self.definitions:
                raise ValueError(f"特徴量の登録名が重複しています: {definition.name}")
            self.definitions[definition.name] = definition
        # 利用者がまだ選んでいない項目も、登録時に依存先と循環を検査する。
        self.order(tuple(self.definitions))

    def order(self, selected: tuple[str, ...], timing: PredictionTiming | None = None) -> tuple[str, ...]:
        ordered: list[str] = []
        complete: set[str] = set()
        visiting: list[str] = []

        def visit(name: str) -> None:
            if name in complete:
                return
            if name not in self.definitions:
                raise ValueError(f"未登録の特徴量です: {' → '.join([*visiting, name])}")
            if name in visiting:
                raise ValueError(f"特徴量の循環参照です: {' → '.join([*visiting, name])}")
            definition = self.definitions[name]
            if timing is not None and not timing.is_at_or_after(definition.known_from):
                raise ValueError(f"{timing.label}には使えない特徴量です: {name}（{definition.known_from.label}から）")
            visiting.append(name)
            for dependency in definition.dependencies:
                visit(dependency)
            visiting.pop()
            complete.add(name)
            ordered.append(name)

        for name in selected:
            visit(name)
        return tuple(ordered)

    def read_selection(self, path: Path, timing: PredictionTiming) -> tuple[str, ...]:
        selected: list[str] = []
        first_lines: dict[str, int] = {}
        for line, text in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            name = text.strip()
            if not name or name.startswith("#"):
                continue
            if name in first_lines:
                raise ValueError(f"{path}:{line}: 特徴量が重複しています: {name}（初出 {first_lines[name]}行）")
            try:
                self.order((name,), timing)
            except ValueError as error:
                raise ValueError(f"{path}:{line}: {error}") from error
            first_lines[name] = line
            selected.append(name)
        if not selected:
            raise ValueError(f"{path}:1: 有効な特徴量がありません")
        return tuple(selected)

    def catalog(self, selected: tuple[str, ...]) -> FeatureCatalog:
        return FeatureCatalog(tuple(
            Feature(name, "custom", self.definitions[name].kind, self.definitions[name].known_from)
            for name in selected
        ))

    def schema(self, selected: tuple[str, ...]) -> list[dict]:
        """依存項目も保存し、コード更新による型・依存関係の不一致を検出する。"""
        return [{
            "name": name, "kind": self.definitions[name].kind.value,
            "known_from": self.definitions[name].known_from.value,
            "dependencies": list(self.definitions[name].dependencies),
        } for name in self.order(selected)]
