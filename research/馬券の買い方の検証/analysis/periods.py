"""期間の定数。予測を出す期間、ウォームアップの始まり、探索（検証期間）と確認（テスト期間）。docs/03-protocol.md と同じ値。"""

from __future__ import annotations

from datetime import date, timedelta

#: 予測を出す期間（両端を含む）。探索期間と確認期間を合わせたもの。
PREDICTION_FIRST_DAY = date(2025, 7, 1)
PREDICTION_LAST_DAY = date(2026, 9, 30)
#: 過去走・過去の荒れ率の計算にだけ使う出走を読み始める日。予想モデルの学習の既定（ウォームアップ 2020年1月〜）と同じにし、
#: 特徴量が学習のときと同じ材料から作られるようにする。
WARMUP_FIRST_DAY = date(2020, 1, 1)
#: 探索（買い方を探す）期間 = 予想モデルの検証期間。
SEARCH_FIRST_DAY = date(2025, 7, 1)
SEARCH_LAST_DAY = date(2025, 12, 31)
#: 確認（1回だけ確かめる）期間 = 予想モデルのテスト期間。
CONFIRM_FIRST_DAY = date(2026, 1, 1)
CONFIRM_LAST_DAY = date(2026, 9, 30)


def day_after(day: date) -> date:
    """翌日。``TrainingData.between`` の終わりは含まないので、最後の日を含めたいときに使う。"""
    return day + timedelta(days=1)
