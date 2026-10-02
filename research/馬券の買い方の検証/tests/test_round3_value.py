"""契約: 見込みの倍率は区切りより前の払戻だけで学び、期待値は穴馬だけに付き、消は直前の1年で決めた線で付き、印は設計書の順で付く。"""

import numpy as np
import pandas as pd
import pytest

from 既存モデルの改善.analysis.windows import window_named

from 馬券の買い方の検証.analysis.value_betting import DangerExclusion, MarkAssigner, PlacePriceFitter, PlaceValueCalculator
from 馬券の買い方の検証.analysis.value_betting import columns as c

from round3_fixtures import WINDOW_1, runners


def test_price_fitter_uses_only_rows_before_the_valid_period():
    history = pd.DataFrame({
        c.RACE_DATE: pd.to_datetime(["2021-05-01"] * 4 + ["2022-08-01"] * 4),
        c.PLACE_ODDS: 2.0, c.PLACE_ODDS_HIGH: 2.4, c.PLACE_PAYOUT: [260.0, 260.0, 0.0, 260.0, 400.0, 400.0, 400.0, 400.0],
    })
    estimator = PlacePriceFitter(history).for_window(window_named(WINDOW_1))  # 検証は 2022-07-01 から
    estimate = estimator.estimate(pd.Series([2.0]), pd.Series([2.4]))
    assert estimate.iloc[0] == pytest.approx(2.0 * 1.3)  # 2022年8月の 400円は使わない


def test_place_value_is_only_for_longshots_and_small_fields_use_top2():
    rows = runners(WINDOW_1, c.PART_TEST, days=1, races=1).copy()
    rows.loc[rows[c.HORSE_NO] == 12, c.FIELD_SIZE] = 7
    estimator = PlacePriceFitter(pd.DataFrame({
        c.RACE_DATE: pd.to_datetime(["2020-01-01"] * 3), c.PLACE_ODDS: [3.0, 3.0, 6.0], c.PLACE_ODDS_HIGH: [3.6, 3.6, 7.2],
        c.PLACE_PAYOUT: [330.0, 0.0, 720.0],
    })).for_window(window_named(WINDOW_1))
    valued = PlaceValueCalculator(estimator).add(rows).set_index(c.HORSE_NO)
    assert valued.loc[1, [c.PLACE_PROB, c.PLACE_VALUE]].isna().all()  # 人気馬には穴馬モデルの確率が無いので、期待値も無い
    assert valued.loc[1, c.PLACE_PRICE] > 0  # 見込みの倍率は、複勝オッズのあるどの馬にも付く（表示のため）
    assert valued.loc[5, c.PLACE_PROB] == pytest.approx(valued.loc[5, c.LONGSHOT_PROB])
    assert valued.loc[5, c.PLACE_VALUE] == pytest.approx(valued.loc[5, c.PLACE_PROB] * valued.loc[5, c.PLACE_PRICE])
    ratio = valued.loc[12, c.MARKET_TOP2] / valued.loc[12, c.MARKET_TOP3]
    assert valued.loc[12, c.PLACE_PROB] == pytest.approx(valued.loc[12, c.LONGSHOT_PROB] * ratio)  # 7頭以下は2着まで


def _favorites(count: int) -> pd.DataFrame:
    danger = np.linspace(0.0, 0.2, count)
    return pd.DataFrame({
        c.POPULARITY: 1, c.MARKET_TOP3: 0.6, c.DANGER_PROB: 0.4 + danger, c.TOP3: np.where(danger >= 0.1, 0, 1),
        c.FIELD_SIZE: 16,
    })


def test_danger_exclusion_learns_a_line_per_band_and_marks_only_favorites():
    exclusion = DangerExclusion().fit(_favorites(120))
    line = exclusion.lines["1番人気"]
    assert 0.0 < line <= 0.1 and "2〜3番人気" not in exclusion.lines  # 2〜3番人気の行が無いので線も無い
    rows = pd.DataFrame({c.POPULARITY: [1, 1, 2, 9], c.MARKET_TOP3: 0.6, c.DANGER_PROB: [0.41 + line, 0.4 + line - 0.01, 0.9, np.nan]})
    marked = exclusion.mark(rows)
    assert marked[c.EXCLUDED].tolist() == [True, False, False, False]  # 2番人気は線が無いので消にならない。9番人気は人気馬でない
    assert marked[c.DANGER].iloc[0] == pytest.approx(line + 0.01) and np.isnan(marked[c.DANGER].iloc[3])


def test_marks_follow_the_design_order():
    rows = pd.DataFrame({
        c.WINDOW: "w", c.PART: "テスト", c.RACE_ID: "r", c.HORSE_NO: range(1, 9),
        c.FORM_PROB: [0.80, 0.70, 0.55, 0.40, 0.30, 0.25, 0.10, 0.05], c.MARKET_TOP3: [0.85, 0.60, 0.50, 0.40, 0.20, 0.15, 0.10, 0.05],
        c.EXCLUDED: [True, False, False, False, False, False, False, False],
        c.PLACE_VALUE: [np.nan, np.nan, np.nan, 1.1, 1.3, 1.6, 0.9, 1.0],
    })
    marks = MarkAssigner().assign(rows).set_index(c.HORSE_NO)[c.MARK]
    # 1番は消。残りの3着以内の確率の順で 2◎ 3○ 4▲ 5△ 6△。☆は穴馬の期待値1位（6番 1.6）だが △ が付いているので付けない。
    # 注は印の無い 7・8番のうち上げ下げ（logit(予想) − logit(市場)）が大きい 8番（同じ 0.05 → 0）ではなく 7番（0.10 対 0.10 → 0）… 同点は先頭
    assert marks.loc[1] == "消" and marks.loc[2] == "◎" and marks.loc[3] == "○" and marks.loc[4] == "▲"
    assert marks.loc[5] == "△" and marks.loc[6] == "△"
    assert (marks == "注").sum() == 1 and marks.loc[7] == "注"
    starred = rows.assign(**{c.PLACE_VALUE: [np.nan, np.nan, np.nan, 1.1, 1.3, 1.2, 1.4, 1.0]})
    marks = MarkAssigner().assign(starred).set_index(c.HORSE_NO)[c.MARK]
    assert marks.loc[7] == "☆" and marks.loc[8] == "注"
    low = rows.assign(**{c.PLACE_VALUE: [np.nan, np.nan, np.nan, 1.1, 1.0, 1.0, 1.2, 1.0]})
    assert (MarkAssigner().assign(low)[c.MARK] == "☆").sum() == 0  # 1.25 未満なら ☆ は付けない
