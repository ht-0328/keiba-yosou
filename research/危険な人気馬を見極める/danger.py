"""危険な人気馬を見極める（研究「危険な人気馬を見極める」の入口）。

    uv run python research/危険な人気馬を見極める/danger.py run      # 1. オッズだけのモデルを出発点にした人気馬の予想を、7つの区切りで学ぶ
    uv run python research/危険な人気馬を見極める/danger.py top      # 2. 危険度の上位の人気馬の成績を、今の本番と比べる（数秒）
    uv run python research/危険な人気馬を見極める/danger.py flags    # 2'. 線を検証期間の危険度の上位 5%・10% にした消の表（数秒）
    uv run python research/危険な人気馬を見極める/danger.py marks    # 4. 道具「印の成績」の結果を作り方ごとに並べる（数秒）
    uv run python research/危険な人気馬を見極める/danger.py form     # 5. 全頭の予想（前日の3着以内と1着）も、オッズだけのモデルを出発点にして7つの区切りで学ぶ
    uv run python research/危険な人気馬を見極める/danger.py longshots  # 6. 穴馬の予想も同じく学び、穴馬度の上位の成績を今の ☆ の元と比べる
    uv run python research/危険な人気馬を見極める/danger.py place    # 7. 穴馬の予想を複勝オッズを出発点に学び、6番人気以下の複勝の成績を出す
    uv run python research/危険な人気馬を見極める/danger.py unseen   # 8. 6番人気以下の複勝の選び方を、まだ見ていない 2021年前半〜2022年前半で確かめる

2 のあと、道具「印の成績」で作り方ごとに印と全券種の買い目の成績を出す（3。README の「動かし方」）。
学習データは研究「既存モデルの改善」の build_tables.py が保存した表（favorites_out_of_top3）を読む。
出るもの（Git 対象外）: ``reports/危険な人気馬を見極める/`` の ``predictions/``・``危険度の上位.md``・``印の成績/``・``印の成績の比べ.md``。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

import pandas as pd  # noqa: E402

from 共通 import render  # noqa: E402

from yosou.favorites_out_of_top3.setting import DEFAULT_SETTINGS_PATH as FAVORITES_SETTINGS  # noqa: E402
from yosou.form_aptitude_top3.dataset import WinTargetData  # noqa: E402
from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH as FORM_SETTINGS  # noqa: E402
from yosou.longshots_in_top3.setting import DEFAULT_SETTINGS_PATH as LONGSHOTS_SETTINGS  # noqa: E402
from yosou.upset_level.setting import DEFAULT_SETTINGS_PATH as UPSET_SETTINGS  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 既存モデルの改善.analysis.head_to_head import base_table_rated, variant_keyed  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore, spec_named  # noqa: E402
from 既存モデルの改善.analysis.variants import variant_named  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, UpsetWindowTrainer, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.win_model.win_variants import spec_keyed  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS, TestWindow, windows_of  # noqa: E402

from 危険な人気馬を見極める.analysis.calibrated_window_trainer import CalibratedWindowTrainer  # noqa: E402
from 危険な人気馬を見極める.analysis.danger_top_report import DangerTopReport  # noqa: E402
from 危険な人気馬を見極める.analysis.longshot_top_report import LongshotTopReport  # noqa: E402
from 危険な人気馬を見極める.analysis.mark_comparison import MarkComparison  # noqa: E402
from 危険な人気馬を見極める.analysis.market_based_window_trainer import MarketBasedWindowTrainer  # noqa: E402
from 危険な人気馬を見極める.analysis.place_bet_report import PlaceBetReport  # noqa: E402
from 危険な人気馬を見極める.analysis.place_market_window_trainer import (  # noqa: E402
    PLACE_MARKET_COLUMN,
    PLACE_MARKET_RATE,
    PlaceMarketWindowTrainer,
)
from 危険な人気馬を見極める.analysis.strict_danger_flags import StrictDangerFlags  # noqa: E402

_OUT = _REPO_ROOT / "reports" / "危険な人気馬を見極める"
_TABLES = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"
_CURRENT_PREDICTIONS = _REPO_ROOT / "reports" / "既存モデルの改善" / "predictions"
#: 人気馬の予想と、今の本番の作り方（people_market）。
_MODEL, _CURRENT = "favorites_out_of_top3", "people_market"
#: この研究の作り方の名前（保存するファイルの名前）。
CALIBRATED = "calibrated"
_CALIBRATED_NAME = "今の本番の列 ＋ オッズだけのモデルを出発点と比べる相手にする"
#: P コア（論理 CPU 0〜11）のマスク。LightGBM と CatBoost が E コアに載ると止まったように遅くなることがある。
_P_CORES = 0xFFF
#: 印の成績の作り方（置き場所 ``印の成績/<フォルダ>/`` → 表に出す名前）と、結果のファイルの名前（全頭の予想の名前）。
#: 線を厳しくした消の表（``predictions/消の表/<フォルダ>.pkl``）の、検証期間の上位の割合。
STRICT_SHARES: dict[str, float] = {"新しい危険度・上位5%": 0.05, "新しい危険度・上位10%": 0.10}
MARK_RUNS: dict[str, str] = {"本番": "今の本番", "消なし": "消を使わない", "新しい危険度": "新しい危険度",
                             **{key: key for key in STRICT_SHARES},
                             "全頭も新しい出発点": "全頭の予想も新しい出発点（消は上位5%）",
                             "穴馬の複勝を足した本番": "今の本番＋穴馬の複勝",
                             "新しい危険度＋穴馬の複勝": "新しい危険度＋穴馬の複勝",
                             "新しい危険度・上位5%＋穴馬の複勝": "新しい危険度・上位5%＋穴馬の複勝",
                             "穴馬軸の3連複・超荒れ": "今の本番＋穴馬軸の3連複（超荒れも分けた荒れ具合で選ぶ）",
                             "荒れ具合ごとの3連複": "今の本番＋荒れ具合ごとの3連複（固い 予想上位4頭・中荒れ 穴−強−9番人気まで・大荒れ 穴−9番人気まで−9番人気まで・超荒れ 穴−強−全頭）"}
_MARK_FILE = "h2h_ability_h2h-day_before.md"
#: 穴馬の予想（今の本番の作り方は人気馬と同じ名前 people_market）。
_LONGSHOTS = "longshots_in_top3"
#: 穴馬の予想の、複勝オッズから見た評価（M）も足した作り方と、それを複勝オッズを出発点にして学んだ予測の名前。
_PLACE_ODDS, PLACE_MARKET = "place_odds", "place_market"
#: まだ見ていない期間の区切り（研究「既存モデルの改善」の7つの区切りより前の、半年ずつの3つ）と、その予測の名前。
UNSEEN_WINDOWS: tuple[TestWindow, ...] = (
    TestWindow("2021年前半", date(2020, 7, 1), date(2021, 1, 1), date(2021, 6, 30)),
    TestWindow("2021年後半", date(2021, 1, 1), date(2021, 7, 1), date(2021, 12, 31)),
    TestWindow("2022年前半", date(2021, 7, 1), date(2022, 1, 1), date(2022, 6, 30)),
)
UNSEEN = "h2h-day_before-unseen"
#: 荒れ具合の予想（今の本番の作り方）を、まだ見ていない期間の区切りで学んだ予測の名前。
_UPSET, UPSET_UNSEEN = "upset_level", "unseen"
#: 全頭の予想の、前日の3着以内と1着の作り方（道具「印の成績」の既定と同じ）。
FORM_TOP3, FORM_WIN = "h2h-day_before", "win-day_before"


def main() -> None:
    args = _parser().parse_args()
    {"run": _run, "top": _top, "flags": _flags, "marks": _marks, "form": _form, "longshots": _longshots,
     "place": _place, "unseen": _unseen, "upset": _upset}[args.step](args)


def _run(args: argparse.Namespace) -> None:
    _pin_to_p_cores()
    spec = spec_named(_MODEL)
    data = TableStore(_TABLES).read(spec.name, spec.catalog)
    settings = _with_threads(HyperparameterSettings.load(None, defaults=FAVORITES_SETTINGS), args.threads)
    store = PredictionStore(args.out / "predictions")
    if store.exists(_MODEL, CALIBRATED) and not args.force:
        print(f"{_CALIBRATED_NAME}: 済んでいるので飛ばします", flush=True)
        return
    variant = variant_named(_MODEL, _CURRENT)
    trainer = CalibratedWindowTrainer(settings)
    frame, log = WalkForwardRunner(trainer, windows_of(_MODEL)).run(data, variant)
    print(f"{_CALIBRATED_NAME}: {store.write(_MODEL, CALIBRATED, frame, log)}", flush=True)


def _top(args: argparse.Namespace) -> None:
    spec = spec_named(_MODEL)
    data = TableStore(_TABLES).read(spec.name, spec.catalog)
    evaluation = pd.concat([data.ids[["レースID", "馬ID"]], data.evaluation], axis=1)
    predictions = {"今の本番": PredictionStore(_CURRENT_PREDICTIONS).read(_MODEL, _CURRENT),
                   _CALIBRATED_NAME: PredictionStore(args.out / "predictions").read(_MODEL, CALIBRATED)}
    _write([DangerTopReport().table(evaluation, predictions)], args.out / "危険度の上位.md")


def _flags(args: argparse.Namespace) -> None:
    predictions = PredictionStore(args.out / "predictions").read(_MODEL, CALIBRATED)
    folder = args.out / "predictions" / "消の表"
    folder.mkdir(parents=True, exist_ok=True)
    for key, share in STRICT_SHARES.items():
        flags = StrictDangerFlags(share).build(predictions)
        flags.to_pickle(folder / f"{key}.pkl")
        print(f"{key}: 消 {int(flags['is_danger'].sum()):,}頭 → {folder / f'{key}.pkl'}", flush=True)


def _marks(args: argparse.Namespace) -> None:
    folder = args.out / "印の成績"
    reports = {name: folder / key / _MARK_FILE for key, name in MARK_RUNS.items() if (folder / key / _MARK_FILE).is_file()}
    _write(MarkComparison().tables(reports), args.out / "印の成績の比べ.md")


def _form(args: argparse.Namespace) -> None:
    """全頭の予想の前日の3着以内（h2h-day_before）と1着（win-day_before）を、オッズだけのモデルを出発点にして学ぶ。

    予測は道具「印の成績」が読む形のまま ``predictions/h2h_ability/<作り方>.pkl`` に書く（--form・--win にそのまま渡せる）。
    """
    _pin_to_p_cores()
    settings = _with_threads(HyperparameterSettings.load(None, defaults=FORM_SETTINGS), args.threads)
    runner = WalkForwardRunner(MarketBasedWindowTrainer(settings), WINDOWS)
    store = PredictionStore(args.out / "predictions")
    top3, win = variant_keyed(FORM_TOP3), spec_keyed(FORM_WIN)
    for variant, load in ((top3, lambda: _form_table(top3.model)),
                          (win.variant, lambda: WinTargetData().training(_form_table(win.table)))):
        if store.exists(variant.model, variant.key) and not args.force:
            print(f"{variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        frame, log = runner.run(load(), variant)
        print(f"{variant.name}（オッズだけのモデルを出発点）: {store.write(variant.model, variant.key, frame, log)}", flush=True)


def _longshots(args: argparse.Namespace) -> None:
    """6番人気以下（穴馬）は「来そうな馬を見つける」。穴馬の予想の今の本番の作り方を、オッズだけのモデルを出発点にして学び、
    穴馬度の上位の成績を、今の ☆ の元（全頭の予想）と比べる。"""
    spec = spec_named(_LONGSHOTS)
    tables = TableStore(args.out / "tables")
    if not tables.exists(spec.name):
        raise FileNotFoundError(f"穴馬の予想の表がありません: {args.out / 'tables' / spec.name}（README の「動かし方」の build_tables.py で作る）")
    data = tables.read(spec.name, spec.catalog)
    store = PredictionStore(args.out / "predictions")
    if not store.exists(_LONGSHOTS, CALIBRATED) or args.force:
        _pin_to_p_cores()
        settings = _with_threads(HyperparameterSettings.load(None, defaults=LONGSHOTS_SETTINGS), args.threads)
        frame, log = WalkForwardRunner(CalibratedWindowTrainer(settings), windows_of(_LONGSHOTS)).run(
            data, variant_named(_LONGSHOTS, _CURRENT))
        print(f"穴馬の予想（オッズだけのモデルを出発点）: {store.write(_LONGSHOTS, CALIBRATED, frame, log)}", flush=True)
    evaluation = pd.concat([data.ids[["レースID", "馬ID"]], data.evaluation], axis=1)
    predictions = {"今の ☆ の元（全頭の予想）": PredictionStore(_CURRENT_PREDICTIONS).read("h2h_ability", FORM_TOP3),
                   "穴馬の予想（オッズだけのモデルを出発点）": store.read(_LONGSHOTS, CALIBRATED)}
    _write([LongshotTopReport().table(evaluation, predictions)], args.out / "穴馬度の上位.md")


def _place(args: argparse.Namespace) -> None:
    """6番人気以下の複勝で回収率 100% を超える。穴馬の予想を、複勝オッズから見た3着以内率を出発点にして学び、
    「予想 − 複勝オッズから見た3着以内率」が線以上の馬の複勝の成績を、全頭の予想で同じく選んだ場合と比べる。"""
    spec = spec_named(_LONGSHOTS)
    tables = TableStore(args.out / "tables")
    if not tables.exists(spec.name):
        raise FileNotFoundError(f"穴馬の予想の表がありません: {args.out / 'tables' / spec.name}（README の「動かし方」の build_tables.py で作る）")
    data = tables.read(spec.name, spec.catalog)
    store = PredictionStore(args.out / "predictions")
    if not store.exists(_LONGSHOTS, PLACE_MARKET) or args.force:
        _pin_to_p_cores()
        settings = _with_threads(HyperparameterSettings.load(None, defaults=LONGSHOTS_SETTINGS), args.threads)
        frame, log = WalkForwardRunner(PlaceMarketWindowTrainer(settings), windows_of(_LONGSHOTS)).run(
            data, variant_named(_LONGSHOTS, _PLACE_ODDS))
        print(f"穴馬の予想（複勝オッズを出発点）: {store.write(_LONGSHOTS, PLACE_MARKET, frame, log)}", flush=True)
    evaluation = pd.concat([data.ids[["レースID", "馬ID", "開催日"]], data.evaluation,
                            data.features[[PLACE_MARKET_RATE]].rename(columns={PLACE_MARKET_RATE: PLACE_MARKET_COLUMN})], axis=1)
    predictions = {"全頭の予想（今の本番）": PredictionStore(_CURRENT_PREDICTIONS).read("h2h_ability", FORM_TOP3),
                   "穴馬の予想（複勝オッズを出発点）": store.read(_LONGSHOTS, PLACE_MARKET)}
    _write(PlaceBetReport().tables(evaluation, predictions), args.out / "6番人気以下の複勝.md")


def _unseen(args: argparse.Namespace) -> None:
    """まだ見ていない 2021年前半〜2022年前半で、6番人気以下の複勝の選び方（全頭の予想 − 複勝オッズから見た3着以内率）を確かめる。

    全頭の予想の今の本番の作り方を、その3つの区切りで学び直し（予測は ``h2h_ability/h2h-day_before-unseen``）、
    同じ表（線ごと・区切りごとに検証で選んだ線）を書く。2022年後半は 2023年前半の区切りの検証期間として見ているので含めない。
    """
    store = PredictionStore(args.out / "predictions")
    if not store.exists("h2h_ability", UNSEEN) or args.force:
        _pin_to_p_cores()
        settings = _with_threads(HyperparameterSettings.load(None, defaults=FORM_SETTINGS), args.threads)
        top3 = variant_keyed(FORM_TOP3)
        frame, log = WalkForwardRunner(WindowTrainer(settings), UNSEEN_WINDOWS).run(_form_table(top3.model), top3)
        print(f"全頭の予想（2021〜2022年）: {store.write('h2h_ability', UNSEEN, frame, log)}", flush=True)
    spec = spec_named(_LONGSHOTS)
    data = TableStore(args.out / "tables").read(spec.name, spec.catalog)
    evaluation = pd.concat([data.ids[["レースID", "馬ID", "開催日"]], data.evaluation,
                            data.features[[PLACE_MARKET_RATE]].rename(columns={PLACE_MARKET_RATE: PLACE_MARKET_COLUMN})], axis=1)
    predictions = {"全頭の予想（2021年前半〜2022年前半）": store.read("h2h_ability", UNSEEN)}
    _write(PlaceBetReport().tables(evaluation, predictions), args.out / "6番人気以下の複勝-まだ見ていない期間.md")


def _upset(args: argparse.Namespace) -> None:
    """荒れ具合の予想の今の本番の作り方（券種ごと・当日）を、まだ見ていない 2021年前半〜2022年前半の3つの区切りで学び直す。

    予測は ``predictions/upset_level/unseen.pkl``（研究「既存モデルの改善」の ``upset_level/current.pkl`` と同じ形）。
    道具「印の成績」の --upset に渡すと、3連複の荒れ具合でレースを選ぶ買い方を、まだ見ていない期間で数えられる。
    """
    store = PredictionStore(args.out / "predictions")
    if store.exists(_UPSET, UPSET_UNSEEN) and not args.force:
        print("荒れ具合（2021〜2022年）: 済んでいるので飛ばします", flush=True)
        return
    _pin_to_p_cores()
    spec = spec_named(_UPSET)
    data = TableStore(_TABLES).read(spec.name, spec.catalog)
    trainer = UpsetWindowTrainer(_with_threads(HyperparameterSettings.load(None, defaults=UPSET_SETTINGS), args.threads))
    results = [trainer.run(data, window) for window in UNSEEN_WINDOWS]
    frame = pd.concat([frame for frame, _ in results], ignore_index=True)
    log = pd.DataFrame([row for _, rows in results for row in rows])
    print(f"荒れ具合（2021〜2022年）: {store.write(_UPSET, UPSET_UNSEEN, frame, log)}", flush=True)


def _form_table(name: str):
    """研究「既存モデルの改善」の対戦レーティングの確かめが作った、今の本番と同じ材料の表。"""
    return TableStore(_TABLES).read(name, base_table_rated(name).rated_catalog)


def _write(tables: list, path: Path) -> None:
    text = render.render(tables, "markdown")
    path.parent.mkdir(parents=True, exist_ok=True)
    render.write(text, path, fmt="markdown")
    print(text)
    print(f"\n保存先: {path}", file=sys.stderr)


def _with_threads(settings: HyperparameterSettings, threads: int) -> HyperparameterSettings:
    """学習のスレッド数を ``threads`` にした設定（ほかのハイパーパラメータは予想の初期値のまま。木の作り方は変わらない）。"""
    values = settings.to_dict()
    values["lightgbm"]["params"]["n_jobs"] = threads
    values["catboost"]["params"]["thread_count"] = threads
    return HyperparameterSettings.from_dict(values)


def _pin_to_p_cores() -> None:
    """Windows では、このプロセスを P コアだけで動かす（学習のスレッドも従う）。ほかの OS では何もしない。"""
    if sys.platform != "win32":
        return
    import ctypes

    kernel = ctypes.windll.kernel32
    kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), _P_CORES)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="危険な人気馬を見極める", allow_abbrev=False)
    parser.add_argument("step", choices=("run", "top", "flags", "marks", "form", "longshots", "place", "unseen", "upset"),
                        help="run（7つの区切りで学ぶ）・top（危険度の上位の人気馬の成績）・flags（線を厳しくした消の表）・"
                             "marks（印の成績を並べる）・form（全頭の予想もオッズだけのモデルを出発点に学ぶ）・"
                             "longshots（穴馬の予想もオッズだけのモデルを出発点に学び、穴馬度の上位の成績を出す）・"
                             "place（穴馬の予想を複勝オッズを出発点に学び、6番人気以下の複勝の成績を出す）・"
                             "unseen（6番人気以下の複勝の選び方を、まだ見ていない 2021〜2022年で確かめる）・"
                             "upset（荒れ具合の予想を、まだ見ていない 2021〜2022年の区切りで学び直す）")
    parser.add_argument("--force", action="store_true", help="run で、済んでいても回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--out", type=Path, default=_OUT, help="出力の置き場所")
    return parser


if __name__ == "__main__":
    main()
