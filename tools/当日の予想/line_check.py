"""当日の予想のモデルごとに、買いにする期待値の線を、学習に使っていない期間で確かめる。

    uv run python tools/当日の予想/line_check.py      # 結果を reports/当日の予想/線の確かめ.md にも書く（数分かかる）

保存済みのモデル（当日の予想・フォワードテストが使うものと同じ）で、線を 1.2 から上げたときの複勝の回収率と、
その下限（開催日を丸ごと取り直すブートストラップの 90% の幅の下側）を、2つの期間で出す。

- 線を選ぶ期間: 検証期間（設定の valid_from 〜 test_from の前日）。学習には使っていない（早期終了の判定にだけ使った）。
- 確かめる期間: テスト期間（test_from 〜 DB の最後）。線を選ぶのには使わない。

選ぶ期間で「点数が 100 以上で下限が 100% に届く」いちばん低い線を選び、確かめる期間でも届けば、その線を使う。
届かなければ、そのモデルは「買い」を出さず「参考」にする。決めた値は predict_today.py の MODELS に手で書く
（このツールは設定を書き換えない。馬体重ありの線はフォワードテストが使っているので変えない）。
確定オッズでの検証なので、買う時点のオッズでは結果が下がりうる。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0]), str(HERE)]

from 共通 import cli, db, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.custom_binary.dataset import CustomDataset  # noqa: E402
from yosou.custom_binary.feature.default_registry import DefaultRegistry  # noqa: E402
from yosou.custom_binary.store import PROJECT_ROOT  # noqa: E402
from yosou.custom_binary.workflow import LoadedModel  # noqa: E402
from yosou.shared.dataset.column_names import RACE_DATE  # noqa: E402

from line_backtest import LineBacktest  # noqa: E402
from line_selection import CANDIDATE_LINES, LOWER_BOUND_FLOOR, MIN_BETS, LineSelection  # noqa: E402
from predict_today import MODELS  # noqa: E402

SAVED = PROJECT_ROOT / "reports" / "当日の予想" / "線の確かめ.md"
LINE_COLUMNS = ["線", "選ぶ_点数", "選ぶ_複勝回収率", "選ぶ_下限", "確かめる_点数", "確かめる_複勝回収率", "確かめる_下限"]


def main(args) -> None:
    registry = DefaultRegistry().build()
    decisions, tables = [], []
    for model in MODELS:
        loaded = LoadedModel.load(model.folder(registry), registry)
        period = loaded.settings.period
        with db.open_db(args.db) as con:
            data = CustomDataset(con, loaded.settings, registry).training()
        choose_data = data.between(period.valid_first_day, period.test_first_day)
        confirm_data = data.between(period.test_first_day, None)
        backtest = LineBacktest(loaded)
        choose = backtest.results(choose_data, CANDIDATE_LINES)
        confirm = backtest.results(confirm_data, CANDIDATE_LINES)
        decision = LineSelection().decide(choose, confirm)
        now = f"{model.line:g}" if model.buys else "参考"
        found = "参考（買わない）" if decision.line is None else f"{decision.line:g}"
        decisions.append([model.label, now, found, decision.reason])
        title = f"{model.label}（選ぶ期間 {_span(choose_data)}・確かめる期間 {_span(confirm_data)}）"
        tables.append(Table(LINE_COLUMNS, [_row(line, choose[line], confirm[line]) for line in CANDIDATE_LINES],
                            title=title))
    summary = Table(["モデル", "今の線", "確かめた結果", "理由"], decisions, title="モデルごとの線", note=(
        f"選ぶ期間で点数 {MIN_BETS} 以上・複勝の回収率の下限 {LOWER_BOUND_FLOOR:.0%} 以上のいちばん低い線を選び、"
        "確かめる期間でも同じ基準に届くかを見た。下限は開催日を丸ごと取り直したブートストラップの 90% の幅の下側。"
        "期待値と払戻は確定オッズで計算したもので、買う時点のオッズでは下がりうる。"
        "「今の線」は predict_today.py の MODELS の設定。馬体重ありの線 1.2 は、フォワードテスト（tools/フォワードテスト/）が"
        "同じ線で記録しているので、この表の結果では変えず、フォワードテストの結果で判断する。"
    ))
    result = [summary, *tables]
    cli.emit(result, args)
    SAVED.parent.mkdir(parents=True, exist_ok=True)
    render.write(render.render(result, "markdown"), SAVED, fmt="markdown")
    print(f"\n保存先: {SAVED}")


def _row(line: float, choose: dict, confirm: dict) -> list:
    return [f"{line:g}", choose["点数"], _percent(choose["複勝回収率"]), _percent(choose["複勝回収率の下限"]),
            confirm["点数"], _percent(confirm["複勝回収率"]), _percent(confirm["複勝回収率の下限"])]


def _span(data) -> str:
    if not len(data):
        return "なし"
    days = data.ids[RACE_DATE]
    return f"{days.min():%Y-%m-%d}〜{days.max():%Y-%m-%d}"


def _percent(value) -> str | None:
    return None if value is None else f"{value:.1%}"


def build_parser():
    return cli.build_parser(__doc__, limit=None)


if __name__ == "__main__":
    cli.run(build_parser(), main)
