"""YAML の training: 学習・検証・テストの期間の区切りを読む。"""

from datetime import date

from yosou.shared.dataset import TrainingPeriod

from .yaml_mapping import YamlMapping

#: training に書ける項目。
ALLOWED = {"warmup_from", "train_from", "valid_from", "test_from"}


class TrainingPeriodReader:
    """書いていない区切りは、共通の既定（``TrainingPeriod.default()``）にする。ウォームアップの始まりだけは省略できる。"""

    def read(self, values: dict) -> TrainingPeriod:
        defaults = TrainingPeriod.default()
        YamlMapping().check(values, ALLOWED, "training")
        return TrainingPeriod.starting(
            self._day(values, "train_from", defaults.train_first_day),
            self._day(values, "valid_from", defaults.valid_first_day),
            self._day(values, "test_from", defaults.test_first_day),
            self._day(values, "warmup_from", None),
        )

    def _day(self, values: dict, name: str, fallback: date | None) -> date | None:
        value = values.get(name, fallback)
        if value is None and name not in values:
            return None
        if type(value) is date:
            return value
        if isinstance(value, str):
            return self._iso_day(value, name)
        raise self._invalid(name)

    def _iso_day(self, value: str, name: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise self._invalid(name) from None

    def _invalid(self, name: str) -> ValueError:
        return ValueError(f"training.{name}はYYYY-MM-DDで指定してください")
