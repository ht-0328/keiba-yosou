"""目的変数に対する確率の評価と、その確率で買った場合の回収率。"""

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import (
    FIELD_SIZE, PLACE_ODDS_LOW, PLACE_PAYOUT, POPULARITY, RACE_DATE, RACE_ID, WIN_ODDS, WIN_PAYOUT,
)
from yosou.shared.feature.value_types import as_numbers
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.place_value import PlacePriceEstimator


HISTORICAL_NOTE = (
    "過去の確定人気・確定オッズを使用。木曜・前日・当日の制限は入力項目の制限であり、"
    "過去の発表時刻・購入時点を再現した評価ではありません。"
)
PAYBACK_NOTE = (
    "1点100円で買ったときの回収率（払戻の合計 ÷ 買った金額）。期待値は、勝利なら確率×確定単勝オッズ、"
    "馬券内・馬券外なら3着以内の確率×複勝の想定払戻倍率（確定の最低オッズ×オッズ帯ごとの倍率。倍率は学習期間の払戻から求める）。"
    "3着以内の確率は、全頭がそろったレースでは合計が3（7頭以下は2）になるようにそろえ直す。"
    "下限は、開催日を丸ごと取り直して計算した回収率の90%の幅の下側。"
    "確定オッズは買う時点では分からないので、実際の回収率はこれより下がりうる。"
)
#: 期待値で買うときの下限。検証期間で選び、テスト期間で確かめる。
EXPECTED_VALUE_LINES = (1.0, 1.1, 1.2, 1.3, 1.5, 2.0)
STAKE = 100.0
#: 開催日を取り直す回数と、乱数の種（同じ結果が出るように固定する）。
BOOTSTRAP_ROUNDS = 1000
BOOTSTRAP_SEED = 0
#: 複勝の払戻が3着までの頭数（7頭以下は2着まで）。
FULL_PLACE_FIELD = 8


def scores(labels: pd.Series, probability: np.ndarray) -> dict:
    if len(labels) == 0:
        return {"件数": 0, "正例率": None, "ログ損失": None, "Brier": None, "AUC": None, "注記": "対象なし"}
    both = labels.nunique() == 2
    return {
        "件数": len(labels), "正例率": float(labels.mean()),
        "ログ損失": float(log_loss(labels, probability, labels=[0, 1])),
        "Brier": float(brier_score_loss(labels, probability)),
        "AUC": float(roc_auc_score(labels, probability)) if both else None,
        "注記": "" if both else "正解が1クラスのみのためAUCは計算不能",
    }


def evaluate(ensemble: EnsembleModel, data: TrainingData) -> list[dict]:
    if len(data) == 0:
        return [{"モデル": "平均", "人気": "全体", **scores(data.label, np.array([]))}]
    probabilities = ensemble.predict_members(data)
    probabilities["平均"] = ensemble.combine(probabilities)
    rows = [{"モデル": name, "人気": "全体", **scores(data.label, probability)}
            for name, probability in probabilities.items()]
    popularity = data.evaluation[POPULARITY]
    for rank in sorted(popularity.dropna().unique()):
        mask = popularity.eq(rank).fillna(False)
        rows.append({"モデル": "平均", "人気": str(int(rank)),
                     **scores(data.label[mask], probabilities["平均"][mask.to_numpy(dtype=bool)])})
    if popularity.isna().any():
        mask = popularity.isna()
        rows.append({"モデル": "平均", "人気": "不明", **scores(data.label[mask], probabilities["平均"][mask.to_numpy()])})
    return rows


def place_probability(data: TrainingData, probability: np.ndarray, target: str) -> np.ndarray:
    """3着以内の確率。馬券外モデルは 1−確率。全頭がそろったレースだけ、合計を3（7頭以下は2）にそろえ直す。

    1頭ずつ学習した確率は、同じレースで足しても3にならない。そろえると、同じレースの馬どうしの比が正しくなる。
    人気範囲や馬の条件で一部の馬だけになったレースは、合計の基準が無いのでそのまま使う。
    """
    coming = 1 - probability if target == "馬券外" else probability
    frame = pd.DataFrame({
        "race": data.ids[RACE_ID].to_numpy(), "p": coming,
        "field": as_numbers(data.evaluation[FIELD_SIZE]).to_numpy(),
    })
    grouped = frame.groupby("race", sort=False)
    complete = grouped["p"].transform("size").to_numpy() == frame["field"].to_numpy()
    places = np.where(frame["field"].to_numpy() >= FULL_PLACE_FIELD, 3.0, 2.0)
    scale = places / grouped["p"].transform("sum").to_numpy()
    return np.where(complete, np.clip(coming * scale, 0.0, 1.0), coming)


