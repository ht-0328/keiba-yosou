# 04 クラスとパッケージの設計

**この文書で決めること:** この予想だけに要るクラスは何か。共通の部品（`src/yosou/shared/`）のうち何を使うか。どのクラスが流れを進める（オーケストレーションする）か。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: 学習は `SimilarityTraining`、1年ごとの評価は `YearlyEvaluation`、予測は `PredictionWorkflow` が流れを進める。** 学習データと予測用データ（特徴量 78個）は、共通の `DatasetBuilder` でほかの予想と同じように作る。この予想だけに作ったのは、1番人気の行を選ぶ・グループを付ける・単位を決める・距離に使う行列にする・グループごとの近さのモデル・判定・掛け金と成績の表・モデルの保存・方針の読み込み、の仕事のクラスである。**共通の部品には手を加えていない。** LightGBM・CatBoost の部品（`ml_model/`・`SegmentedTraining`・`TrainingWorkflow`・`ModelRepository` など）は使わない。

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、if 文・for 文の入れ子は1段まで、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 用語の意味（public メソッド・オーケストレーション・リポジトリ）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. 共通の部品の使い方

| 共通の部品 | この予想での使い方 |
|---|---|
| `DatasetBuilder` | 1番人気の行の選び方（`FavoriteOnlySelector`）・グループの列（`FinishGroupLabeler`）・特徴量の一覧（`CATALOG`）を渡して、学習データと予測用データを作る |
| 特徴量のまとまり A〜I と、J（`PopularityHistoryFeatures`）・K（`OddsFeatures`） | 特徴量を作る。一覧は [09-features.md](09-features.md) |
| `TrainingData`（`for_timing`・`between`・`where`） | 方針の時点の列にする・年で区切る・単位の行を選ぶ |
| `OddsResolver`・`PopularityApplier`・`OddsInput`・`PopularityInput` | 予測に使う単勝オッズと人気を決める（[07-prediction-timing.md](07-prediction-timing.md#予測のときの1番人気の決め方)） |
| `SettingsFile`・`SettingsNameCheck`・`SettingsOverlay` | 設定ファイル（TOML）を読み、書き間違いを確かめ、初期値に重ねる（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `CommonArguments` | コマンドに共通の引数（`--models` `--db` `--format` `--out`） |

## 2. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。パッケージ名は、予想のやり方が分かる `favorite_buy_or_fade`（favorite = 1番人気、buy or fade = 買うか消すか）とした。

```text
src/yosou/favorite_buy_or_fade/     1番人気を買うか消すかを予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・evaluate・predict）の引数。入口
├── workflow/                       学習・1年ごとの評価・予測の流れ（ほかを順に呼ぶだけ）
├── evaluation/                     掛け金と、年ごと・判定ごと・単位ごとの成績の表
├── decision/                       3つの点数から判定する
├── similarity/                     近さのモデル（特徴量の行列・グループごとの近さ・単位ごとの一式）
├── unit/                           芝ダート × 距離の単位の決め方
├── dataset/                        1番人気の行の選び方・グループの列と、共通の DatasetBuilder の組み立て
├── feature/                        この予想の特徴量の一覧（CATALOG）
├── setting/                        方針の初期値のファイルと、それを読むクラス
├── repository/                     学習したモデルの一式の読み書き
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダの `__init__.py` の先頭に「クラス → 仕事」の表を書いた。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`FavoriteOnlySelector` → `favorite_only_selector.py`）。学習したモデルの一式は、Git の対象外の `reports/favorite_buy_or_fade/models/` に保存する。フォルダ名を `model` にしない決まり（[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり)）に合わせ、近さのモデルのフォルダは `similarity` とした。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `favorite_buy_or_fade` → `shared`。`shared` から予想のパッケージを参照しない。ほかの予想のパッケージも参照しない | 片方の予想の都合が、もう片方に入り込まない |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `evaluation`・`decision` → `similarity` → `unit`・`dataset` → `feature`。`setting` と `repository` は、それを使うところから参照する | 参照が循環すると、1つを直すと全部に響く |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |

## 3. この予想だけのクラスの一覧

### dataset/ — 行を選ぶ・グループを付ける

| 名前 | 仕事 | 主な public メソッド |
|---|---|---|
| `FavoriteOnlySelector` | 確定単勝人気が 1 の行だけを残す。特徴量はレースの全頭で作ってから絞る（[06-flowchart.md](06-flowchart.md#図1-学習データに入れる行の選び方)）。共通の `SampleSelector` を守る | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` |
| `FinishGroupLabeler` | グループの列（勝利・馬券内・馬券外。どれも 1/0）を付ける。競走中止・失格は馬券外（[10-target.md](10-target.md#グループの分け方)）。共通の `TargetLabeler` を守る | `build(サンプルの行)`、`label_name` |
| `dataset_builder()` | 上の2つと特徴量の一覧を渡して、共通の `DatasetBuilder` を組み立てる関数（`dataset_assembly.py`） | `dataset_builder(接続)` |
| `column_names.py` の `GROUPS` | 3つのグループの名前（勝利・馬券内・馬券外） | ―（値） |

### feature/ — 特徴量の一覧

| 名前 | 中身 |
|---|---|
| `CATALOG` | この予想の特徴量 78個の一覧。共通の `BASE_FEATURES`（A〜I）＋ `POPULARITY_FEATURES`（J）＋ `ODDS_FEATURES`（K）で、`favorites_out_of_top3` と同じ（[09-features.md](09-features.md)） |

### unit/ — 単位を決める

| 名前 | 仕事 | 主な public メソッド |
|---|---|---|
| `CourseUnitMap` | 芝ダ → 単位にする距離の並びを持つ。学習データで1番人気が `min_rows` 頭以上いる距離を単位にし、少ない距離は同じ芝ダのいちばん近い単位にまとめる（差が同じなら長いほう）。その芝ダにどれも足りなければ、いちばん頭数の多い距離1つにまとめる（[06-flowchart.md](06-flowchart.md#図3-使う単位を決める)）。単位の名前は「芝2000m」の形 | `from_rows(特徴量, min_rows)`、`unit_of(芝ダ, 距離)`、`units_of(特徴量)`、`members(特徴量)` |

### similarity/ — 近さのモデル

| 名前 | 仕事 | 主な public メソッド |
|---|---|---|
| `FeatureMatrix` | 特徴量の表を、距離を測れる数の行列にする。数の列は単位の中央値で埋めて標準化し、どの行も同じ値の列は使わない。欠損値だったかの 0/1 の列を足す。カテゴリの列は one-hot にする。0/1 の列は標準化せず 1/√2 を掛ける。まとまり A〜K の重みを掛ける。重み 0 と除く特徴量は使わない（[12-neighbor-distance.md](12-neighbor-distance.md)） | `fit(特徴量)`、`transform(特徴量)`、`column_names` |
| `GroupSimilarity` | 1つのグループの馬だけを覚え（k近傍法）、対象の馬の近さの点数を出す。点数は、同じ単位の1番人気全員と比べた順位（[13-closeness-score.md](13-closeness-score.md#2-点数のそろえ方)） | `fit(単位の行列, グループの馬か)`、`distances(行列)`、`scores(行列)`、`k` |
| `UnitSimilarity` | 1つの単位の、共通の `FeatureMatrix` 1つと、3つの `GroupSimilarity` | `fit(特徴量, グループの列)`、`scores(特徴量)`、`group_rows()` |
| `SimilarityModelSet` | 学習したモデルの一式。単位の決め方（`CourseUnitMap`）・単位の名前 → `UnitSimilarity`・学習に使った方針 | `scores(特徴量)` |
| `score_columns.py` の `SCORE_COLUMNS`・`UNIT` | 点数の列の名前（「勝利の近さ」など）と単位の列の名前 | ―（値） |

### decision/ — 判定

| 名前 | 仕事 | 主な public メソッド |
|---|---|---|
| `BuyDecision` | 3つの点数を比べて判定する。判定の線（`fade_margin`・`win_margin`）を持つ。同点は、消さない・単勝を足さない（[06-flowchart.md](06-flowchart.md#図2-1番人気の買い方を決める)） | `decide(点数の表)` |
| `bet_kinds.py` | 判定の名前（消す・単勝と複勝・複勝だけ）と、判定の列の名前 | ―（値） |

### evaluation/ — 掛け金と成績の表

| 名前 | 仕事 | 主な public メソッド |
|---|---|---|
| `StakePlan` | 判定ごとの単勝・複勝の掛け金（円）。投資と払戻を出す（[16-evaluation.md](16-evaluation.md#4-買い方と掛け金)） | `of(方針)`、`invested(判定)`、`returned(判定, 払戻)` |
| `DecisionSummary` | 判定した1番人気の束を、まとめの1行（消した馬の馬券外率・単勝も買った馬の勝率・回収率など）にする | `summarize(行)` |
| `KindSummary` | 判定ごとの成績の1行（勝率・複勝率・馬券外率・単勝回収率・複勝回収率） | `summarize(判定, 行)` |
| `EvaluationTables` | 年ごと・判定ごと・単位ごとの表を作る（[16-evaluation.md](16-evaluation.md#2-出す表)） | `tables(行)`、`by_year`・`by_kind`・`by_unit` |

### repository/ — モデルの保存

| 名前 | 読む・書くもの | 主な public メソッド |
|---|---|---|
| `SimilarityModelRepository` | 学習したモデルの一式（pickle）と、学習に使った方針（`settings.json`）。置き場所は `reports/favorite_buy_or_fade/models/`（[12-neighbor-distance.md の「6.」](12-neighbor-distance.md#6-保存)） | `save(一式)`、`load()` |

### setting/ — 方針

| 名前 | 仕事 | 主な public メソッド |
|---|---|---|
| `default_settings.toml` | 方針の初期値（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） | ―（ファイル） |
| `BuyOrFadeSettings` | 方針の値。初期値に `--config` のファイルを重ねて作る。知らない名前はエラー。時点に木曜を書いたらエラー | `load(パス)`、`to_dict()`・`from_dict()`・`to_json()` |

### workflow/ — 流れを進める

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `TrainingDataReader` | 方針の「学習の最初の年」の1月1日から、元DB の最後の開催日までの1番人気の学習データを読む（その前の年はウォームアップ） | `read(接続)` | `dataset_builder()`、共通の `TrainingPeriod` |
| `SimilarityTraining` | 学習の流れ。方針の時点の列にする → 単位を決める → 単位ごとに3つのモデルを作る | `train(学習データ)` | `CourseUnitMap`・`FeatureMatrix`・`UnitSimilarity`・`SimilarityModelSet` |
| `FavoriteJudgement` | 学習した一式で、1番人気ごとの単位・3つの点数・判定を出す（評価と予測で同じもの） | `judge(特徴量)` | `SimilarityModelSet`・`BuyDecision` |
| `YearlyEvaluation` | 1年ごとの評価。評価する年ごとに、学習の最初の年からその前年までで学習し直し、その年の1番人気を判定する | `run(学習データ)` | `SimilarityTraining`・`FavoriteJudgement` |
| `PredictionWorkflow` | 予測の流れ。オッズと人気を決め、学習した方針の時点で予測用データを作り、1番人気を判定する | `run(レースID, 渡された人気=省略可, 渡されたオッズ=省略可)` | 共通の `OddsResolver`・`PopularityApplier`・`DatasetBuilder`、`FavoriteJudgement` |

### command/ — コマンド

| 名前 | 仕事 |
|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |
| `TrainCommand` | `train`: 本番用のモデルを学習して保存し、単位ごとのグループの頭数の表を出す |
| `EvaluateCommand` | `evaluate`: 1年ごとの評価をして、年ごと・判定ごと・単位ごとの表を出す。`--rows-out` で1頭ずつの表も CSV に書く |
| `PredictCommand` | `predict`: 1レースの1番人気の単位・3つの点数・判定を出す。レースは rid か `--date --venue --race`。`--pops`・`--odds` を受け取る |
| `SettingsArgument` | `train` と `evaluate` に `--config` を足し、方針を読む |
| `yosou_name.py` の `YOSOU_NAME` | この予想の名前（`favorite_buy_or_fade`）。保存先の既定の置き場所に使う |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-25 |
| 更新 | 2026-09-25: k近傍法の設計に作り直した。同日、実装したクラスとフォルダに合わせて書き直した |
