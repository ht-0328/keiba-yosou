"""材料を1つずつ足す実験の表を作って保存する（研究「既存モデルの改善」の入口⑥）。

    uv run python research/既存モデルの改善/build_experiments.py

先に build_tables.py で全頭の学習データの表を作っておく。元DB から 2016年からの全出走と、券種ごとの確定オッズを読み、
能力指数・当日の馬場傾向・近走の市場に対する成績・騎手と血統の市場に対する成績・券種ごとの支持を作って、
全頭の学習データに足した表を reports/既存モデルの改善/tables/form_experiments/ に保存する。
そのあと walk_forward.py --model form_experiments で、1つずつ足した作り方を回す。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.render import Table  # noqa: E402

from 既存モデルの改善.analysis.experiments import ExperimentTableBuilder  # noqa: E402
from 既存モデルの改善.analysis.repository import (  # noqa: E402
    POOL_SPECS,
    ComboPoolSupportRepository,
    FirstHorsePoolSupportRepository,
    RunnerHistoryRepository,
)
from 既存モデルの改善.analysis.tables import TableStore, spec_named  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TABLES = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"
#: 読む最初の日（DB にある最初の年）。
_FIRST_DAY = date(2016, 1, 1)


def main(args) -> None:
    store = TableStore(args.tables)
    form_spec = spec_named("form_aptitude_top3")
    form = store.read(form_spec.name, form_spec.catalog)
    print("元DB から全出走と券種ごとの確定オッズを読んでいます …", file=sys.stderr, flush=True)
    with db.open_db(args.db) as con:
        history = RunnerHistoryRepository(con).read(_FIRST_DAY)
        supports = [_support(con, spec) for spec in POOL_SPECS]
    print("材料を作っています …", file=sys.stderr, flush=True)
    data = ExperimentTableBuilder().build(form, history, supports)
    folder = store.write(spec_named("form_experiments").name, data)
    rows = [[name, float(data.features[name].notna().mean())] for name in data.features.columns[len(form.features.columns):]]
    cli.emit(Table(["足した材料", "値のある行の割合"], rows, title=f"実験の表（{len(data)}行）", note=str(folder)), args)


def _support(con, spec):
    print(f"  {spec.column} …", file=sys.stderr, flush=True)
    repository = FirstHorsePoolSupportRepository(con, spec) if spec.first_only else ComboPoolSupportRepository(con, spec)
    return repository.read(_FIRST_DAY)


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--tables", type=Path, default=_DEFAULT_TABLES, help="学習データの表の置き場所")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