def expected_values(data: TrainingData, probability: np.ndarray, target: str,
                    place_price: PlacePriceEstimator | None = None) -> np.ndarray:
    """1円あたりの払戻の見込み。オッズの無い馬は欠損値。``place_price`` が無ければ複勝の最低オッズをそのまま使う。"""
    if target == "勝利":
        return probability * as_numbers(data.evaluation[WIN_ODDS]).to_numpy()
    lowest = as_numbers(data.evaluation[PLACE_ODDS_LOW])
    price = lowest.to_numpy() if place_price is None else place_price.estimate(lowest).to_numpy()
    return place_probability(data, probability, target) * price


def bootstrap_lower(days: np.ndarray, payouts: np.ndarray) -> float | None:
    """開催日を丸ごと取り直した回収率の、90%の幅の下側（5%点）。1日しか無ければ None。"""
    frame = pd.DataFrame({"day": days, "payout": payouts}).groupby("day").agg(bets=("payout", "size"), paid=("payout", "sum"))
    if len(frame) < 2:
        return None
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    picks = rng.integers(0, len(frame), size=(BOOTSTRAP_ROUNDS, len(frame)))
    rates = frame["paid"].to_numpy()[picks].sum(axis=1) / (STAKE * frame["bets"].to_numpy()[picks].sum(axis=1))
    return float(np.quantile(rates, 0.05))


def bet_result(data: TrainingData, rows: np.ndarray, name: str) -> dict:
    """``rows``（真偽の配列）の馬を単勝・複勝1点100円ずつ買った結果。"""
    bets = int(rows.sum())
    win = as_numbers(data.evaluation[WIN_PAYOUT]).fillna(0).to_numpy()[rows]
    place = as_numbers(data.evaluation[PLACE_PAYOUT]).fillna(0).to_numpy()[rows]
    races = data.ids[RACE_ID].to_numpy()[rows]
    days = data.ids[RACE_DATE].to_numpy()[rows]
    if bets == 0:
        return {"買い方": name, "点数": 0, "レース数": 0, "単勝的中率": None, "単勝回収率": None, "単勝回収率の下限": None,
                "複勝的中率": None, "複勝回収率": None, "複勝回収率の下限": None}
    return {
        "買い方": name, "点数": bets, "レース数": int(len(set(races))),
        "単勝的中率": float((win > 0).mean()), "単勝回収率": float(win.sum() / (STAKE * bets)),
        "単勝回収率の下限": bootstrap_lower(days, win),
        "複勝的中率": float((place > 0).mean()), "複勝回収率": float(place.sum() / (STAKE * bets)),
        "複勝回収率の下限": bootstrap_lower(days, place),
    }


def top_pick_rows(data: TrainingData, score: np.ndarray) -> np.ndarray:
    """各レースで ``score`` がいちばん高い馬（対象の馬の中で）。"""
    frame = pd.DataFrame({"race": data.ids[RACE_ID].to_numpy(), "score": score})
    rows = np.zeros(len(frame), dtype=bool)
    rows[frame.groupby("race", sort=False)["score"].idxmax().to_numpy()] = True
    return rows


def paybacks(data: TrainingData, probability: np.ndarray, target: str,
             place_price: PlacePriceEstimator | None = None) -> list[dict]:
    """対象の全頭・各レースの確率1位・期待値の下限ごとに買った回収率。馬券外は確率が低いほど「来る」側として扱う。"""
    if len(data) == 0:
        return [bet_result(data, np.zeros(0, dtype=bool), "対象の全頭")]
    coming = 1 - probability if target == "馬券外" else probability
    results = [
        bet_result(data, np.ones(len(data), dtype=bool), "対象の全頭（モデルなし）"),
        bet_result(data, top_pick_rows(data, coming), "各レースで確率1位"),
    ]
    value = expected_values(data, probability, target, place_price)
    for line in EXPECTED_VALUE_LINES:
        results.append(bet_result(data, np.nan_to_num(value, nan=-1.0) >= line, f"期待値{line:g}以上"))
    return results


def fitted_place_price(train: TrainingData) -> PlacePriceEstimator:
    """学習期間の払戻から、複勝の想定払戻倍率の帯ごとの倍率を求める（評価する期間の払戻は使わない）。"""
    return PlacePriceEstimator().fit(train.evaluation[PLACE_ODDS_LOW], train.evaluation[PLACE_PAYOUT])
