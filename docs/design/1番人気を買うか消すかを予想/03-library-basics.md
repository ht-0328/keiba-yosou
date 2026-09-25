# 03 StandardScaler と NearestNeighbors（と pandas）の使い方

**この文書の目的:** 設計を読む前に、この予想で使う scikit-learn の2つの道具（`StandardScaler`・`NearestNeighbors`）と、表を扱う pandas で何ができるかを知っておく。この文書は決めごとではなく、道具の説明である。

**結論: `StandardScaler` は「`fit()` で列ごとの平均と標準偏差を覚える → `transform()` で尺度をそろえる」、`NearestNeighbors` は「`fit()` でグループの馬を覚える → `kneighbors()` で似た k頭と、その距離を返す」の手順で使える。** この予想では、そのうえで、似た k頭との平均距離を「同じ単位の1番人気全員」の距離と比べて、近さの点数にする。

- この予想での使い方（列の作り方・点数の出し方）は [12-neighbor-distance.md](12-neighbor-distance.md)・[13-closeness-score.md](13-closeness-score.md) を参照。
- 用語の意味（k近傍法・距離・標準化・百分位など）は [02-glossary.md](02-glossary.md) を参照。
- コードは、scikit-learn 1.9.1・pandas 3.0.6・numpy 2.5.3 で、乱数で作った架空の馬のデータを使って動くことを確かめた（2026-09-25）。出力の数字も、その架空のデータのものである。

## 1. 準備

| パッケージ | 何に使うか | 依存にあるか |
|---|---|---|
| `scikit-learn` | `StandardScaler` と `NearestNeighbors` | ある（ほかの予想の LightGBM のために入れてある） |
| `pandas` | 学習データを表（`DataFrame`）で扱う | ある |

新しいパッケージは足していない。この予想では `lightgbm` と `catboost` を使わない（[01-overview.md](01-overview.md)）。

## 2. pandas の使い方

