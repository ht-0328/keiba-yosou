# 14 方針を外から指定する

**この文書で決めること:** 単位のまとめ方・特徴量の時点・k・判定の線・掛け金・評価の年などの方針を、プログラムを書き換えずに外から指定する方法。

**結論: 方針は設定ファイル（TOML 形式）にまとめた。初期値は `src/yosou/favorite_buy_or_fade/setting/default_settings.toml` にあり、`train` と `evaluate` に `--config` で別のファイルを渡すと、そのファイルに書いた項目だけが置き換わる。方針を変えたら、`evaluate`（1年ごとの評価）か `train`（本番用のモデル）を実行し直すだけで反映される。1回あたり1分ほどで終わる。** 指定のしかたの決まり（書き間違いはエラー、使った方針を一緒に保存する）は手本と同じ考え方である（[手本の 14 の「決まり」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#決まり)）。

用語の意味は [02-glossary.md](02-glossary.md) を参照。

## 設定ファイルの形

初期値のファイルの中身は、次のとおりである（実装のファイルそのまま）。値を決めた理由は [15-decisions.md](15-decisions.md) を参照。

```toml
# 1番人気を買うか消すかの予想の、方針の初期値（設計書 14・15）。
# train・evaluate・predict に --config で別のファイルを渡すと、そのファイルに書いた項目だけが置き換わる。
# ここに無い名前は書けない（書き間違いを黙って無視しないため）。
# 方針を変えたら、train（本番用のモデル）か evaluate（1年ごとの評価）を実行し直すだけで反映される。

[unit]
# 学習データでの1番人気がこれより少ない「芝ダート × 距離」は、同じ芝ダートのいちばん近い距離の単位とまとめる。
min_rows = 500

[features]
# どの時点の特徴量で近さを測るか（前日 か 当日）。前日なら、馬体重（当日に分かる）を使わない。
timing = "当日"
# 近さの計算に使わない特徴量。騎手・調教師・血統の名前は距離を測れないので、強さは数字の列
# （騎手・調教師の近1年の3着以内の割合、父・母の父の産駒の3着以内の割合）で渡す。
# 人気順位はどの行も 1 なので使わない。
exclude = ["騎手", "調教師", "父", "父の父", "母の父", "人気順位"]
# 数の特徴量が欠損値だった行を、0 と 1 の列（欠損値だったか）でも表すか。欠損値は単位の中央値で埋める。
add_missing_flags = true

[features.group_weights]
# まとまりごとの重み。標準化したあとの値に掛ける。大きいほど、そのまとまりの違いが近さに効く。0 なら使わない。
A = 1.0   # レースの条件
B = 1.0   # 馬のこと
C = 1.0   # 騎手と調教師
D = 1.0   # 前走（前走の人気を含む）
E = 1.0   # 近走のまとめ
F = 1.0   # この条件での経験
G = 1.0   # 同じレースの馬との比較
H = 1.0   # 血統
I = 1.0   # 調教
J = 1.0   # 人気の履歴（前走の人気と着順の差など。過去のレースの人気なので、今回のオッズではない）
K = 0.0   # 単勝オッズから見た評価。オッズなしで予想するため使わない（1 にすると、今回の単勝オッズも近さに入る）

[similarity]
# 近さを測るときに見る、そのグループの中で似ている馬の頭数（k近傍法の k）。
k = 10

[decision]
# 馬券外の近さの点数が、馬券内の点数よりこの点数を超えて高ければ消す。0 なら「少しでも馬券外に近ければ消す」で、
# 1番人気のおよそ半分を消すことになるので、はっきり馬券外に近い馬だけを消すよう 5 にしている。
fade_margin = 5.0
# 勝利の近さの点数が、馬券内の点数よりこの点数を超えて高ければ、単勝と複勝を買う。そうでなければ複勝だけ。
win_margin = 0.0

[stake]
# 1頭あたりの掛け金（円）。「単勝と複勝」と「複勝だけ」の合計を同じにして、単勝を足したかどうかだけで比べる。
win_and_place_win = 100
win_and_place_place = 200
place_only_place = 300

[evaluation]
# 1年ごとの評価（evaluate）。評価する年ごとに、学習の最初の年からその前年までで学習し直す。
train_first_year = 2017
first_year = 2019
last_year = 2026
```

| 表 | 何を決めるか | 書いてある文書 |
|---|---|---|
| `[unit]` | 単位にする距離の、1番人気の頭数の下限（`min_rows`） | [08-training-data.md の「単位の決め方」](08-training-data.md#単位の決め方) |
| `[features]` | 特徴量の時点（`timing`）、距離に使わない特徴量（`exclude`）、欠損値だったかの列を足すか（`add_missing_flags`） | [07-prediction-timing.md](07-prediction-timing.md)、[12-neighbor-distance.md の「1.」・「2.」](12-neighbor-distance.md#1-距離に使う列の作り方) |
| `[features.group_weights]` | まとまり A〜K の重み | [12-neighbor-distance.md の「4.」](12-neighbor-distance.md#4-特徴量の重み) |
| `[similarity]` | 似た馬を何頭探すか（`k`） | [12-neighbor-distance.md の「5.」](12-neighbor-distance.md#5-k近傍で似た馬を探す) |
| `[decision]` | 判定の線（`fade_margin`・`win_margin`） | [13-closeness-score.md の「4.」](13-closeness-score.md#4-判定) |
| `[stake]` | 判定ごとの掛け金（円） | [16-evaluation.md の「4.」](16-evaluation.md#4-買い方と掛け金) |
| `[evaluation]` | 学習の最初の年（`train_first_year`）と、評価する年の範囲（`first_year`〜`last_year`） | [16-evaluation.md の「1.」](16-evaluation.md#1-1年ごとの評価ウォークフォワード) |

## 方針の変え方

変えたい項目だけを書いたファイルを作り、`--config` で渡す。書かなかった項目は初期値のままになる。

```toml
[decision]
fade_margin = 10.0

[features.group_weights]
K = 1.0
```

```powershell
uv run python -m yosou.favorite_buy_or_fade evaluate --config reports/favorite_buy_or_fade/settings/with-odds.toml --out reports/favorite_buy_or_fade/evaluation-with-odds.md
uv run python -m yosou.favorite_buy_or_fade train --config reports/favorite_buy_or_fade/settings/with-odds.toml
```

（1行目は、消しの線を 10点にし、単勝オッズから見た評価（K）も近さに使う方針で、1年ごとの評価をやり直すコマンド。2行目は、同じ方針で本番用のモデルを作り直すコマンド。初期値はオッズなしで予想する（K = 0.0）ので、オッズも使うときは、このように K = 1.0 などにする）

## 決まり

| 決まり | 理由 |
|---|---|
| `--config` は `train` と `evaluate` で渡す。`predict` は、`train` で保存した方針（時点・判定の線など）をそのまま使う | 予測のときに、学習したときと違う時点や線で判定すると、点数の物差しと合わなくなる |
| 初期値のファイルに無い名前を書いたらエラーにする（共通の `SettingsNameCheck`） | 書き間違いを黙って無視すると、変えたつもりの方針が効いていないことに気づけない |
| `timing` に木曜を書いたらエラーにする | 木曜は、誰が1番人気かが分からない（[07-prediction-timing.md](07-prediction-timing.md)） |
| `k` と `min_rows` は 1 以上。評価の年は `train_first_year` < `first_year` ≦ `last_year` | 意味の無い値で作ると、点数や評価が壊れる |
| 使った方針を、モデルの一式と一緒に保存する（`settings.json`。[12-neighbor-distance.md の「6.」](12-neighbor-distance.md#6-保存)） | あとで、どの方針で作ったかを確かめられる |
| 1つの方針を、全部の単位・グループに使う | 単位ごとに変える仕組みは、評価を見て要るとなったときに足す |

設定ファイルを読む部品（ファイルを読む `SettingsFile`・名前を確かめる `SettingsNameCheck`・初期値に重ねる `SettingsOverlay`）は共通のものを使い、この予想の `BuyOrFadeSettings` がそれを組み立てる（[04-classes.md](04-classes.md#setting--方針)）。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-25 |
| 更新 | 2026-09-25: LightGBM・CatBoost のハイパーパラメータから、k近傍法の設定に作り直した。同日、実装の設定ファイル（`default_settings.toml`）に合わせて書き直した |
