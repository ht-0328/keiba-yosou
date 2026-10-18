"""入口③（前の年の区切りと、学び直すモデル）のテスト。DB と学習データは使わない。"""

from __future__ import annotations

from pathlib import Path

from yosou.shared.feature import PredictionTiming

from 既存モデルの改善.analysis.material_check.current_production import current_production
from 既存モデルの改善.analysis.windows import WINDOWS
from 複勝以外の回収率100超.analysis.early_windows import EARLIEST_WINDOWS, EARLY_WINDOWS, WINDOW_SETS
from 複勝以外の回収率100超.analysis.retrain_targets import RETRAIN_TARGETS, retrain_target_named


def test_前の年の区切りは今の7つの区切りより前で名前も重ならない() -> None:
    assert [window.name for window in EARLY_WINDOWS] == ["2021年前半", "2021年後半", "2022年前半", "2022年後半"]
    assert all(window.test_last_day < WINDOWS[0].test_first_day for window in EARLY_WINDOWS)
    assert not {window.name for window in EARLY_WINDOWS} & {window.name for window in WINDOWS}
    # テストの期間はすき間なく続く
    for before, after in zip(EARLY_WINDOWS, EARLY_WINDOWS[1:], strict=False):
        assert (after.test_first_day - before.test_last_day).days == 1


def test_学び直すのは前日と当日の3着以内と1着と危険な人気馬の5つ() -> None:
    labels = [target.label for target in RETRAIN_TARGETS]
    assert sorted(labels) == sorted(["前日・3着以内", "当日・3着以内", "前日・1着", "当日・1着", "危険な人気馬"])
    keys = {(target.variant.model, target.variant.key) for target in RETRAIN_TARGETS}
    assert len(keys) == len(RETRAIN_TARGETS)  # 予測のファイルが重ならない


def test_今の本番の列と表のまま学び直し本番の予測と合わせる() -> None:
    target = retrain_target_named("当日・1着")
    current = current_production(PredictionTiming.RACE_DAY, "1着")
    assert target.win and target.variant.columns == current.columns and target.variant.model == current.base_table
    assert target.variant.uses_baseline and target.variant.timing is PredictionTiming.RACE_DAY
    assert target.production_path(Path("reports")) == Path("reports") / current.research / "predictions" / current.table / f"{current.key}.pkl"
    favorites = retrain_target_named("危険な人気馬")
    assert not favorites.win and favorites.production == "既存モデルの改善/favorites_out_of_top3/people_market"


def test_手順5の区切りは2019年と2020年で手順4の区切りの前にすき間なく続く() -> None:
    assert [window.name for window in EARLIEST_WINDOWS] == ["2019年前半", "2019年後半", "2020年前半", "2020年後半"]
    assert (EARLY_WINDOWS[0].test_first_day - EARLIEST_WINDOWS[-1].test_last_day).days == 1
    assert WINDOW_SETS["2019"] == (EARLIEST_WINDOWS, "predictions-2019") and WINDOW_SETS["2021"] == (EARLY_WINDOWS, "predictions")


def test_手順6の区切りは2015年前半から2018年後半の8つで手順5の区切りの前にすき間なく続く() -> None:
    from 複勝以外の回収率100超.analysis.early_windows import OLDEST_WINDOWS

    assert [window.name for window in OLDEST_WINDOWS][:2] == ["2015年前半", "2015年後半"] and len(OLDEST_WINDOWS) == 8
    assert (EARLIEST_WINDOWS[0].test_first_day - OLDEST_WINDOWS[-1].test_last_day).days == 1
    for before, after in zip(OLDEST_WINDOWS, OLDEST_WINDOWS[1:], strict=False):
        assert (after.test_first_day - before.test_last_day).days == 1
    assert WINDOW_SETS["2015"] == (OLDEST_WINDOWS, "predictions-2015")