表の作り方、列の型、欠損値（`NaN`）の扱いは、手本と同じである。[手本の 03 の「2. pandas の使い方」](../近走と適性から3着以内を予想/03-library-basics.md#2-pandas-の使い方) を参照。この予想で足して使う操作は次の2つである。

| やりたいこと | 書き方 | 結果 |
|---|---|---|
| 欠損値を中央値で埋める | `X.fillna(X.median())` | 列ごとに、欠損値がその列の中央値になる |
| 種類の列を 0/1 の列に分ける（ワンホットエンコーディング） | `(X["馬場状態"] == "良").astype(float)` を種類ごとに作る | 「馬場状態=良」「馬場状態=稍重」…の 0/1 の列ができる |

## 3. StandardScaler の使い方

k近傍法の距離は、列ごとの差を足し合わせる。単勝オッズ（1〜5 くらい）と馬体重（400〜550 くらい）をそのまま足すと、数の大きい馬体重ばかりが距離を決めてしまう。そこで、列ごとに平均 0・ばらつき 1 にそろえる（標準化）。

| 手順 | コード | 何が起きるか |
|---|---|---|
| 1. 物差しを作る | `scaler = StandardScaler().fit(X)` | 列ごとの平均と標準偏差を覚える |
| 2. そろえる | `scaler.transform(X_new)` | 覚えた平均を引き、標準偏差で割る。学習データと同じ物差しで、予測したい馬もそろえる |

| | 変換前 | 変換後 |
|---|---|---|
| 単勝オッズ | 1.8, 2.4, 3.6 | −1.07, −0.27, 1.34 |

実装（`FeatureMatrix`）は、同じ計算（平均を引いて標準偏差で割る）を pandas で書いている。0/1 の列を標準化しないなど、列ごとに扱いを変えるためである（[12-neighbor-distance.md の「3.」](12-neighbor-distance.md#3-尺度をそろえる標準化)）。

## 4. NearestNeighbors の使い方

| 手順 | コード | 何が起きるか |
|---|---|---|
| 1. 覚える | `nn = NearestNeighbors(n_neighbors=k).fit(グループの馬)` | グループの馬の、そろえた特徴量を覚える。これが「そのグループの馬だけで作るモデル」になる |
| 2. 似た馬を探す | `distances, rows = nn.kneighbors(X_new)` | 対象の馬1頭ずつに、いちばん似た k頭の距離（小さい順）と、その行の番号を返す |

- **グループの馬自身を `kneighbors()` に渡すと、いちばん似ているのは自分自身（距離 0）になる。** そこで、グループの馬について距離を出すときは `n_neighbors=k + 1` で探し、1列目（自分）を捨てる。
- 距離の測り方の既定は、ユークリッド距離である。

## 5. 動かして確かめた最小のコード

架空の1番人気 300頭（1つの単位の学習データのつもり）で、3つのグループのモデルを作り、対象の馬の点数を出して判定するまでを動かした。点数のそろえ方と判定の線は、実装（`GroupSimilarity`・`BuyDecision`）と同じである。

```python
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

rng = np.random.default_rng(0)

# 架空の1番人気 300頭（1つの単位の学習データのつもり）。本番は 70個ほどの特徴量から作る
n = 300
horses = pd.DataFrame({
    "単勝オッズ": rng.uniform(1.3, 4.5, n).round(1),
    "前走の人気": rng.integers(1, 8, n).astype(float),
    "前走の着順": rng.integers(1, 10, n).astype(float),
})
horses.loc[rng.random(n) < 0.1, "前走の着順"] = np.nan          # 前走が無い馬（新馬戦など）
finish = rng.integers(1, 12, n)                                   # 確定着順（架空）

# 1. 欠損値を中央値で埋め、尺度をそろえる。物差しは、3つのグループを合わせた単位の全頭で作る
filled = horses.fillna(horses.median())
scaler = StandardScaler().fit(filled)
matrix = scaler.transform(filled)

# 2. グループごとに、そのグループの馬だけを覚える。比べる相手（単位の1番人気全員）の距離も出しておく
k = 10
groups = {"勝利": finish == 1, "馬券内": finish <= 3, "馬券外": finish >= 4}
fitted = {}
for name, is_member in groups.items():
    nn = NearestNeighbors(n_neighbors=k + 1).fit(matrix[is_member])
    distances, _ = nn.kneighbors(matrix)                  # 単位の全頭について、そのグループの似た馬との距離
    own = distances[:, 1:].mean(axis=1)                   # グループの馬は、いちばん近いのが自分なので除く
    other = distances[:, :k].mean(axis=1)                 # グループの外の馬は、近い k頭をそのまま使う
    reference = np.sort(np.where(is_member, own, other))  # 単位の1番人気全員の距離の並び
    fitted[name] = (nn, reference)
    print(name, "の頭数", is_member.sum())

# 3. 対象の馬（学習データに無い馬）の点数 = 単位の1番人気のうち、対象の馬と同じか、より遠い馬の割合（%）
target = pd.DataFrame({"単勝オッズ": [2.4], "前走の人気": [1.0], "前走の着順": [3.0]})
x = scaler.transform(target)
scores = {}
for name, (nn, reference) in fitted.items():
    d = nn.kneighbors(x, n_neighbors=k)[0].mean()
    nearer = np.searchsorted(reference, d, side="left")   # 対象の馬より近い馬の数
    scores[name] = 100 * (len(reference) - nearer) / len(reference)
print({name: round(float(score), 1) for name, score in scores.items()})

# 4. 判定: 馬券外が馬券内より 5点を超えて高ければ消す → 勝利が馬券内より高ければ単勝と複勝 → そうでなければ複勝だけ
fade_margin, win_margin = 5.0, 0.0
if scores["馬券外"] - scores["馬券内"] > fade_margin:
    print("消す")
elif scores["勝利"] - scores["馬券内"] > win_margin:
    print("単勝と複勝")
else:
    print("複勝だけ")
```

出力（乱数の架空データのもの）:

```text
勝利 の頭数 30
馬券内 の頭数 81
馬券外 の頭数 219
{'勝利': 31.7, '馬券内': 30.3, '馬券外': 26.0}
単勝と複勝
```

- 例のために、特徴量を3つに絞り、着順を乱数で付けた（そのため勝利の頭数が本物の1番人気より少ない）。本番の1単位は数百〜数千頭で、特徴量は 70個ほど使う（[08-training-data.md](08-training-data.md)・[12-neighbor-distance.md](12-neighbor-distance.md)）。
- 3. の「対象の馬」はグループの外の馬なので、自分を除く必要は無い（`n_neighbors=k`）。
- 例では、この架空の馬は3つのグループのどれにも、単位の1番人気の中では遠いほう（点数 30 前後）である。勝利が馬券内をわずかに上回ったので「単勝と複勝」になった。

## 6. この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 距離に使う数字の表にする | 欠損値の埋め・0/1 の列・標準化 | [12-neighbor-distance.md の「1.」〜「4.」](12-neighbor-distance.md#1-距離に使う列の作り方) |
| グループの馬を覚え、似た k頭を探す | `NearestNeighbors`・`kneighbors` | [12-neighbor-distance.md の「5.」](12-neighbor-distance.md#5-k近傍で似た馬を探す) |
| 距離を点数にそろえる | 単位の1番人気全員の距離の並びと、`np.searchsorted` | [13-closeness-score.md の「2.」](13-closeness-score.md#2-点数のそろえ方) |
| 学習したものを、レース当日まで取っておく | `pickle` | [12-neighbor-distance.md の「6.」](12-neighbor-distance.md#6-保存) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-25 |
| 更新 | 2026-09-25: LightGBM・CatBoost の説明から、k近傍法の道具の入門に作り直した。同日、点数のそろえ方を実装と同じにして、確かめ直した |
| 確かめた版 | scikit-learn 1.9.1、pandas 3.0.6、numpy 2.5.3（乱数で作った架空のデータ） |
