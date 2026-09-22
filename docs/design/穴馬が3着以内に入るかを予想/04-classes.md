# 04 クラスとパッケージの設計

**この文書で決めること:** 手本の予想・危険な人気馬の予想と、この予想で、同じ仕事をするクラスをどこに置くか。この予想だけに要るクラスは何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: データを読む・特徴量を作る・学習する・予測するのクラスは、手本と危険な人気馬の予想と共通で、すでに `src/yosou/shared/` にある。この予想では、危険な人気馬の予想だけが持っている「人気に関する部品」と、手本だけが持っている「3着以内の目的変数を付ける部品」も `shared` に移し、3つの予想から使う。この予想だけに作るのは、穴馬の行を選ぶ・区分を決める・区分で絞る、の仕事のクラスと、予測の流れを進める `PredictionWorkflow`、コマンドである。学習の流れ（`TrainingWorkflow`）は共通のものをそのまま使う。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共通のクラスの一覧（どのクラスが何をするか）は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。人気に関するクラスの仕事は [人気馬の 04 の「3. この予想だけのクラスの一覧」](../人気馬が4着以下になるかを予想/04-classes.md#3-この予想だけのクラスの一覧) を参照。この文書には、この予想だけのクラスと、移すものを書く。
- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ・エンコーダー）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. 共通の部品と、この予想だけの部品の分け方

手本と危険な人気馬の予想に共通の部品は、すでに `src/yosou/shared/` にある（[人気馬の 04 の「1. 共通の部品と、この予想だけの部品の分け方」](../人気馬が4着以下になるかを予想/04-classes.md#1-共通の部品とこの予想だけの部品の分け方)）。この予想は、その2つの予想の中間（人気を使い、3着以内を当てる）なので、両方から部品を借りることになる。**予想のパッケージどうしで import はしない**（片方を直すともう片方が壊れる）。そこで、次を `shared` に移す（[15-decisions.md](15-decisions.md#6-共通部分の置き方)）。これが、この予想を作るときの最初の作業になる。

| 移すもの | 今の置き場所 | 移す先 | この予想での使い方 |
|---|---|---|---|
| `PopularityApplier`・`PopularityInput` | `favorites_out_of_top3/dataset/` | `shared/dataset/` | 予測のときの人気を決める。`PopularityInput` は「馬番:人気」に加えて「馬名:人気」（木曜用。馬番が無い）も受け取れるように広げる |
| `AnnouncedOddsRepository` | `favorites_out_of_top3/repository/` | `shared/repository/` | 締め切り前のオッズから人気を作る |
| `PopularityHistoryFeatures`・`PopularityRunSummary`・J の一覧 `POPULARITY_FEATURES` | `favorites_out_of_top3/feature/` | `shared/feature/group/`・`shared/feature/history/`・`shared/feature/feature_catalog.py` | まとまり J（[09-features.md](09-features.md#j-人気と人気の履歴4個)）を作る |
| `TargetBuilder`（3着以内なら 1。1着の列も付ける） | `form_aptitude_top3/dataset/` | `shared/dataset/`。名前は `Top3TargetBuilder` に変える | 目的変数を付ける（[10-target.md](10-target.md#作り方)） |
| 多頭数の線引き（14頭） | `favorites_out_of_top3/dataset/favorite_rule.py` の定数 `LARGE_FIELD_FROM` | `shared/dataset/` の定数 | `LongshotRule` と `FavoriteRule` が同じ値を使う。線引きを1か所で持つ |

移したあとの、まとまりごとの置き場所は次のとおり。

| まとまり | 共通にするか | この予想だけのもの |
|---|---|---|
| `repository/`（データの読み書き） | 共通（締め切り前のオッズを読むものを含む） | 無し |
| `dataset/`（学習データ・予測用データを作る） | 大半を共通 | 穴馬の決まり・区分・行の選択・区分での絞り込み |
| `feature/`（特徴量を作る） | 共通（まとまり A〜J） | この予想の特徴量の一覧 `CATALOG` だけ |
| `ml_model/`・`setting/`・`evaluation/` | 共通 | 初期値の設定ファイルだけ（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `workflow/`（流れを進める） | 学習は共通、予測は予想ごと | `PredictionWorkflow`、予測を出す時点の並び |
| `command/` | 部品は共通、入口は予想ごと | コマンドの組み立てと引数（`--pops`・`--zone`） |

**共通のクラスが、予想ごとの違いを知らずに済むようにする。** そのために、`shared` のインターフェース（`Protocol`）を、この予想のクラスが守る（手本・危険な人気馬の予想と同じ仕組み）。

| インターフェース（`shared` にある） | 決まり（public メソッド） | この予想で守るクラス |
|---|---|---|
| `SampleSelector` | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | `LongshotSelector` |
| `TargetLabeler` | `build(サンプルの行)`、`label_name` | 共通の `Top3TargetBuilder` をそのまま使う |
| `FeatureGroup` | `build(記録)` | 共通の `PopularityHistoryFeatures` をそのまま使う。この予想で新しく足すまとまりは無い |
| `ProbabilityModel` | `fit`・`predict_proba`・`save`・`load` | 共通の `LightGbmModel`・`CatBoostModel` をそのまま使う |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない | 片方の予想の都合が、もう片方に入り込まない |
| 予想のパッケージどうしも参照しない（`longshots_in_top3` から `favorites_out_of_top3` を import しない） | 両方で使う部品は `shared` に置く。予想を直したときに、ほかの予想が壊れない |
| `DatasetBuilder` は、行を選ぶクラス（`SampleSelector`）と目的変数を付けるクラス（`TargetLabeler`）を、作られるときに受け取る | 予想ごとの違いが、渡すクラスの中に収まる |
| `keep_samples()` は、特徴量を作ったあとに呼ぶ | レース内順位は、レースの全出走馬から計算する。穴馬だけに絞るのは、そのあとになる（[08-training-data.md](08-training-data.md#3-どのサンプルを入れるか)） |
| 区分で絞るのは、予測確率を出したあとにする | モデルは穴馬すべてで学習し、穴馬すべてに確率を出す。区分は出力の絞り込みだけである（[15-decisions.md](15-decisions.md#3-区分ごとに別のモデルにするか)） |
| 手本と危険な人気馬の予想も、移したあとの `shared` を使う形に直す | 同じ仕事のクラスが2つに増えると、直すときに片方を忘れる |

## 2. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `longshots_in_top3`（longshots = 穴馬、in top3 = 3着以内に入る）とする。

```text
src/yosou/shared/                   3つの予想から使う部品
├── repository/                     データの読み書き。1 SQL につき 1 リポジトリ（締め切り前のオッズを含む）
├── dataset/                        学習データ・予測用データを作る（人気を決める部品、3着以内の目的変数、多頭数の線引きを含む）
├── feature/                        特徴量を作る（まとまり A〜J と、過去の記録から数える部品）
├── ml_model/                       LightGBM・CatBoost・エンコーダー・2つの平均
├── setting/                        設定ファイルを読む
├── evaluation/                     当たり具合を測る
├── workflow/                       学習の流れ（TrainingWorkflow）
├── command/                        コマンドの部品のうち、予想に依らないもの（共通の引数・結果の表）
└── tests/                          共通の部品のテストと、テスト用の合成のシーズン

src/yosou/longshots_in_top3/        穴馬が3着以内に入るかを予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict）の引数
├── workflow/                       予測の流れ（ほかを順に呼ぶだけ）と、予測を出す時点
├── dataset/                        穴馬の決まり・区分・行を選ぶ・区分で絞る
├── feature/                        この予想の特徴量の一覧
├── setting/                        ハイパーパラメータの初期値のファイル
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`LongshotSelector` → `longshot_selector.py`）。学習したモデルは、Git の対象外の `reports/longshots_in_top3/models/` に、時点ごとに保存する。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `longshots_in_top3` → `shared`。`shared` から予想のパッケージを参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `dataset` → `feature` | 手本と同じ決まり |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 3. この予想だけのクラスの一覧

### dataset/ — 穴馬の決まり・区分・行を選ぶ・区分で絞る

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `LongshotRule` | 穴馬の決まりを表す値。頭数の線引き（共通の定数 14）と、頭数ごとの「穴馬の最初の人気」（4 か 6）・「大穴の最初の人気」（7 か 10）を持つ（[08-training-data.md](08-training-data.md#3-どのサンプルを入れるか)） | `popularity_range(出走頭数)`、`is_longshot(人気, 出走頭数)`、`are_longshots(人気の列, 出走頭数の列)`、`zone_of(人気, 出走頭数)`、`zones_of(人気の列, 出走頭数の列)` | ― |
| `LongshotZone` | 区分を表す値（列挙。中穴・大穴）。`--zone` の文字を読む。指定が無ければ「絞らない」 | `label`、`parse(書き方)` | ― |
| `LongshotSelector` | 学習データ・予測用データに入れる行を選び、「穴馬か」「穴馬の区分」の列を足す。特徴量を作ったあとに、穴馬の行だけを残す（[06-flowchart.md](06-flowchart.md#図1-学習データに入れる行の選び方)）。予測では、人気の分からない馬が1頭でもいれば止める（[06-flowchart.md](06-flowchart.md#図2-予測用データに人気を当てる)） | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | `LongshotRule`、共通の `FlatRunnerFilter` |
| `LongshotZoneFilter` | 予測の結果を、指定された区分の行だけにする。指定が無ければそのまま返す | `apply(予測の結果, 区分)` | ― |
| `column_names.py` の `IS_LONGSHOT`・`LONGSHOT_ZONE` | 「穴馬か」「穴馬の区分」の列の名前 | ―（値） | ― |
| `dataset_assembly.py` の `dataset_builder()` | この予想の部品（`LongshotSelector`、共通の `Top3TargetBuilder`、`CATALOG`、まとまり A〜F・H・I と共通の `PopularityHistoryFeatures`）を渡して、共通の `DatasetBuilder` を組み立てる | `dataset_builder(接続)` | 上のクラスと共通の `DatasetBuilder` |

決めた「馬番（木曜は馬名）→ 人気」は、`PredictionWorkflow` が共通の `DatasetBuilder.build_prediction_data()` に渡し、出走の行に当てるのは共通の `RaceEntryTableRepository` である（危険な人気馬の予想と同じ。[05-sequence.md](05-sequence.md#図2-予測)）。「穴馬の区分」の列は `LongshotSelector` が足し、モデルには渡さず、出力の表と評価にだけ使う（[08-training-data.md](08-training-data.md#2-列の種類)）。

### feature/ — 特徴量の一覧

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `feature_catalog.py` の `CATALOG` | この予想の特徴量の一覧。共通の A〜I（`BASE_FEATURES`）に共通の J（`POPULARITY_FEATURES`）を足したもの（75個。[09-features.md](09-features.md)） | ―（値） | 共通の `FeatureCatalog` |

この予想で新しく作るまとまり（`FeatureGroup`）は無い。`FeatureBuilder` には、この `CATALOG` と、共通の A〜F・H・I の8つに共通の `PopularityHistoryFeatures` を足したまとまりの並びを渡す。G（`FieldComparisonFeatures`）は `FeatureBuilder` が内部で持つ。

### workflow/ — 流れを進める

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PredictionWorkflow` | 予測の流れを進める。人気を決め、予測用データを作り、その時点のモデルを読み込み、2つの予測確率を平均し、区分で絞る | `run(レースID, 時点, 渡された人気, 区分)` | 共通の `PopularityApplier`・`DatasetBuilder`・`ModelRepository`・`EnsembleModel`、`LongshotZoneFilter` |
| `prediction_timings.py` の `TIMINGS` | この予想が学習し、予測を出す時点（木曜・前日・当日）の並び。手本と同じ3つ | ―（値） | ― |

`PredictionWorkflow` は、ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない。

**学習の流れ（`TrainingWorkflow`）は、共通のものをそのまま使う。** この予想は `TIMINGS`（3つ）と、初期値の設定ファイルを渡す。モデルは合わせて6つになる（[07-prediction-timing.md](07-prediction-timing.md)）。

### command/ — コマンド

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `CommandLine` | この予想 | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | この予想 | `train`: 学習する。期間の引数から `TrainingPeriod` を作る | `add_parser(subparsers)`、`run(引数)` |
| `PredictCommand` | この予想 | `predict`: 1レースの穴馬を予測する。`--pops` で全頭の人気を受け取って `PopularityInput` にし、`--zone` を `LongshotZone` にする | `add_parser(subparsers)`、`run(引数)` |
| `CommonArguments` | `shared` | 2つのサブコマンドに共通の引数（`--models` `--db` `--format` `--out`） | `add_to(parser)` |
| `TrainingReportTables` | `shared` | 学習の結果を表にする | `tables()` |
| `PredictionTable` | `shared` | 予測の結果を、3着以内に入る確率の高い順の表にする。`extra_columns` に「人気順位」「穴馬の区分」を渡して、その2列も出す | `table()` |

`--timing` は、時点の書き方を共通の `PredictionTiming.parse()` で読む。`--zone` の書き方が違うときに止めるのは `LongshotZone.parse()` で、誤りは `共通.cli` が1行で見せる（同じ判断を2か所に書かない）。

## 4. 選ばなかった選び方で変わるクラス

[15-decisions.md](15-decisions.md) で選ばなかった選び方にしたとき、上の一覧がどう変わるかを残しておく。

| 選び方 | 変わるクラス |
|---|---|
| 区分ごとに別のモデルにする（[15 の 3](15-decisions.md#3-区分ごとに別のモデルにするか)） | `LongshotSelector` が作られるときに区分を受け取り、`keep_samples()` でその区分の行だけを残す。`dataset_builder(接続, 区分)`。`TrainCommand` が区分ごとに `TrainingWorkflow` を回し、`reports/longshots_in_top3/models/<区分>/` に保存する。`PredictionWorkflow` は、`--zone` が無ければ2つのモデルを順に使う。`LongshotZoneFilter` は要らない |
| 穴馬の区分を特徴量に入れる（[15 の 5](15-decisions.md#5-穴馬の区分を特徴量に入れるか)） | `feature/longshot_zone_features.py` に、`FeatureGroup` を守る `LongshotZoneFeatures`（出走の行の区分の列を、カテゴリ特徴量「穴馬の区分」にする）を足し、`CATALOG` に1個足して 76個にする |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-23 |
