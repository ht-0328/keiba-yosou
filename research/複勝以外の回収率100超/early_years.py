"""手順4: 印のルールの買い目を、まだ見ていない年（2021〜2022年）で確かめるための予測を作る（研究「複勝以外の回収率100超」の入口③）。

    uv run python research/複勝以外の回収率100超/early_years.py run                    # 5つのモデルを前の年の4つの区切りで学習する（1時間ほど。済んだものは飛ばす）
    uv run python research/複勝以外の回収率100超/early_years.py run --only 当日・1着    # 1つだけ
    uv run python research/複勝以外の回収率100超/early_years.py combine                # 今の本番の7つの区切りの予測と合わせる
    uv run python research/複勝以外の回収率100超/early_years.py run --from-year 2019     # 手順5: 2019年前半〜2020年後半の4つの区切りで学習する
    uv run python research/複勝以外の回収率100超/early_years.py combine --from-year 2019 # 手順5: 2021年〜の11の区切りの予測と合わせる（2019年〜の15の区切り）

学ぶのは、道具「印の成績」で印を付けるのに要る5つ（前日・当日の 3着以内と1着の今の本番と、危険な人気馬の今の本番）。
列と表は研究「既存モデルの改善」の入口⑭が「今の予想」として持つもの（``analysis/material_check/current_production.py``）と同じで、
区切りだけを ``analysis/early_windows.py`` の4つ（2021年前半〜2022年後半）にする。
``combine`` は、その予測と今の本番の7つの区切りの予測を合わせて、2021年〜2026年の11の区切りの予測を作る。
道具「印の成績」に ``--form``・``--win``・``--danger`` でそのファイルを渡すと、前の年も含めた買い目の成績が出る（手順は docs/03）。
出るもの（Git 対象外）: ``reports/複勝以外の回収率100超/predictions/``（前の年だけ）と ``predictions-2021から/``（合わせたもの）。
``--from-year 2019`` は手順5（docs/04）の区切り（2019年前半〜2020年後半）で、``predictions-2019/`` と ``predictions-2019から/``
（2019年の4つ ＋ 2021年からの11 ＝ 15の区切り）に書く。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コアに絞る（入口⑭と同じ）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yosou.form_aptitude_top3.dataset import WinTargetData  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.win_check import _pin_to_p_cores as pin_to_p_cores  # noqa: E402  学習の下ごしらえは入口⑪と同じ
from 既存モデルの改善.win_check import _with_threads as with_threads  # noqa: E402
from 複勝以外の回収率100超.analysis.early_windows import WINDOW_SETS  # noqa: E402
from 複勝以外の回収率100超.analysis.retrain_target import RetrainTarget  # noqa: E402
from 複勝以外の回収率100超.analysis.retrain_targets import RETRAIN_TARGETS, retrain_target_named  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
DEFAULT_ROOT = _REPORTS / "複勝以外の回収率100超"
#: 学習データの表の置き場所（研究「既存モデルの改善」の build_tables.py・development_score_check.py が作ったもの）。
DEFAULT_TABLES = _REPORTS / "既存モデルの改善" / "tables"
#: 合わせた予測の置き場所（``<root>/`` の下のフォルダ名。区切りの組の最初の年 → フォルダ名）。
COMBINED: dict[str, str] = {"2021": "predictions-2021から", "2019": "predictions-2019から"}
#: 区切りの組 → 合わせる相手（その組より新しい区切りの予測。2021年の組は今の本番の7つの区切り、2019年の組は 2021年からの11の区切り）。
PARTNER: dict[str, str | None] = {"2021": None, "2019": COMBINED["2021"]}


def main() -> None:
    args = _parser().parse_args()
    targets = [retrain_target_named(label) for label in args.only] if args.only else list(RETRAIN_TARGETS)
    {"run": _run, "combine": _combine}[args.step](args, targets)


def _run(args: argparse.Namespace, targets: list[RetrainTarget]) -> None:
    pin_to_p_cores()
    windows, folder = WINDOW_SETS[args.from_year]
    store, tables = PredictionStore(args.root / folder), TableStore(args.tables)
    for target in targets:
        variant = target.variant
        if store.exists(variant.model, variant.key) and not args.force:
            print(f"{target.label}: 済んでいるので飛ばします", flush=True)
            continue
        print(f"{target.label}: 表 {variant.model} を読んでいます …", flush=True)
        data = tables.read(variant.model, target.catalog)
        if target.win:
            data = WinTargetData().training(data)
        settings = with_threads(HyperparameterSettings.load(None, defaults=target.settings), args.threads)
        frame, log = WalkForwardRunner(WindowTrainer(settings), windows).run(data, variant)
        print(f"{target.label}: {store.write(variant.model, variant.key, frame, log)}", flush=True)


def _combine(args: argparse.Namespace, targets: list[RetrainTarget]) -> None:
    early_store = PredictionStore(args.root / WINDOW_SETS[args.from_year][1])
    combined_store = PredictionStore(args.root / COMBINED[args.from_year])
    partner = PARTNER[args.from_year]
    for target in targets:
        variant = target.variant
        early = early_store.read(variant.model, variant.key)
        production = (pd.read_pickle(target.production_path(args.reports)) if partner is None
                      else PredictionStore(args.root / partner).read(variant.model, variant.key))
        overlap = set(early["区切り"]) & set(production["区切り"])
        if overlap:
            raise ValueError(f"{target.label}: 区切りの名前が重なっています: {'・'.join(sorted(overlap))}")
        columns = [column for column in production.columns if column in early.columns]
        combined = pd.concat([early[columns], production[columns]], ignore_index=True)
        source = str(target.production_path(args.reports)) if partner is None else str(args.root / partner)
        log = pd.DataFrame({"元": ["前の年", "新しい区切り"], "ファイル": [str(early_store), source]})
        path = combined_store.write(variant.model, variant.key, combined, log)
        print(f"{target.label}: 前の年 {len(early):,}行 ＋ 今の本番 {len(production):,}行 → {path}", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="印のルールの買い目を前の年で確かめるための予測を作る", allow_abbrev=False)
    parser.add_argument("step", choices=("run", "combine"), help="run（前の年の区切りで学習する）・combine（今の本番の予測と合わせる）")
    parser.add_argument("--only", nargs="*", default=None, metavar="モデル",
                        help=f"回すモデル（{' / '.join(target.label for target in RETRAIN_TARGETS)}。省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだモデルも回し直す")
    parser.add_argument("--from-year", choices=tuple(WINDOW_SETS), default="2021",
                        help="区切りの組（2021: 手順4 の 2021〜2022年。2019: 手順5 の 2019〜2020年。既定: 2021）")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="予測の置き場所（predictions/・predictions-2021から/ など）")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--reports", type=Path, default=_REPORTS, help="今の本番の予測を探す reports の場所")
    return parser


if __name__ == "__main__":
    main()
