"""材料の候補が、今の予想の確率に足りない情報を持っているかを、まとめて確かめる（段2のふるい）。

    uv run python research/重賞の事例から材料を作る/screen.py    # reports/重賞の事例から材料を作る/ふるい.md に書く

今の予想の確率（3着以内・1着）を出発点（init_score = ロジット）にして、候補の材料だけで小さな LightGBM を学び、確率を直す。
1年を抜いて残りの年で学び、抜いた年の重賞の行でログ損失を測る（当日の予想のある 2020〜2026年。前日の予想で 2015〜2026年も）。
比べる相手として、候補の値を年の中でかき混ぜた材料でも同じことをする（偶然でどれだけ良くなるか）。
候補を1つずつ抜いたときの悪くなり方も出す（どの候補が効いているか）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import lightgbm
import numpy as np
import pandas as pd
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))

from candidates import CANDIDATES  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
_OUT = _ROOT / "reports" / "重賞の事例から材料を作る"
_PREDICTIONS = _ROOT / "reports" / "既存モデルの改善" / "predictions" / "graded_race_day"
#: （名前, 予測のファイル（複数なら年で分けてつなぐ）, 目的）
_SETS = (
    ("当日の3着以内（2020〜2026年）", ("general-top3",), "top3"),
    ("当日の1着（2020〜2026年）", ("general-win",), "win"),
    ("前日の3着以内（2015〜2026年）", ("dayb-top3-early", "dayb-top3"), "top3"),
    ("前日の1着（2015〜2026年）", ("dayb-win-early", "dayb-win"), "win"),
)
_PARAMS = dict(objective="binary", learning_rate=0.02, num_leaves=7, min_child_samples=200, subsample=0.8, subsample_freq=1,
               colsample_bytree=0.8, reg_lambda=5.0, n_estimators=300, verbose=-1, n_jobs=4)
_EPS = 1e-6
#: 直線の直し方の罰の強さ（標準化した材料の重みの2乗の和に掛ける。行数で割った損失に足す）。
_PENALTIES = (0.001, 0.01, 0.1)


def main() -> None:
    candidates = pd.read_parquet(_OUT / "候補.parquet")
    facts = pd.read_parquet(_OUT / "facts.parquet", columns=["race_id", "horse_id", "finish", "ran"])
    facts = facts[facts["ran"]]
    lines = ["# 材料の候補のふるい（重賞の行）", "",
             "直す前 = 今の予想の確率のログ損失。直した後 = 候補で直した確率（その年を抜いて学んだもの）。小さいほど良い。",
             "かき混ぜ = 候補の値を年の中でかき混ぜて同じことをしたもの（偶然でどれだけ動くか）。", ""]
    for name, keys, target in _SETS:
        rows = _rows(candidates, facts, keys, target)
        lines += _section(name, rows)
        lines += _linear_section(name, rows)
    out = _OUT / "ふるい.md"
    out.write_bytes("\n".join(lines).encode("utf-8"))
    print("\n".join(lines))


def _rows(candidates: pd.DataFrame, facts: pd.DataFrame, keys: tuple[str, ...], target: str) -> pd.DataFrame:
    frames = []
    for key in keys:
        frame = pd.read_pickle(_PREDICTIONS / f"{key}.pkl")
        frame = frame[frame["期間"].eq("テスト")]
        frames.append(pd.DataFrame({"race_id": frame["レースID"].astype(str), "horse_id": frame["馬ID"].astype(str), "p": frame["確率"].to_numpy()}))
    prediction = pd.concat(frames).drop_duplicates(["race_id", "horse_id"], keep="last")
    rows = candidates.merge(prediction, on=["race_id", "horse_id"]).merge(facts[["race_id", "horse_id", "finish"]], on=["race_id", "horse_id"])
    rows = rows.dropna(subset=["finish"])
    rows["y"] = (rows["finish"].astype(float) <= (3 if target == "top3" else 1)).astype(float)
    return rows.reset_index(drop=True)


def _section(name: str, rows: pd.DataFrame) -> list[str]:
    real = _corrected(rows, list(CANDIDATES))
    shuffled = _corrected(_shuffle(rows), list(CANDIDATES))
    lines = [f"## {name}", "", f"重賞の行 {len(rows):,}。", "",
             "| 年 | 直す前 | 直した後 | かき混ぜ | 良くなったか |", "|---|---|---|---|---|"]
    years = sorted(rows["year"].unique())
    better = 0
    for year in years:
        mask = rows["year"].eq(year).to_numpy()
        before, after, noise = (_loss(rows["y"][mask], values[mask]) for values in (rows["p"].to_numpy(), real, shuffled))
        better += after < before
        lines.append(f"| {year} | {before:.5f} | {after:.5f} | {noise:.5f} | {'○' if after < before else '×'} |")
    total = [_loss(rows["y"], values) for values in (rows["p"].to_numpy(), real, shuffled)]
    lines += [f"| 全体 | {total[0]:.5f} | {total[1]:.5f} | {total[2]:.5f} | {better}/{len(years)} |", ""]
    lines += ["候補を1つずつ抜いたときの、直した後の全体のログ損失の増え方（大きいほどその候補が効いている）:", ""]
    drops = []
    for column in CANDIDATES:
        without = _corrected(rows, [c for c in CANDIDATES if c != column])
        drops.append((column, _loss(rows["y"], without) - total[1]))
    lines += [f"- {column}: {delta * 1e5:+.1f}（×10⁻⁵）" for column, delta in sorted(drops, key=lambda item: -item[1])]
    return lines + [""]


def _corrected(rows: pd.DataFrame, columns: list[str]) -> np.ndarray:
    """1年ずつ抜いて学び、抜いた年の直した確率を返す。"""
    logit = _logit(rows["p"].to_numpy())
    out = np.empty(len(rows))
    for year in rows["year"].unique():
        test = rows["year"].eq(year).to_numpy()
        model = lightgbm.LGBMClassifier(**_PARAMS)
        model.fit(rows.loc[~test, columns], rows.loc[~test, "y"], init_score=logit[~test])
        raw = model.predict(rows.loc[test, columns], raw_score=True) + logit[test]
        out[test] = 1.0 / (1.0 + np.exp(-raw))
    return out


def _linear_section(name: str, rows: pd.DataFrame) -> list[str]:
    """直線の直し方（ずらしのロジスティック回帰に重みの罰）で、罰の強さごとに全体と年ごとの勝ち数を出す。"""
    lines = [f"### {name}: 直線の直し方", "", "| 罰の強さ | 直す前 | 直した後 | かき混ぜ | 良くなった年 |", "|---|---|---|---|---|"]
    before = _loss(rows["y"], rows["p"])
    shuffled = _shuffle(rows)
    for penalty in _PENALTIES:
        real, noise = _linear(rows, penalty), _linear(shuffled, penalty)
        years = sorted(rows["year"].unique())
        better = sum(_loss(rows["y"][m], real[m]) < _loss(rows["y"][m], rows["p"][m])
                     for m in (rows["year"].eq(y).to_numpy() for y in years))
        lines.append(f"| {penalty} | {before:.5f} | {_loss(rows['y'], real):.5f} | {_loss(rows['y'], noise):.5f} | {better}/{len(years)} |")
    return lines + [""]


def _linear(rows: pd.DataFrame, penalty: float) -> np.ndarray:
    logit = _logit(rows["p"].to_numpy())
    y = rows["y"].to_numpy()
    out = np.empty(len(rows))
    for year in rows["year"].unique():
        test = rows["year"].eq(year).to_numpy()
        x_train, x_test = _design(rows.loc[~test, list(CANDIDATES)], rows.loc[test, list(CANDIDATES)])
        w = _fit_offset(x_train, y[~test], logit[~test], penalty)
        out[test] = 1.0 / (1.0 + np.exp(-(logit[test] + x_test @ w[1:] + w[0])))
    return out


def _design(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """学びの年で標準化し、欠損は 0（平均）にして、欠損かどうかの列を足す。"""
    mean, std = train.mean(), train.std().replace(0, 1).fillna(1)
    def build(frame: pd.DataFrame) -> np.ndarray:
        scaled = ((frame - mean) / std).clip(-5, 5)
        missing = frame.isna().astype(float).loc[:, train.isna().any()]
        return np.hstack([scaled.fillna(0).to_numpy(), missing.to_numpy()])
    return build(train), build(test)


def _fit_offset(x: np.ndarray, y: np.ndarray, offset: np.ndarray, penalty: float) -> np.ndarray:
    def loss(w):
        z = offset + w[0] + x @ w[1:]
        p = 1.0 / (1.0 + np.exp(-z))
        value = -np.mean(y * np.log(np.clip(p, _EPS, 1)) + (1 - y) * np.log(np.clip(1 - p, _EPS, 1))) + penalty * np.sum(w[1:] ** 2)
        grad = np.concatenate([[np.mean(p - y)], x.T @ (p - y) / len(y) + 2 * penalty * w[1:]])
        return value, grad
    return minimize(loss, np.zeros(x.shape[1] + 1), jac=True, method="L-BFGS-B").x


def _shuffle(rows: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    shuffled = rows.copy()
    for year, index in rows.groupby("year").groups.items():
        order = rng.permutation(len(index))
        shuffled.loc[index, list(CANDIDATES)] = rows.loc[index, list(CANDIDATES)].to_numpy()[order]
    return shuffled


def _logit(p: np.ndarray) -> np.ndarray:
    clipped = np.clip(p, _EPS, 1 - _EPS)
    return np.log(clipped / (1 - clipped))


def _loss(y, p) -> float:
    actual, prob = np.asarray(y, dtype=float), np.clip(np.asarray(p, dtype=float), _EPS, 1 - _EPS)
    return float(-np.mean(actual * np.log(prob) + (1 - actual) * np.log(1 - prob)))


if __name__ == "__main__":
    sys.exit(main())
