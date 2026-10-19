"""上のクラス・ハンデ戦の馬の予想モデルを分ける案を確かめる（docs/01 の手順4・7）。

    uv run python research/レースの種類ごとの買い方/horse_model.py kinds                 # 2012年からのレースの種類を元DB から読む（数分）
    uv run python research/レースの種類ごとの買い方/horse_model.py run --variant 今       # 今の材料のまま、23の区切りで学び直す（1〜2時間）
    uv run python research/レースの種類ごとの買い方/horse_model.py run --variant 分ける
    uv run python research/レースの種類ごとの買い方/horse_model.py run --variant 材料を足す
    uv run python research/レースの種類ごとの買い方/horse_model.py compare               # 上のクラス・ハンデ戦のテスト期間の誤差を比べ、採否を出す

学ぶのは当日の3着以内の今の本番（研究「複勝以外の回収率100超」の ``当日・3着以内``）。学習データの表は同じ研究の ``tables-2012``、
学び方は研究「既存モデルの改善」の ``WalkForwardRunner``（LightGBM と CatBoost の平均・今の本番の設定）。
出るものは全部 Git 対象外の ``reports/レースの種類ごとの買い方/horse/``。
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import db  # noqa: E402

from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.variants import ModelVariant  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.win_check import _pin_to_p_cores as pin_to_p_cores  # noqa: E402
from 既存モデルの改善.win_check import _with_threads as with_threads  # noqa: E402
from 複勝以外の回収率100超.analysis.retrain_targets import retrain_target_named  # noqa: E402
from レースの種類ごとの買い方.analysis.horse_model_comparison import HorseModelComparison  # noqa: E402
from レースの種類ごとの買い方.analysis.horse_windows import HORSE_WINDOWS  # noqa: E402
from レースの種類ごとの買い方.analysis.kind_columns import SEGMENT_COLUMN, TARGET_SEGMENT, KindColumns  # noqa: E402
from レースの種類ごとの買い方.analysis.race_kinds import RaceKinds  # noqa: E402
from レースの種類ごとの買い方.analysis.weight_type_variant import WeightTypeVariant  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
OUT = _REPORTS / "レースの種類ごとの買い方" / "horse"
TABLES_2012 = _REPORTS / "複勝以外の回収率100超" / "tables-2012"
KINDS_2012 = OUT / "kinds-2012.parquet"
#: 学び直す今の本番（当日の3着以内）。
TARGET = "当日・3着以内"
#: 案の名前 → 保存するファイルの名前。
VARIANT_KEYS: dict[str, str] = {"今": "base", "分ける": "split", "材料を足す": "weight_type"}


def main() -> None:
    args = _parser().parse_args()
    {"kinds": _kinds, "run": _run, "compare": _compare}[args.step](args)


def _kinds(args: argparse.Namespace) -> None:
    with db.open_db(args.db) as con:
        kinds = RaceKinds().read(con, "2012-01-01")
    OUT.mkdir(parents=True, exist_ok=True)
    kinds.to_parquet(KINDS_2012)
    print(f"{len(kinds):,}レース → {KINDS_2012}", flush=True)


def _variant(name: str) -> ModelVariant:
    base = retrain_target_named(TARGET).variant
    key = VARIANT_KEYS[name]
    if name == "分ける":
        return replace(base, key=key, name=f"{base.name}・上のクラスとハンデ戦を分ける", segment_column=SEGMENT_COLUMN)
    if name == "材料を足す":
        return WeightTypeVariant(base.model, key, f"{base.name}・重量種別を足す", base.columns, base.uses_baseline,
                                 base.segment_column, base.timing)
    return replace(base, key=key, name=f"{base.name}・学び直し")


def _data():
    target = retrain_target_named(TARGET)
    data = TableStore(TABLES_2012).read(target.variant.model, target.catalog)
    return KindColumns(pd.read_parquet(KINDS_2012)).add(data)


def _run(args: argparse.Namespace) -> None:
    pin_to_p_cores()
    target = retrain_target_named(TARGET)
    variant = _variant(args.variant)
    path = OUT / f"{variant.key}.pkl"
    if path.exists() and not args.force:
        print(f"済み: {path}", flush=True)
        return
    settings = with_threads(HyperparameterSettings.load(None, defaults=target.settings), args.threads)
    frame, log = WalkForwardRunner(WindowTrainer(settings), HORSE_WINDOWS).run(_data(), variant)
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_pickle(path)
    log.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    print(f"{args.variant}: {len(frame):,}行 → {path}", flush=True)


def _compare(args: argparse.Namespace) -> None:
    data = _data()
    labels = data.ids[["レースID", "馬番"]].assign(y=data.label.to_numpy(),
                                                  target=(data.evaluation[SEGMENT_COLUMN] == TARGET_SEGMENT).to_numpy())
    comparison = HorseModelComparison(labels, "y", "target")
    predictions = {name: pd.read_pickle(OUT / f"{key}.pkl") for name, key in VARIANT_KEYS.items()}
    table = comparison.table(predictions, "今")
    lines = ["# 上のクラス・ハンデ戦のレースのテスト期間の対数損失（当日の3着以内。小さいほど良い）\n", table.round(5).to_markdown(), ""]
    for name in ("分ける", "材料を足す"):
        wins, total, adopted = comparison.verdict(table, name, "今")
        lines.append(f"- {name}: 今より誤差が小さい区切り {wins} / {total}・全体 "
                     f"{(table[name] * table['行']).sum() / table['行'].sum():.5f}（今 {(table['今'] * table['行']).sum() / table['行'].sum():.5f}）"
                     f" → {'採用の基準を満たす' if adopted else '満たさない'}")
    text = "\n".join(lines) + "\n"
    (OUT / "比べた結果.md").write_text(text, encoding="utf-8")
    print(text, flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="上のクラス・ハンデ戦の馬の予想モデルを分ける案を確かめる（docs/01 の 7）", allow_abbrev=False)
    parser.add_argument("step", choices=("kinds", "run", "compare"))
    parser.add_argument("--variant", choices=tuple(VARIANT_KEYS), default="今", help="run で学ぶ案")
    parser.add_argument("--threads", type=int, default=4, help="学習のスレッド数（既定: 4。ほかの計算と並べて回すため）")
    parser.add_argument("--force", action="store_true", help="済んだものも学び直す")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
