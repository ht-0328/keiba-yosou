"""任意 SQL の契約: 読む文だけ、1文だけ、上限で切る、時間で止める。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import browse, db


def test_select_is_wrapped_and_truncated(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        table = browse.run_sql(con, "select 馬番 from se order by 馬番;", limit=4)
    assert [r[0] for r in table.rows] == ["01", "02", "03", "04"]
    assert table.meta["truncated"] is True and "打ち切り" in table.note


def test_describe_and_with_are_allowed(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        assert browse.run_sql(con, "describe se").columns[0] == "column_name"
        assert browse.run_sql(con, "with x as (select 1 as v) select v from x").rows == [[1]]


@pytest.mark.parametrize("bad", ["select 1; select 2", "", "create table t (a int)", "delete from se", "copy se to 'x.csv'"])
def test_rejects_multiple_or_writing_statements(one_race_db: Path, bad):
    with db.open_db(one_race_db) as con:
        with pytest.raises(ValueError):
            browse.run_sql(con, bad)


def test_timeout_interrupts_long_query(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        with pytest.raises(TimeoutError):
            browse.run_sql(con, "select count(*) from range(200000000) a, range(100000) b", timeout_s=0.2)
        assert browse.run_sql(con, "select 1").rows == [[1]]
