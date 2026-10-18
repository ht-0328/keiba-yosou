"""手順4: 印のルールの買い目を、まだ見ていない年（2021〜2022年）で確かめるための予測を作る（研究「複勝以外の回収率100超」の入口③）。

    uv run python research/複勝以外の回収率100超/early_years.py run                    # 5つのモデルを前の年の4つの区切りで学習する（1時間ほど。済んだものは飛ばす）
    uv run python research/複勝以外の回収率100超/early_years.py run --only 当日・1着    # 1つだけ
    uv run python research/複勝以外の回収率100超/early_years.py combine                # 今の本番の7つの区切りの予測と合わせる
    uv run python research/複勝以外の回収率100超/early_years.py run --from-year 2019     # 手順5: 2019年前半〜2020年後半の4つの区切りで学習する
    uv run python research/複勝以外の回収率100超/early_years.py combine --from-year 2019 # 手順5: 2021年〜の11の区切りの予測と合わせる（2019年〜の15の区切り）
    uv run python research/複勝以外の回収率100超/early_years.py tables                   # 手順6: 2012年からの学習データの表を用意する（十数分）
    uv run python research/複勝以外の回収率100超/early_years.py run --from-year 2015 --tables reports/複勝以外の回収率100超/tables-2012 --only 当日・3着以内 当日・1着 危険な人気馬
    uv run python research/複勝以外の回収率100超/early_years.py combine --from-year 2015 --only 当日・3着以内 当日・1着 危険な人気馬   # 2015年〜の23の区切り

学ぶのは、道具「印の成績」で印を付けるのに要る5つ（前日・当日の 3着以内と1着の今の本番と、危険な人気馬の今の本番）。
列と表は研究「既存モデルの改善」の入口⑭が「今の予想」として持つもの（``analysis/material_check/current_production.py``）と同じで、
区切りだけを ``analysis/early_windows.py`` の4つ（2021年前半〜2022年後半）にする。
``combine`` は、その予測と今の本番の7つの区切りの予測を合わせて、2021年〜2026年の11の区切りの予測を作る。
道具「印の成績」に ``--form``・``--win``・``--danger`` でそのファイルを渡すと、前の年も含めた買い目の成績が出る（手順は docs/03）。
出るもの（Git 対象外）: ``reports/複勝以外の回収率100超/predictions/``（前の年だけ）と ``predictions-2021から/``（合わせたもの）。
``--from-year 2019`` は手順5（docs/04）の区切り（2019年前半〜2020年後半）で、``predictions-2019/`` と ``predictions-2019から/``
（2019年の4つ ＋ 2021年からの11 ＝ 15の区切り）に書く。
``--from-year 2015`` は手順6（docs/05）の区切り（2015年前半〜2018年後半）で、``predictions-2015/`` と ``predictions-2015から/``（23の区切り）に書く。
当日の表は 2017年1月からなので、``tables`` で 2012年1月からの表を ``tables-2012/`` に用意して ``--tables`` で渡す。当日の3着以内と1着は、
研究「既存モデルの改善」の ``form_race_day``（``stakes_rebuild.py`` が作った 2012年からの当日の表。今の本番の当日の2つのモデルの列を全部持つ）を
その名前で置き（ハードリンク）、危険な人気馬の表は 2011年をウォームアップにして 2012年から作り直す。
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

from 共通 import db  # noqa: E402

from 既存モデルの改善.analysis.tables import TableStore, spec_named  # noqa: E402
from 既存モデルの改善.analysis.tables.model_tables import UPSET_TABLE_PERIOD  # noqa: E402
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
COMBINED: dict[str, str] = {"2021": "predictions-2021から", "2019": "predictions-2019から", "2015": "predictions-2015から"}
#: 区切りの組 → 合わせる相手（その組より新しい区切りの予測。2021年の組は今の本番の7つの区切り、2019年の組は 2021年からの11の区切り、
#: 2015年の組は 2019年からの15の区切り）。
PARTNER: dict[str, str | None] = {"2021": None, "2019": COMBINED["2021"], "2015": COMBINED["2019"]}
#: 手順6 の 2012年からの表の置き場所と、当日の2つのモデルの表に置く 2012年からの当日の表（研究「既存モデルの改善」の表の名前）。
TABLES_2012 = DEFAULT_ROOT / "tables-2012"
RACE_DAY_2012 = "form_race_day"
#: 2012年からの表に、2012年からの当日の表をそのまま置く表（今の本番の当日の3着以内と1着の表の名前）。前日の表はもとから 2012年から。
LINKED_TABLES: dict[str, str] = {"dscore_race_day": RACE_DAY_2012, "dscore_finish_race_day": RACE_DAY_2012,
                                 "dscore_day_before": "dscore_day_before"}
FAVORITES = "favorites_out_of_top3"


def main() -> None:
    args = _parser().parse_args()
    targets = [retrain_target_named(label) for label in args.only] if args.only else list(RETRAIN_TARGETS)
    {"run": _run, "combine": _combine, "tables": _tables}[args.step](args, targets)


def _tables(args: argparse.Namespace, targets: list[RetrainTarget]) -> None:
    """手順6 の 2012年からの表を ``TABLES_2012`` に用意する。当日の表はハードリンクで置き、危険な人気馬の表は作り直す。"""
    for name, source in LINKED_TABLES.items():
        _link_table(args.tables / source, TABLES_2012 / name)
        if source != name:
            _fill_columns(args.tables / name, TABLES_2012 / name)
        print(f"{name}: {args.tables / source} を置きました", flush=True)
    if TableStore(TABLES_2012).exists(FAVORITES) and not args.force:
        print(f"{FAVORITES}: 済んでいるので飛ばします", flush=True)
        return
    spec = spec_named(FAVORITES)
    print(f"{FAVORITES}: 2012年からの表を作っています …", flush=True)
    with db.open_db(args.db) as con:
        data = spec.builder_factory(con).build_training_data(UPSET_TABLE_PERIOD)
    print(f"{FAVORITES}: {len(data):,}行 → {TableStore(TABLES_2012).write(FAVORITES, data)}", flush=True)


def _fill_columns(original: Path, target: Path) -> None:
    """置いた表の特徴量に、元の表（同じ名前の 2017年からの表）にあって置いた表に無い列を、欠損値の列として足す。
    当日の表の特徴量の一覧には、当日のモデルが使わない列（対戦レーティング・展開の予想など。2012年からの当日の表には無い）も入っていて、
    学習の前に一覧の列を全部取り出すため。モデルが使う列はそろっているので、学ぶ中身は変わらない。"""
    columns = pd.read_pickle(original / "features.pkl").columns
    features = pd.read_pickle(target / "features.pkl")
    missing = [column for column in columns if column not in features.columns]
    (target / "features.pkl").unlink()
    features.assign(**{column: float("nan") for column in missing}).to_pickle(target / "features.pkl")
    print(f"{target.name}: 使わない列 {len(missing)} 個を欠損値で足しました", flush=True)


def _link_table(source: Path, target: Path) -> None:
    """表のフォルダのファイルを、ハードリンクで別の名前のフォルダに置く（大きいのでコピーしない）。前のものは置き換える。"""
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        placed = target / path.name
        placed.unlink(missing_ok=True)
        placed.hardlink_to(path)


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
    parser.add_argument("step", choices=("run", "combine", "tables"),
                        help="run（前の年の区切りで学習する）・combine（新しい区切りの予測と合わせる）・tables（手順6 の 2012年からの表を用意する）")
    parser.add_argument("--only", nargs="*", default=None, metavar="モデル",
                        help=f"回すモデル（{' / '.join(target.label for target in RETRAIN_TARGETS)}。省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだモデルも回し直す")
    parser.add_argument("--from-year", choices=tuple(WINDOW_SETS), default="2021",
                        help="区切りの組（2021: 手順4 の 2021〜2022年。2019: 手順5 の 2019〜2020年。2015: 手順6 の 2015〜2018年。既定: 2021）")
    parser.add_argument("--db", type=Path, default=None, help="tables で、危険な人気馬の表を作る元DB の場所")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="予測の置き場所（predictions/・predictions-2021から/ など）")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--reports", type=Path, default=_REPORTS, help="今の本番の予測を探す reports の場所")
    return parser


if __name__ == "__main__":
    main()
