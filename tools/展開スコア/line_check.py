"""展開スコアの線（展開有利・展開不利の ±0.01）を、過去のレースで確かめる。

    uv run python tools/展開スコア/line_check.py                     # 木曜・前日・当日。結果を reports/展開スコア/線の確かめ.md にも書く（数分）
    uv run python tools/展開スコア/line_check.py --timing 前日 当日   # 時点を絞る

過去のレース（展開の予想の年ごとの確かめの予測がある 2016年〜）に、その年より前だけで学習した展開のモデルの予測と、その年より前のレースだけで
作った表 G から展開スコアを付け、線を動かしたときに、判定した馬の「実際の3着以内率 − 市場から見た3着以内率」（差。ポイント）と複勝の回収率が
どう変わるかを数える（設計書「買うレースと買い目を決める」05 の 2 の「線を決め直す」）。展開スコアの 10分位・年ごと・人気帯ごとの表も出す。
払戻は確定オッズのもので、買う時点のオッズでは下がりうる。線を変えるときは ``yosou.development_score.advantage_judge.DEFAULT_LINE`` を直す。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0]), str(HERE)]

from 共通 import cli, db, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.development_score import DEFAULT_LINE, AdvantageRuns, DevelopmentRunRepository, ScoreHistory, names  # noqa: E402
from yosou.form_aptitude_top3.command.development_root_argument import DEFAULT_DEVELOPMENT_ROOT  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402

from line_tally import LineTally  # noqa: E402

SAVED = HERE.parents[1] / "reports" / "展開スコア" / "線の確かめ.md"
#: 答え合わせに付ける材料の列。
_TRUTH_COLUMNS: list[str] = ["race_id", "horse_id", names.TOP3, names.MARKET_TOP3, "popularity", "place_payout", "win_payout"]


def main(args) -> None:
    timings = [PredictionTiming.parse(text) for text in args.timing] if args.timing else list(PredictionTiming)
    with db.open_db(args.db) as con:
        print("2011年からの全出走を読んで、表 G の材料（脚質・ペース・市場の見立て）を作っています …", file=sys.stderr, flush=True)
        prepared = AdvantageRuns().build(DevelopmentRunRepository(con).read())
    truth = prepared[_TRUTH_COLUMNS].assign(race_id=prepared["race_id"].astype(str), horse_id=prepared["horse_id"].astype(str))
    history = ScoreHistory(args.development_root)
    summary, tables = [], []
    for timing in timings:
        print(f"{timing.label}: 年ごとの確かめの予測に展開スコアを付けています …", file=sys.stderr, flush=True)
        scored = history.of(timing, prepared).merge(truth, on=["race_id", "horse_id"], how="left")
        tally = LineTally(scored.dropna(subset=[names.TOP3, names.MARKET_TOP3]))
        by_line = tally.by_line()
        default = by_line[by_line["線"] == f"±{args.line:g}"].iloc[0]
        summary.append([timing.label, len(tally), f"{tally.correlation():.4f}", default["有利_頭数"], default["有利_差"], default["有利_複勝回収率"],
                        default["不利_頭数"], default["不利_差"], default["不利_複勝回収率"]])
        tables += [
            _table(by_line, f"{timing.label}: 線ごと（全期間）", "差 = 実際の3着以内率 − 市場から見た3着以内率（ポイント）。向きの合った年 = 有利ならプラス、不利ならマイナスだった年の数"),
            _table(tally.by_year(args.line), f"{timing.label}: 線 ±{args.line:g} の年ごと"),
            _table(tally.by_decile(), f"{timing.label}: 展開スコアの 10分位（1 がいちばん低い）"),
            _table(tally.by_popularity(args.line), f"{timing.label}: 線 ±{args.line:g} の人気帯ごと"),
        ]
    head = Table(["時点", "頭数", "相関", "有利_頭数", "有利_差", "有利_複勝回収率", "不利_頭数", "不利_差", "不利_複勝回収率"], summary,
                 title=f"時点ごとのまとめ（線 ±{args.line:g}）", note=(
                     "相関 = 展開スコアと「3着以内 − 市場から見た3着以内率」の相関。差はポイント、回収率は %（確定オッズ。買う時点では下がりうる）。"
                     "表 G は各年の1月1日より前のレースだけ、展開の予測はその年より前だけで学習したモデルのもの"))
    result = [head, *tables]
    cli.emit(result, args)
    SAVED.parent.mkdir(parents=True, exist_ok=True)
    render.write(render.render(result, "markdown"), SAVED, fmt="markdown")
    print(f"\n保存先: {SAVED}", file=sys.stderr)


def _table(frame, title: str, note: str = "") -> Table:
    return Table([str(column) for column in frame.columns], frame.astype(object).where(frame.notna(), None).values.tolist(), title=title, note=note)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--timing", nargs="*", default=None, help="時点（木曜・前日・当日。省略すると全部）")
    parser.add_argument("--line", type=float, default=DEFAULT_LINE, help=f"年ごと・人気帯ごとの表で使う線（既定: {DEFAULT_LINE:g}）")
    parser.add_argument("--development-root", type=Path, default=DEFAULT_DEVELOPMENT_ROOT,
                        help="予想「展開から着順を予想」の置き場所（既定: reports/展開から着順を予想。その out_of_sample/ を読む）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
