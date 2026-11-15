"""「裏まで買うか」を決めるモデル（裏が当たる確率。本番の部品 ``ReverseExactaModel``）を学ぶ。

    uv run python research/裏目を買うかの予想/fit.py --until 2025-09-06   # その日より前で学び、その日からのレースで当たり具合を出す
    uv run python research/裏目を買うかの予想/fit.py --save-models        # 全部のレースで学び、本番のモデルの置き場所に書く

裏は「1着が ○▲☆（☆ は複勝の期待値 1.25 以上だけ）のどれかで、◎ が2着か3着」。1行 = 1レースで、材料は本番と同じ部品
（``ReverseExactaFeatures``）で作り、目的は裏が当たったか（1 か 0）。
印の表は ``analysis/marked_table.py`` が書いたもの（``reports/裏目を買うかの予想/marked.pkl``）を読む（DB は開かない）。
``--save-models`` は、本番のモデルの置き場所（``reports/近走と適性から3着以内を予想/models``）の ``馬単の裏/``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "tools"))

from 今週の予想.mark_rule import TOP_MARK  # noqa: E402
from 今週の予想.model_folders import DEFAULT_MODELS  # noqa: E402
from 今週の予想.reverse_exacta_features import ReverseExactaFeatures  # noqa: E402
from 今週の予想.reverse_exacta_judge import FOLDER, LINE  # noqa: E402
from 今週の予想.reverse_exacta_model import ReverseExactaModel  # noqa: E402

#: 印の表（``analysis/marked_table.py`` が書く）。
MARKED = _ROOT / "reports" / "裏目を買うかの予想" / "marked.pkl"
#: 学ぶときのスレッドの数（発走前の通知と並べて動かしても通知を遅らせないように、全部は使わない）。
THREADS = 6


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--until", help="この日（YYYY-MM-DD）より前で学び、この日からのレースで当たり具合を出す")
    group.add_argument("--save-models", action="store_true", help="全部のレースで学び、本番のモデルの置き場所に書く")
    parser.add_argument("--marked", type=Path, default=MARKED, help="印の表（analysis/marked_table.py が書いたもの）")
    args = parser.parse_args()
    table = race_rows(pd.read_pickle(args.marked))
    features = ReverseExactaFeatures().frame(table["features"].tolist())
    labels = table["y"]
    if args.save_models:
        model = ReverseExactaModel.fit(features, labels, THREADS)
        folder = model.save(DEFAULT_MODELS / FOLDER, {"races": len(table), "reverse_hits": int(labels.sum())})
        print(f"{len(table):,} レース（裏が当たった {labels.mean():.1%}）で学び、{folder} に書いた")
        return
    learn = (table["day"] < args.until).to_numpy()
    model = ReverseExactaModel.fit(features[learn], labels[learn], THREADS)
    check = ~learn
    probability = np.clip(model.predict(features[check]), 1e-4, 1 - 1e-4)
    truth = labels[check]
    print(f"学び {learn.sum():,} レース／確かめ {check.sum():,} レース（裏が当たった {truth.mean():.1%}）")
    print(f"ログ損失 {log_loss(truth, probability):.4f}  AUC {roc_auc_score(truth, probability):.3f}  予想の平均 {probability.mean():.3f}")
    over = probability >= LINE
    print(f"確率 {LINE} 以上: {over.sum():,} レース（{over.mean():.1%}）で、裏が当たった {truth[over].mean():.1%}")


def race_rows(marked: pd.DataFrame) -> pd.DataFrame:
    """1行 = 1レースの、材料（辞書）・目的（裏が当たったか）・開催日。結果の無いレースと、材料を作れないレースは除く。"""
    maker = ReverseExactaFeatures()
    rows = []
    for race_id, race in marked.groupby(marked["race_id"].astype(str), sort=False):
        if race["finish"].isna().all():
            continue
        features = maker.of(race)
        if features is None:
            continue
        rows.append({"race_id": race_id, "day": str(pd.Timestamp(race["race_date"].iloc[0]).date()), "features": features,
                     "y": reverse_hit(race)})
    return pd.DataFrame(rows)


def reverse_hit(race: pd.DataFrame) -> int:
    """裏が当たったか（1着が相手のどれかで、◎ が2着か3着）。相手は ``ReverseExactaFeatures`` と同じ。"""
    race = race.reset_index(drop=True)
    top = race.loc[race["mark"] == TOP_MARK].iloc[0]
    winners = race.index[race["finish"] == 1]
    partners = set(ReverseExactaFeatures.partners(race))
    return int(top["finish"] in (2, 3) and len(winners) > 0 and winners[0] in partners)


if __name__ == "__main__":
    main()
