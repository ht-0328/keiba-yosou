"""まとまり D（その日の馬場の傾向）の SQL。合成データだけを使う。"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from 合成DB import synth
from 共通 import db

from 既存モデルの改善.analysis.graded_race import D_NAMES, DayBiasReader

_DAY = "20240406"


def _day_db(path):
    """同じ日・同じ競馬場の芝の 1R・2R・3R（どれも8頭）。1R と 2R は、内の馬番1〜3が4コーナー1〜3番手で1〜3着（前残り・内有利）。"""
    rows = synth.Sample()
    for no in ("01", "02", "03"):
        race_row = synth.race(_DAY, no, field_size="08", entries="08")
        rows.ra.append(race_row)
        for num in range(1, 9):
            rows.se.append(synth.runner(race_row, num, num, num, hid=f"20200000{no}{num:02d}"))
    return synth.build_db(path, rows)


def test_d_uses_only_races_two_before(tmp_path):
    with db.open_db(_day_db(tmp_path / "d.duckdb")) as con:
        frame = DayBiasReader(con).read(date(2024, 1, 1))
    by_race = frame.assign(no=frame["race_id"].str[-2:]).groupby("no")
    counts = by_race["その日の先のレースの数"].first()
    # 2つ前のレースまでしか使わないので、1R・2R は 0、3R は 1R だけ
    assert counts.tolist() == [0.0, 0.0, 1.0]
    third = frame[frame["race_id"].str.endswith("03")]
    # 1R の3着以内は4コーナー 1〜3番手（8頭）→ 位置の平均は 2/8。3頭とも内（馬番が頭数の半分以下）
    assert third["その日の前残りの度合い"].iloc[0] == pytest.approx(2 / 8)
    assert third["その日の内の度合い"].iloc[0] == pytest.approx(1.0)
    first = frame[frame["race_id"].str.endswith("01")]
    assert first[list(D_NAMES[1:])].isna().all().all()


def test_d_fit_is_larger_for_inner_horses_on_an_inner_day(tmp_path):
    with db.open_db(_day_db(tmp_path / "d.duckdb")) as con:
        frame = DayBiasReader(con).read(date(2024, 1, 1))
    third = frame[frame["race_id"].str.endswith("03")].assign(horse_no=lambda f: f["horse_id"].str[-2:].astype(int)).sort_values("horse_no")
    fit = third["枠と馬場の合い具合"].to_numpy()
    assert fit[0] > 0 > fit[-1]
    # 直近の走りが無い馬（3R の馬はこの日が初めて）は脚質が分からないので、脚質との合い具合は欠損値
    assert pd.isna(third["脚質と馬場の合い具合"]).all()
