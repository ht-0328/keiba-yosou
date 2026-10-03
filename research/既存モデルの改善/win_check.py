"""1着のモデル（全頭の予想の目的変数「1着」）を、今の本番と同じ材料で時点ごとに7つの区切りで学ぶ（研究「既存モデルの改善」の入口⑪）。

    uv run python research/既存モデルの改善/win_check.py run                          # 時点ごとに7つの区切りで学習する（1つ 30〜60分。済んだものは飛ばす）
    uv run python research/既存モデルの改善/win_check.py run --variants win-day_before  # 1つだけ
    uv run python research/既存モデルの改善/win_check.py summary                      # 1着のモデルの確率の誤差を、オッズから見た勝率と比べた表を書く

学習データの表は、対戦レーティングの確かめ（入口⑧）と展開の予想の確かめ（入口⑩）が作った今の本番と同じ材料の表
（前日 ``h2h_ability``・木曜 ``pace_thursday``・当日 ``h2h_pool_ability``）をそのまま読み、予想のパッケージの ``WinTargetData`` で
目的変数を「1着」に、基準を「オッズから見た勝率」に持ち替えて学ぶ。列は今の本番の3着以内のモデルと同じ。
出るもの（Git 対象外）: ``predictions/<表>/win-<時点>.pkl``・``compare/1着のモデル-<日付>.md``。
◎（単勝の期待値がいちばん高い馬）と期待度を付けた単勝の成績は、道具「印の成績」で出す（``tools/印の成績/mark_stats.py --win h2h_ability/win-day_before``）。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yosou.form_aptitude_top3.dataset import WinTargetData  # noqa: E402
from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.win_model import WIN_VARIANTS, WinComparison, WinPredictionTruth, WinVariantSpec  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = _REPO_ROOT / "reports" / "既存モデルの改善"
#: P コア（論理 CPU 0〜11）のマスク。LightGBM と CatBoost が E コアに載ると止まったように遅くなることがある。
_P_CORES = 0xFFF


def main() -> None:
    args = _parser().parse_args()
    {"run": _run, "summary": _summary}[args.step](args)


def _run(args: argparse.Namespace) -> None:
    _pin_to_p_cores()
    settings = _with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    runner = WalkForwardRunner(WindowTrainer(settings), WINDOWS)
    predictions = PredictionStore(args.root / "predictions")
    tables = TableStore(args.root / "tables")
    chosen = [spec for spec in WIN_VARIANTS if not args.variants or spec.key in args.variants]
    for spec in chosen:
        if predictions.exists(spec.table, spec.key) and not args.force:
            print(f"{spec.variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        if not tables.exists(spec.table):
            raise FileNotFoundError(f"{spec.variant.name}: 学習データの表 {args.root / 'tables' / spec.table} がありません"
                                    "（h2h_check.py tables / pace_check.py tables で作る）")
        print(f"{spec.variant.name}: 表 {spec.table} を読んで、目的変数を「1着」に持ち替えています …", flush=True)
        data = WinTargetData().training(tables.read(spec.table, spec.catalog))
        frame, log = runner.run(data, spec.variant)
        print(f"{spec.variant.name}: {predictions.write(spec.table, spec.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    truth = WinPredictionTruth(args.root / "tables", args.root / "predictions")
    store = PredictionStore(args.root / "predictions")
    lines = [f"# 1着のモデル — 確率の誤差（{args.day}）", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             "比べる相手は「オッズから見た勝率をそのまま確率にしたもの」（何も学ばない）。モデルのログ損失がこれより小さければ、",
             "馬の情報がオッズに上乗せの情報を足している。木曜はオッズの無い時点なので、相手の値は参考（確定オッズを知っていたらの値）。",
             "◎（単勝の期待値がいちばん高い馬）と期待度を付けた単勝の成績は、道具「印の成績」の表（`reports/印の成績/`）で見る。", ""]
    for spec in WIN_VARIANTS:
        lines += _section(spec, truth, store)
    out = args.out or (args.root / "compare" / f"1着のモデル-{args.day:%Y%m%d}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}", flush=True)


def _section(spec: WinVariantSpec, truth: WinPredictionTruth, store: PredictionStore) -> list[str]:
    if not store.exists(spec.table, spec.key):
        return [f"## {spec.variant.name}", "", "予測がまだ無い。", ""]
    table = WinComparison().by_window(truth.read(spec.table, spec.key))
    return [f"## {spec.variant.name}（表 {spec.table}）", "", table.to_markdown(index=False), ""]


def _with_threads(settings: HyperparameterSettings, threads: int) -> HyperparameterSettings:
    """学習のスレッド数を ``threads`` にした設定（ほかのハイパーパラメータは予想の初期値のまま）。

    同じマシンでほかの学習が全部のコアを使っていると、スレッドの取り合いで止まったように遅くなるため、数を絞る。
    スレッド数は、木の作り方（学習の結果）を変えない。
    """
    values = settings.to_dict()
    values["lightgbm"]["params"]["n_jobs"] = threads
    values["catboost"]["params"]["thread_count"] = threads
    return HyperparameterSettings.from_dict(values)


def _pin_to_p_cores() -> None:
    """Windows では、このプロセスを P コアだけで動かす（学習のスレッドも従う）。ほかの OS では何もしない。

    ハンドルとマスクは 64 ビットなので、ctypes に型を教えてから呼ぶ（教えないと 32 ビットに切られ、黙って失敗する）。
    失敗したら止める（全コアで走ると、同じマシンのほかの学習とぶつかる）。
    """
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), _P_CORES):
        raise OSError(f"P コアへの割り当てに失敗しました（エラー {ctypes.get_last_error()}）")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="1着のモデルを時点ごとに7つの区切りで学ぶ", allow_abbrev=False)
    parser.add_argument("step", choices=("run", "summary"), help="run（学習する）・summary（確率の誤差の表を書く）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方",
                        help=f"run で回す作り方（{' / '.join(spec.key for spec in WIN_VARIANTS)}。省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="表（tables/）と予測（predictions/）と結果（compare/）の置き場所")
    parser.add_argument("--out", type=Path, default=None, help="summary の結果を書くファイル（既定: compare/1着のモデル-<日付>.md）")
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(), help="summary の結果のファイル名と題に付ける日付")
    return parser


if __name__ == "__main__":
    main()
