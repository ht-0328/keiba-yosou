# 04 クラスとパッケージの設計

**この文書で決めること:** 3つの予想（①先頭の馬・②序盤の位置・③前半のペース）を、手本の予想と共通の部品（`src/yosou/shared/`）の上にどう載せるか。共通の部品に何を足し、何を変えるか。この予想だけに要るクラスは何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: 学習の流れは `DevelopmentTrainingWorkflow`、予測の流れは `DevelopmentPredictionWorkflow` が進める。** この2つは、ほかのクラスを順に呼んでデータを受け渡すだけで、自分では計算しない。1頭ごとの学習データ（①②）は共通の `DatasetBuilder`、1レースごとの学習データ（③）は共通の `RaceDatasetBuilder` で作り、それぞれ1回だけ作って、目的変数の列を持ち替えて使い回す。モデルは、②と③の区分は共通の多クラスのモデルをそのまま使い、①は共通の二値のモデルを「レースの中でそろえる」クラスで包み、③の秒数は分位点回帰のモデルを新しく作る。

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共通のクラスの一覧（どのクラスが何をするか）は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。レース単位の学習データを作る仕組み（`RaceDatasetBuilder`・`RaceFeatureBuilder`）は [荒れ具合の 04 の 1.](../レースの荒れ具合を4段階で予想/04-classes.md#1-レース単位の学習データを作る仕組み) を参照。この文書には、足すもの・変えるもの・この予想だけのものを書く。
- 用語の意味は [02-glossary.md](02-glossary.md) を参照。クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. 3つの予想を、共通の部品の上にどう載せるか

| 予想 | 1行 | 学習データを作るクラス | 目的変数の列 | モデルのクラス | 学習を回すクラス |
|---|---|---|---|---|---|
| ① 先頭の馬 | 1頭 | 共通の `DatasetBuilder` | 先頭（1/0） | `LightGbmLeaderModel`・`CatBoostLeaderModel`（共通の二値のモデルを包み、レースの中で合計 1 にそろえる） | 共通の `TrainingWorkflow` |
| ② 序盤の位置 | 1頭 | ①と同じ学習データ（列を持ち替える） | 序盤の位置の区分（0〜2） | 共通の `LightGbmMulticlassModel`・`CatBoostMulticlassModel` | 共通の `TrainingWorkflow` |
| ③ ペースの区分 | 1レース | 共通の `RaceDatasetBuilder` | ペースの区分（0〜2） | 共通の `LightGbmMulticlassModel`・`CatBoostMulticlassModel` | 共通の `TrainingWorkflow` |
| ③ 前半タイム | 1レース | ③の区分と同じ学習データ（列を持ち替える） | 前半タイムの基準との差（秒） | `LightGbmQuantileModel`・`CatBoostQuantileModel`（新しく作る） | `PaceTimeTrainingWorkflow`（新しく作る） |

- **学習データは2つだけ作る。** 1頭ごとの表（①②）と、1レースごとの表（③）である。元DB を読むのは、この2回だけである。目的変数は、共通の `TrainingData.with_label()` で列を持ち替える（その列が欠損値の行は、そのとき除かれる）。
- **①はモデルを包む。** 二値分類の学習は共通の `LightGbmModel`・`CatBoostModel` がそのまま行い、包んだクラスが、検証データの後半で温度を決めて、予測のときにレースの中で合計 1 にそろえる（[03-library-basics.md](03-library-basics.md#2-先頭の確率をレースの中で合計-1-にそろえる)）。包んだクラスも `ProbabilityModel` の決まりを守るので、共通の `TrainingWorkflow`・`EnsembleModel`・`ModelRepository` がそのまま使える。
- **③の秒数だけ、学習を回すクラスを別に作る。** 分位点回帰のモデルは確率ではなく秒を返すので、`predict_proba()` の名前を持たせない（名前と中身が食い違うため）。共通の `TrainingWorkflow` は `predict_proba()` を呼ぶ前提なので、同じ手順（時点ごとに学習・保存・確かめ）を分位点回帰の名前で回すクラスを置く。

## 2. 共通の部品に足すもの・変えるもの

| 置き場所 | 種類 | 部品 | 仕事・主な public メソッド | 理由・備考 |
|---|---|---|---|---|
| `tools/共通/facts.py`（事実表） | **変更**（列を足す） | 事実表 | 1〜3コーナーの順位（`corner1`〜`corner3`）、最初のコーナーの番号と周回数（`first_corner_no`・`first_corner_lap`）、記録に2周目以降のコーナーがあるか（`corner_laps_over_one`）、最初のコーナーの先頭の馬番（`first_corner_leader_no`。1頭に決まらなければ NULL）、前3ハロン（`first3f`、秒）と測る区間（`first3f_m`）を足す | 目的変数（10）と、過去走から作る特徴量（K）の元。今は4コーナーの順位しか無い。列を足すだけなので、既存の道具と予想の値は変わらない。足したら `perf.py --check` で確かめる |
| `shared/repository/` | **変更** | `PastRunRepository` | 読む列に、上で足した列と、馬番・芝ダ・距離・コース・競馬場を足す | K の元（近5走の序盤の位置、同じ芝ダでの平均など） |
| `shared/repository/` | **変更** | `PeopleDayRepository` | 日ごとの数に、最初のコーナーの記録がある数・先頭の数・先団の数を足す | K の騎手の先頭率・先団率。騎手の近1年の3着以内の割合と同じ作り（前日までの 365日） |
| `shared/repository/` | 追加 | `RaceEarlyRecordRepository` | `read(対象)`。対象の最初の開催日の 1095日前から、最後の開催日までのレースを、1行 = 1レースで読む（競馬場・コース・距離・クラス・出走頭数・最初のコーナーの番号・先頭の馬番・前3ハロン・測る区間・成績が確定したか）。1つの SQL | M（コースの形）と、③の目的変数・Q（前半タイムの基準）の元。予測するレースは成績が無いので、条件の列だけ入る |
| `shared/feature/` | **変更** | `EntryRecords` | 列 `race_history`（上のリポジトリの表）を足す。既定は空の表 | 1頭ごとの特徴量（M）を作るときに、過去のレースの記録を見るため |
| `shared/dataset/` | **変更** | `EntryRecordsLoader` | 作られるときに `RaceEarlyRecordRepository` を受け取れるようにする。受け取らなければ呼ばず、`race_history` は空 | ほかの予想は SQL が増えない |
| `shared/feature/` | **変更** | `FeatureBuilder` | 作られるときに、同じレースの馬どうしで比べるまとまりの並び（既定は G だけ）を受け取れるようにする | L（同じレースの馬との比較・序盤）は、G と同じく、ほかのまとまりの特徴量を全頭で比べて作るため |
| `shared/dataset/` | **変更** | `TrainingData.with_label()` | クラスの並びも一緒に持ち替えられるようにする（`with_label(列名, クラスの並び=省略可)`） | ①（0・1）と②（0〜2）が同じ学習データから作られるため |
| `shared/dataset/` | **変更** | `RaceDatasetBuilder` | 払戻のリポジトリの口を、レースごとの結果の表を返す決まり `RaceResultSource`（`read(記録, 最初の日)`）に一般化する。前日までの何日を読むか（今は 366日）と、単勝オッズの確かめ（`FieldOddsCheck`）を、作られるときに渡せるようにする | ③は払戻ではなく前半タイムの記録を結果に使い、基準に3年を見るため。オッズは使わない。荒れ具合の予想は、払戻のリポジトリを包む `PayoutResultSource` を渡し、動きは変わらない |
| `shared/feature/` | **変更** | `RaceRecords` | 列の名前 `payouts` を `race_results`（レースごとの結果）に変える | 払戻に限らなくなるため。荒れ具合の予想の3か所の呼び方を直す |
| `upset_level/feature/` → `shared/feature/` | **移す** | `RaceConditionSummary` | レースの条件（11個）を、レースの1頭目の値から作る | ③のまとまり R にそのまま使う。予想のパッケージどうしは参照しない決まりなので、`shared` に移す |

**共通のクラスが、予想ごとの違いを知らずに済むようにする。** そのために、`shared` のインターフェースを、この予想のクラスが守る。

| インターフェース（`shared` にある） | 決まり（public メソッド） | この予想で守るクラス |
|---|---|---|
| `SampleSelector` | `training_samples`・`prediction_runners`・`keep_samples` | `EarlyRunnerSelector` |
| `TargetLabeler` | `label_name`・`build` | `EarlyPositionLabeler`（①②） |
| `RaceTargetLabeler` | `label_names`・`build` | `PaceLabeler`（③） |
| `RaceResultSource`（新設） | `read(記録, 最初の日)` | `PaceRecordSource` |
| `FeatureGroup` | `build(記録)` | `EarlyHistoryFeatures`（K）・`CourseShapeFeatures`（M） |
| 同じレースの馬どうしで比べるまとまり（新設の決まり。G の `FieldComparisonFeatures` と同じ形） | `build(出走の行, ほかのまとまりの特徴量)` | `EarlyFieldComparisonFeatures`（L） |
| `RaceFeatureGroup` | `build(レースの記録)` | 共通の `RaceConditionSummary`（R）、`PaceMaterialFeatures`（P）、`PaceBaselineFeatures`（Q） |
| `ProbabilityModel` | `fit`・`predict_proba`・`save`・`load` | `LightGbmLeaderModel`・`CatBoostLeaderModel` |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない。予想のパッケージどうしも参照しない | 手本と同じ。片方の予想の都合が、もう片方に入り込まない |
| 1頭ごとの特徴量 A〜I は、共通の `FeatureBuilder` のまとまりをそのまま使い、この予想では書き直さない | 直す場所が1か所で済む |
| 前半タイムの基準は `PaceBaseline` の1か所で作り、目的変数（`PaceLabeler`）と特徴量（Q）の両方がそれを使う | 基準を変えたとき、目的変数と特徴量が食い違わない |
| 序盤の位置の計算（順位から 0〜1 に直す、先団・中団・後方に分ける）は `EarlyPosition` の1か所で行い、目的変数と K・L の両方が使う | 過去の走と今回の走で、同じ物差しになる |
| 学習データ・予測用データは、同じ `DatasetBuilder`・`RaceDatasetBuilder` で作る | 学習と予測で、特徴量の中身がずれないようにする（[11-leak-prevention.md](11-leak-prevention.md#決まり) の 4） |

## 3. この予想だけのクラスの一覧

### workflow/ — 流れを進める

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `DevelopmentTrainingWorkflow` | 学習の流れを進める。1頭ごとの学習データと 1レースごとの学習データを1回ずつ作り、4つの予想の学習を順に呼ぶ。学習する予想は引数で絞れる | `run(設定ファイルのパス, 予想の並び)`、`read_training_data()`、`train(学習データ2つ, 設定ファイルのパス, 予想の並び)` | 共通の `TrainingWorkflow`（①②③の区分）、`PaceTimeTrainingWorkflow`（③の秒数） |
| `PaceTimeTrainingWorkflow` | ③の秒数の学習を回す。時点ごとに、その時点の列だけで2つの分位点回帰のモデルを学習し、保存し、検証データで確かめる | `train(学習データ, 設定)` | `PeriodSplitter`・`ModelRepository`（共通）、`PaceTimeEvaluator` |
| `DevelopmentPredictionWorkflow` | 予測の流れを進める。1頭ごとの予測用データと 1レースの予測用データを作り、4つの予想のモデルをその時点の分だけ読み込み、予測をまとめて `DevelopmentForecast` にし、`PredictionArchiveRepository` に残す | `run(レースID, 時点)` | 共通の `DatasetBuilder`・`RaceDatasetBuilder`・`ModelRepository`・`EnsembleModel`、`QuantileEnsemble`、`PaceTimeInterval`、`PredictionArchiveRepository` |
| `DevelopmentModelKind` | 4つの予想を表す値（列挙。先頭・序盤の位置・ペースの区分・前半タイム）。目的変数の列名、モデルのクラスの並び、保存先のフォルダ名（`leader`・`position`・`pace_class`・`pace_time`）を持つ | `label_name`・`member_types`・`folder`・`parse(書き方)`・`all()` | ― |
| `prediction_timings.py` の `TIMINGS` | 学習し、予測を出す時点（木曜・前日・当日）の並び | ―（値） | ― |
| `DevelopmentForecast` | 1レースの予測の入れ物。1頭ごとの表（先頭の確率・先団・中団・後方の確率・使った履歴の数）と、レースの1行（ハイ・平均・スローの確率・前半タイムの真ん中と幅・基準・測る区間）を持つ | ― | ― |

### dataset/ — 行を選ぶ・正解を付ける

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `EarlyRunnerSelector` | 学習データ・予測用データに入れる行を選ぶ。平地・出走馬・期間内の全頭を残す（[06-flowchart.md](06-flowchart.md#図3-学習データに入れる行の選び方)）。`keep_samples` はそのまま返す | `training_samples(出走の行, 学習データの始まり)`・`prediction_runners(出走の行, レースID)`・`keep_samples(特徴量の付いた行)` | 共通の `FlatRunnerFilter` |
| `EarlyPosition` | 最初のコーナーでの順位と出走頭数から、序盤の位置（0〜1）と区分（先団・中団・後方）を出す。**序盤の位置の物差しの唯一の置き場所** | `of(順位, 出走頭数)`・`zone_of(序盤の位置)` | ― |
| `EarlyPositionLabeler` | ①②の目的変数を付ける（[06-flowchart.md](06-flowchart.md#図1-先頭と序盤の位置の正解の付け方)）。列は「先頭」「序盤の位置の区分」と、評価用の「序盤の位置」 | `label_name`・`build(サンプルの行)` | `EarlyPosition` |
| `PaceBaseline` | 前半タイムの基準（平均・標準偏差・件数・どの段で作ったか）を、各レースについて、開催日の前日までの 1095日のレースから作る（[06-flowchart.md](06-flowchart.md#図2-前半タイムの基準の決め方とペースの正解の付け方)）。**基準の唯一の置き場所** | `attach(レースの記録)` | ― |
| `PaceRecordSource` | `RaceResultSource` を守る。記録の中のレースの序盤の記録に、`PaceBaseline` で基準を付けて返す | `read(記録, 最初の日)` | `PaceBaseline` |
| `PaceLabeler` | ③の目的変数を付ける。列は「ペースの区分」と「前半タイムの基準との差」 | `label_names`・`build(レースの行)` | ― |
| `dataset_assembly.py` の `horse_dataset_builder()`・`race_dataset_builder()` | この予想の部品を渡して、共通の `DatasetBuilder`・`RaceDatasetBuilder` を組み立てる関数 | `horse_dataset_builder(接続)`・`race_dataset_builder(接続)` | 上のクラスと共通のクラス |

### feature/ — 特徴量を作る

| クラス | まとまり | 仕事 | 呼ぶクラス |
|---|---|---|---|
| `EarlyHistoryFeatures` | K（15個） | 過去走と騎手の日ごとの数から、序盤の位置取りの履歴を作る | `EarlyRunSummary`・`SmoothedRate`・共通の `AsOfLookup` |
| `EarlyFieldComparisonFeatures` | L（9個） | K の値を、同じレースの全頭で比べる（ほかの馬の合計・内側と外側の合計・レース内順位） | ― |
| `CourseShapeFeatures` | M（3個） | 過去のレースの記録から、そのコースの最初のコーナーの番号・記録されるコーナーの数・先頭になった馬の馬番の位置の平均を付ける | `CourseHistory` |
| `EarlyRunSummary` | ― | 1頭の過去走から、近5走・近10走の序盤の位置の平均・ばらつき・先頭の数などを出す（開催日より前の走だけ） | `EarlyPosition` |
| `SmoothedRate` | ― | 走った数が少ない馬の割合を、全体の割合に寄せる（[09-features.md の K](09-features.md#k-序盤の位置取りの履歴15個)） | ― |
| `CourseHistory` | ― | コース（競馬場・コース・距離）ごとに、前日までの 1095日のレースの記録をまとめる | 共通の `AsOfLookup` |
| `PaceMaterialFeatures` | P（10個） | 1頭ごとの K・L を、レースに1つの値に集約する（先頭率の1位・2位・合計など） | ― |
| `PaceBaselineFeatures` | Q（6個） | `PaceRecordSource` の表から、前半タイムの基準・標準偏差・件数・測る区間と、M のコースの2個をレースに1つ付ける | ― |
| `feature_catalog.py` の `HORSE_CATALOG`・`RACE_CATALOG` | ― | この予想の特徴量の一覧。1頭ごとは共通の `BASE_FEATURES`（71個）に K・L・M を足した 98個、1レースごとは R・P・Q の 27個。[09-features.md](09-features.md) の表の写し | 共通の `FeatureCatalog` |

### ml_model/ — 先頭の確率をそろえるモデルと、分位点回帰のモデル

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `WithinRaceLeaderModel` | 共通の二値のモデル1つを包む。`fit` では、検証データを前半と後半に分け、前半で早期終了しながら中のモデルを学習し、後半で温度を決める。`predict_proba` では、中のモデルの確率を raw スコアに戻し、温度で割ってレースごとに合計 1 にする（[05-sequence.md](05-sequence.md#図3-先頭の確率をレースの中でそろえる)） | `from_settings(設定)`・`fit(学習データ, 検証データ)`・`predict_proba(データ)`・`tree_count`・`save(パス)`・`load(パス, 設定)` |
| `LightGbmLeaderModel`・`CatBoostLeaderModel` | 上のクラスで、中のモデルを `LightGbmModel`・`CatBoostModel` にしたもの。名前と保存するファイルの名前を持つ | 上と同じ |
| `RaceSoftmax` | raw スコアを温度で割り、レースIDごとに合計 1 の確率に直す | `apply(raw スコア, レースID, 温度)` |
| `TemperatureFitter` | 温度の候補（0.50〜2.00 の 0.01 刻み）から、レースごとのログ損失がいちばん小さいものを選ぶ | `fit(raw スコア, レースID, 先頭か)` |
| `ValidationHalves` | 検証データを、開催日で前半と後半に分ける（真ん中の開催日で切る） | `split(検証データ)` |
| `QuantileModel` | 分位点回帰の2つのモデルに共通の決まり（インターフェース） | `from_settings`・`fit`・`predict_quantiles(データ)`（行数 × 3）・`tree_count`・`save`・`load` |
| `LightGbmQuantileModel` | `LGBMRegressor(objective="quantile")` を 10%・50%・90% の3つ持つ。エンコーダーは共通の `LightGbmEncoder`（[12-lightgbm.md](12-lightgbm.md)） | 上と同じ |
| `CatBoostQuantileModel` | `CatBoostRegressor(loss_function="MultiQuantile:alpha=0.1,0.5,0.9")` を1つ持つ。エンコーダーは共通の `CatBoostEncoder`（[13-catboost.md](13-catboost.md)） | 上と同じ |
| `QuantileEnsemble` | 2つの分位点回帰のモデルの値を平均し、行ごとに小さい順に並べ直す | `predict_quantiles(データ)` |
| `PaceTimeInterval` | 基準との差の3つの値に基準を足して、前半タイムの秒数（真ん中・10%・90%）に直す | `to_seconds(3つの値, 基準)` |

### evaluation/ — 当たり具合と比べる基準

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `LeaderEvaluator` | ①の当たり具合（レースごとのログ損失・確率1位が先頭だった割合・上位3頭に先頭がいた割合・確率の帯ごとの実際の割合）を測る。共通の `TrainingWorkflow` の `Evaluator` の決まりを守る | `evaluate(時点, アンサンブル, データ)` |
| `PaceTimeEvaluator` | ③の秒数の当たり具合（MAE・分位点の損失・80% の予測区間の包含率と平均の幅）を測る | `evaluate(時点, アンサンブル, データ)` |
| `DevelopmentBaselines` | モデルによらない基準（全馬に同じ確率・平滑化した先頭率をそろえたもの・推定脚質・学習データの割合・基準だけの秒数）の当たり具合を、同じ指標で出す（[16-evaluation.md](16-evaluation.md#3-比べる基準)） | `leader(データ)`・`position(データ)`・`pace_class(データ)`・`pace_time(データ)` |

②と③の区分の当たり具合は、共通の `ClassModelEvaluator` をそのまま使う。

### command/ — コマンド

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `CommandLine` | この予想 | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | この予想 | `train`: 学習する。期間の引数から `TrainingPeriod` を作る。`--kind` で予想を絞れる（既定は4つ全部） | `add_parser(subparsers)`・`run(引数)` |
| `PredictCommand` | この予想 | `predict`: 1レースの展開を予測する | `add_parser(subparsers)`・`run(引数)` |
| `DevelopmentReportTables` | この予想 | 学習の結果（4つの予想の当たり具合と、比べる基準）を表にする | `tables()` |
| `DevelopmentPredictionTables` | この予想 | 予測の結果を、1頭ごとの表（先頭の確率の高い順）とレースの1行の表にする | `tables()` |
| `CommonArguments` | `shared` | 2つのサブコマンドに共通の引数（`--models` `--db` `--format` `--out`） | `add_to(parser)` |

### repository/ — 予測の記録を残す

| クラス | 置き場所 | 読む・書くもの | 主な public メソッド |
|---|---|---|---|
| `PredictionArchiveRepository` | この予想 | 予測のたびに、予測用データ（特徴量）と `DevelopmentForecast` を、Git の対象外の `reports/race_development/predictions/<開催日>/` に書き足す。同じレース・同じ時点でも上書きせず、予測した時刻を名前に付けて残す | `save(予測用データ2つ, 予測, 予測した時刻)` |

残す理由は、あとで「発走前に実際に手に入っていた材料で、どれだけ当たったか」を確かめるためである（[15-decisions.md](15-decisions.md#12-予測の記録を残すか)）。今の元DB は、同じレースの出馬表を新しい版で上書きするので、過去の予測の時点の材料を後から作り直せない。

## 4. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `race_development`（race development = レースの展開）とする。

```text
src/yosou/shared/                   5つの予想から使う部品（上の「2.」を足す・変える）
├── repository/                     RaceEarlyRecordRepository を足す。PastRunRepository・PeopleDayRepository に列を足す
├── dataset/                        RaceDatasetBuilder の結果の口を一般化。TrainingData.with_label を変える
├── feature/                        EntryRecords・FeatureBuilder・RaceRecords を変える。RaceConditionSummary を移す
└── …                               ほかは変えない

src/yosou/race_development/         序盤の位置取りと前半ペースを予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict）の引数と、結果の表
├── workflow/                       学習と予測の流れ（ほかを順に呼ぶだけ）、4つの予想の値、予測を出す時点、予測の入れ物
├── evaluation/                     先頭と秒数の当たり具合、比べる基準
├── ml_model/                       先頭の確率をそろえるモデル、分位点回帰のモデル
├── dataset/                        行を選ぶ・序盤の位置・前半タイムの基準・目的変数を付ける
├── feature/                        まとまり K・L・M（1頭ごと）と R 以外の P・Q（1レース）、特徴量の一覧
│   └── history/                    過去の記録から数える部品（EarlyRunSummary・SmoothedRate・CourseHistory）
├── repository/                     予測の記録を残す
├── setting/                        ハイパーパラメータの初期値のファイル
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`EarlyPositionLabeler` → `early_position_labeler.py`）。学習したモデルは、Git の対象外の `reports/race_development/models/<予想>/<時点>/` に保存する（予想ごとに `ModelRepository` を1つ作り、置き場所とモデルのクラスを変える。`ModelRepository` は変えない）。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `race_development` → `shared`。`shared` から予想のパッケージを参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `evaluation` → `ml_model` → `dataset` → `feature`。`workflow` は `repository` を使う | 手本と同じ決まり |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 5. 選ばなかった選び方で変わるクラス

[15-decisions.md](15-decisions.md) で選ばなかった選び方にしたとき、上の一覧がどう変わるかを残しておく。

| 選び方 | 変わるクラス |
|---|---|
| 先頭を CatBoost の `QuerySoftMax` で学習する（[15 の 1](15-decisions.md#1-先頭の確率の作り方)） | `CatBoostLeaderModel` の中身が `CatBoostRanker` になり、温度は要らなくなる。LightGBM には同じものが無いので、`LightGbmLeaderModel` は今のまま残る |
| 前半タイムの秒数を出さない（[15 の 6](15-decisions.md#6-前半タイムの秒数の出し方)） | `ml_model/` の分位点回帰の5クラスと `PaceTimeTrainingWorkflow`・`PaceTimeEvaluator`・`PaceTimeInterval` が要らなくなる |
| ほかの予想と共通の特徴量を使わない（[15 の 7](15-decisions.md#7-ほかの予想と共通の特徴量-71個も使うか)） | `HORSE_CATALOG` が K・L・M と、枠番・馬番・距離などの数個だけになる。クラスは変わらない |
| コースの形の表を作る（[15 の 8](15-decisions.md#8-コースの形の表を最初の版に入れるか)） | コースの表を読む `CourseShapeRepository` と、表の値を付ける `CourseShapeTableFeatures` が増える |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
