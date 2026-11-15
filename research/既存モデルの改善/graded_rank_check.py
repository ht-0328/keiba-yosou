"""順位で学ぶ予想（3案目）を、1年ずつの7つの区切りで確かめる（研究「既存モデルの改善」の入口⑰）。

    uv run python research/既存モデルの改善/graded_rank_check.py run       # 7つの区切りで学び、テストの年の確率を残す（1つの区切り 5〜10分）
    uv run python research/既存モデルの改善/graded_rank_check.py summary   # テストの年の重賞の行のログ損失を、当日の手本と比べる

学習の行は中央の平地の全レース（今の本番の当日の表 ``tables/dscore_race_day``。列も今の本番の当日の3着以内と同じ）。
同じレースの馬を1つの組にして、着順の並びを LightGBM の lambdarank で学ぶ（出発点はオッズから見た勝率の対数）。
点数は、1着の確率（レースで合計 1）と3着以内の確率（Harville の式）にし、効き具合（温度）は検証の年で合わせる。
出るもの（Git 対象外）: ``predictions/graded_race_day/rank-top3.pkl``・``rank-win.pkl``・``compare/順位で学ぶ予想-<日付>.md``。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.dataset import HORSE_ID, RACE_ID, TOP3, WIN  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402
from yosou.shared.feature.form_aptitude_catalog import RACE_DAY_CATALOG  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 既存モデルの改善.analysis.development_score.score_tables import score_table_named  # noqa: E402
from 既存モデルの改善.analysis.graded_race import IS_GRADED, PREDICTION_TABLE, TOP3_TABLE  # noqa: E402
from 既存モデルの改善.analysis.graded_rank import RankWindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore  # noqa: E402
from 既存モデルの改善.analysis.windows import STAKES_WINDOWS  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports" / "既存モデルの改善"
_TABLES, _PREDICTIONS = _REPORTS / "tables", _REPORTS / "predictions"
_COLUMNS = RACE_DAY_CATALOG.columns_for(PredictionTiming.RACE_DAY)
#: 比べる予測（入口⑮ の当日の手本と、入口⑯ の二段の予想・前日の1段目）。
_COMPARE = {"top3": ("rank-top3", "general-top3", "dayb-top3"), "win": ("rank-win", "general-win", "dayb-win")}
_P_CORES, _BELOW_NORMAL = 0xFFF, 0x4000
_EPS = 1e-15


def main() -> None:
    args = _parser().parse_args()
    {"run": _run, "summary": _summary}[args.step](args)


def _run(args: argparse.Namespace) -> None:
    _pin_to_p_cores()
    values = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH).to_dict()
    values["lightgbm"]["params"]["n_jobs"] = args.threads
    settings = HyperparameterSettings.from_dict(values).lightgbm
    data = TableStore(_TABLES).read(TOP3_TABLE, score_table_named(TOP3_TABLE).catalog)
    trainer = RankWindowTrainer(settings, _COLUMNS)
    tops, wins, logs = [], [], []
    for window in STAKES_WINDOWS:
        print(f"順位で学ぶ予想 / {window.name}: 学習しています …", file=sys.stderr, flush=True)
        top3, win, log = trainer.run(data, window)
        tops.append(top3), wins.append(win), logs.append(log)
        print(f"順位で学ぶ予想 / {window.name}: {log}", file=sys.stderr, flush=True)
    store = PredictionStore(_PREDICTIONS)
    log_frame = pd.DataFrame(logs)
    print(store.write(PREDICTION_TABLE, "rank-top3", pd.concat(tops, ignore_index=True), log_frame))
    print(store.write(PREDICTION_TABLE, "rank-win", pd.concat(wins, ignore_index=True), log_frame))


def _summary(args: argparse.Namespace) -> None:
    store, tables = PredictionStore(_PREDICTIONS), TableStore(_TABLES)
    base = tables.read(TOP3_TABLE, score_table_named(TOP3_TABLE).catalog)
    extra = pd.read_pickle(_TABLES / "graded_extra" / f"{TOP3_TABLE}.pkl")
    keyed = pd.DataFrame({"race_id": base.ids[RACE_ID].astype(str).to_numpy(), "horse_id": base.ids[HORSE_ID].astype(str).to_numpy(),
                          "top3": base.targets[TOP3].to_numpy(), "win": base.targets[WIN].to_numpy(), "graded": extra[IS_GRADED].to_numpy()})
    graded = keyed[keyed["graded"].eq(1.0)]
    lines = [f"# 順位で学ぶ予想: テストの年の重賞の行のログ損失（{date.today().isoformat()}）", "", "小さいほど良い。3つの予測のどれもある行だけで比べる。", ""]
    for target, keys in _COMPARE.items():
        rows = graded[["race_id", "horse_id", target]]
        for key in keys:
            rows = rows.merge(_probability(store, key).rename(columns={"p": key}), on=["race_id", "horse_id"], how="inner")
        rows = rows.assign(year=rows["race_id"].str[:4])
        lines += [f"## {'3着以内' if target == 'top3' else '1着'}", "", "| 年 | 行数 | " + " | ".join(keys) + " | 順位が手本より小さい |",
                  "|---|---|" + "---|" * len(keys) + "---|"]
        for year, group in [*rows.groupby("year"), ("全体", rows)]:
            losses = [_logloss(group[target], group[key]) for key in keys]
            lines.append(f"| {year} | {len(group):,} | " + " | ".join(f"{loss:.5f}" for loss in losses) + f" | {'○' if losses[0] < losses[1] else '×'} |")
        lines.append("")
    out = _REPORTS / "compare" / f"順位で学ぶ予想-{date.today().isoformat()}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def _probability(store: PredictionStore, key: str) -> pd.DataFrame:
    frame = store.read(PREDICTION_TABLE, key)
    frame = frame[frame["期間"] == "テスト"]
    return pd.DataFrame({"race_id": frame[RACE_ID].astype(str), "horse_id": frame[HORSE_ID].astype(str), "p": frame["確率"]}).drop_duplicates(
        ["race_id", "horse_id"], keep="last")


def _logloss(y: pd.Series, p: pd.Series) -> float:
    actual, prob = y.to_numpy(dtype=float), np.clip(p.to_numpy(dtype=float), _EPS, 1 - _EPS)
    return float(-np.mean(actual * np.log(prob) + (1 - actual) * np.log(1 - prob)))


def _pin_to_p_cores() -> None:
    """Windows では、このプロセスを P コアだけで、ふつうより低い優先度で動かす。"""
    if sys.platform != "win32":
        return
    import ctypes

    kernel = ctypes.windll.kernel32
    kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), _P_CORES)
    kernel.SetPriorityClass(kernel.GetCurrentProcess(), _BELOW_NORMAL)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="順位で学ぶ予想の確かめ", allow_abbrev=False)
    parser.add_argument("step", choices=("run", "summary"))
    parser.add_argument("--threads", type=int, default=10, help="学習のスレッド数（既定: 10）")
    return parser


if __name__ == "__main__":
    main()
