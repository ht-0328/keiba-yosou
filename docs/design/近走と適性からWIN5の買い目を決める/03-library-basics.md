# 03 LightGBM と CatBoost（と pandas）の使い方

**この文書の目的:** 設計を読む前に、この予想で使う道具で何ができるかを知っておく。

**この文書で示すこと: この予想は機械学習のモデルを学ばないので、LightGBM と CatBoost は使わない（1着の確率を出す今のモデルの中でだけ使われる。使い方は [手本の 03](../近走と適性から3着以内を予想/03-library-basics.md)）。この予想で使うのは、(1) pandas でレースの中の合計を 1 にそろえる、(2) Python の `itertools` でフォーメーションの組を全部並べる、(3) scikit-learn の `LinearRegression` で配当の見積もりの式を作る、の3つの使い方である。**

pandas の基本（表の作り方・列の型・欠損値）は、手本の 03 に書いてあるので、ここには写さない。

## 1. 手本の 03 のどこに何が書いてあるか

今のモデルの中のことと、pandas の基本を知りたいときに読む。

| 知りたいこと | 手本の節 |
|---|---|
| 入れるパッケージ（`lightgbm`・`catboost`・`scikit-learn`・`pandas`） | [1. 準備](../近走と適性から3着以内を予想/03-library-basics.md#1-準備) |
| 表（`DataFrame`）の作り方、列の型、欠損値、この予想で使う操作 | [2. pandas の使い方](../近走と適性から3着以内を予想/03-library-basics.md#2-pandas-の使い方) |
| 2つのモデルに共通の流れ（モデルを作る → `fit()` → `predict_proba()`）と、`predict()` を使わない理由 | [3. 2つに共通する使い方](../近走と適性から3着以内を予想/03-library-basics.md#3-2つに共通する使い方) |
| LightGBM のコード例と機能（カテゴリ型・早期終了・保存） | [4. LightGBM の使い方](../近走と適性から3着以内を予想/03-library-basics.md#4-lightgbm-の使い方) |
| CatBoost のコード例と機能（`cat_features`・早期終了・保存） | [5. CatBoost の使い方](../近走と適性から3着以内を予想/03-library-basics.md#5-catboost-の使い方) |
| 2つの予測確率の平均のしかた（重みを付けない単純な平均） | [6. 2つの予測確率を合わせる](../近走と適性から3着以内を予想/03-library-basics.md#6-2つの予測確率を合わせる) |

この予想が借りる「1着になる確率」は、今のモデルの1着のモデルの `predict_proba()` の2列目を、LightGBM と CatBoost で平均したものである（[10-target.md の 1.](10-target.md#1-1着の確率今のモデルのものを使う)）。

## 2. レースの中で合計を 1 にそろえる（pandas）

今のモデルは、1頭ずつ別々に確率を出す（二値分類）ので、同じレースの全頭の確率を足しても 1 にならない。組の当たる確率はレースごとの確率のかけ算なので、先にレースの中で合計を 1 にそろえる。

```python
import pandas as pd

horses = pd.DataFrame({
    "レースID": ["A", "A", "A", "B", "B"],     # この例では2レース・5頭。実際は対象レースの全頭
    "馬番": [1, 2, 3, 1, 2],
    "1着の確率": [0.30, 0.20, 0.10, 0.45, 0.35],
})
# 同じレースの確率の合計で割って、レースごとの合計を 1 にする
horses["そろえた確率"] = horses["1着の確率"] / horses.groupby("レースID")["1着の確率"].transform("sum")
print(horses)
```

```text
  レースID  馬番  1着の確率    そろえた確率
0     A   1   0.30  0.500000
1     A   2   0.20  0.333333
2     A   3   0.10  0.166667
3     B   1   0.45  0.562500
4     B   2   0.35  0.437500
```

**`groupby("レースID")[列].transform("sum")` で、各行にそのレースの合計を並べる。**（行の数を変えずに割り算できるようにするため）

| | 値 |
|---|---|
| 変換前（`1着の確率`） | 0.30・0.20・0.10 |
| 変換後（そのレースの合計） | 0.60・0.60・0.60 |

## 3. フォーメーションの組を全部並べる（itertools）

フォーメーションは、レースごとに選んだ馬の全部の組み合わせである。Python に入っている `itertools.product` で全部の組を並べ、組の当たる確率を、5頭のそろえた確率のかけ算で出す。

```python
import itertools
import math

import pandas as pd

legs = {                                 # レースごとに選んだ馬（馬番: そろえた1着の確率）。この例では 2×1×3×1×2 = 12点
    "1R目": {3: 0.40, 7: 0.25},
    "2R目": {5: 0.50},
    "3R目": {1: 0.30, 2: 0.20, 9: 0.10},
    "4R目": {4: 0.35},
    "5R目": {6: 0.45, 8: 0.20},
}
combos = []
for picks in itertools.product(*[leg.items() for leg in legs.values()]):
    numbers = tuple(number for number, _ in picks)
    probability = math.prod(p for _, p in picks)     # 5つのレースは別々に決まるとみなして、かけ算する
    combos.append({"組": numbers, "当たる確率": probability})
table = pd.DataFrame(combos)
print(len(table), "点")
print(table.sort_values("当たる確率", ascending=False).head(3))
print("どれかが当たる確率", round(table["当たる確率"].sum(), 4))
```

```text
12 点
                 組     当たる確率
0  (3, 5, 1, 4, 6)  0.009450
2  (3, 5, 2, 4, 6)  0.006300
6  (7, 5, 1, 4, 6)  0.005906
どれかが当たる確率 0.0444
```

- 当たる組は1つだけなので、買い目のどれかが当たる確率は、組の確率の合計になる（同着のときを除く）。
- 実際に使う予算（数百点まで）なら、組を全部並べても数秒で済む。

## 4. 配当の見積もりの式を作る（scikit-learn の LinearRegression）

過去の WIN5 の当たり組について、払戻の対数を、市場の組の確率の逆数の対数と、キャリーオーバーの比の対数から当てる1次式を作る（式の中身は [10-target.md の 2.](10-target.md#2-配当の見積もりで当てるもの)）。手本で入れてある scikit-learn の `LinearRegression` を使う。

```python
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

rng = np.random.default_rng(0)                   # この例は乱数の架空データ 300回分。実際は元DB の過去の WIN5
n = 300
inv_q = np.exp(rng.uniform(3, 14, n))            # 市場の組の確率の逆数
carry = rng.choice([0.0, 0.0, 0.0, 0.5], n)      # キャリーオーバー ÷ 払戻に回るお金
log_pay = 4.0 + 0.95 * np.log(inv_q) + 0.9 * np.log1p(carry) + rng.normal(0, 0.6, n)

X = pd.DataFrame({"log_逆数": np.log(inv_q), "log_キャリー": np.log1p(carry)})
model = LinearRegression().fit(X, log_pay)       # 1. 式を作る（傾きと切片を決める）
print("傾き", model.coef_.round(3), "切片", round(model.intercept_, 3))

new = pd.DataFrame({"log_逆数": [np.log(5000.0)], "log_キャリー": [0.0]})
smear = np.mean(np.exp(log_pay - model.predict(X)))   # 2. 対数から戻すときの補正（外れの散らばりの分）
print("見積もりの配当", round(float(np.exp(model.predict(new))[0] * smear)))
```

```text
傾き [0.958 0.681] 切片 3.934
見積もりの配当 210746
```

**対数で当てた値を元に戻すときは、外れ（実際 − 式）の散らばりの分を掛ける。**（対数の平均を戻しただけでは、配当の平均より小さく出るため）

| | 値 |
|---|---|
| 補正なし | `exp(式の値)`。配当の「真ん中あたり」 |
| 補正あり | `exp(式の値) × mean(exp(外れ))`。配当の「平均」。期待値にはこちらを使う |

## 5. この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 対象レースの1着の確率を出す | 今のモデルの予測の流れを呼ぶ（LightGBM・CatBoost はその中で使われる） | [05-sequence.md の図2](05-sequence.md#図2-win5-の日の予測) |
| レースの中で合計を 1 にそろえる | `groupby().transform("sum")` | [16-evaluation.md の 3.](16-evaluation.md#3-組の当たる確率と期待値) |
| フォーメーションの組を並べる | `itertools.product`・`math.prod` | [06-flowchart.md の図3](06-flowchart.md#図3-買い目の組み方と買う日の判断) |
| 配当の見積もりの式を作る・使う | `LinearRegression` の `fit()`・`predict()` | [10-target.md の 2.](10-target.md#2-配当の見積もりで当てるもの)、[05-sequence.md の図1](05-sequence.md#図1-配当の見積もりの式を作る) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-08 |
| 確かめた版 | 2〜4 のコードは、作業フォルダの Python で動かして確かめた（pandas 3.0.6、scikit-learn 1.9.1、numpy 2.5.3） |
