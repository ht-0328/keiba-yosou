# 04 クラスとパッケージの設計

**この文書で決めること:** データを読む・特徴量を作る・学習する・予測するを、どのクラスにやらせるか。中央の荒れ具合の予想の部品のうち、何をそのまま使い、何を地方のために足すか。クラスをどのフォルダ（パッケージ）・ファイルに置くか。コマンドが、どんな引数を受け取り、何を出すか。

**結論: 学習の流れは共通の `TrainingWorkflow`、予測の流れは中央の荒れ具合の予想と同じ `PredictionWorkflow` が進める。** レース単位の学習データを作る `RaceDatasetBuilder`・まとまり A〜E・券種・荒れ具合・目的変数の付け方・券種ごとのモデルの置き場所は、中央の荒れ具合の予想（`yosou.upset_level`）の部品をそのまま使う。地方だけの決めごと（線引きの額・事実表と出走別着度数地方・当日の馬場傾向のレースの値・学習データのとっておき・発走前の1レースの入口）は、この予想のパッケージ `src/yosou/local_upset_level/` に置く。

- 用語の意味は [02-glossary.md](02-glossary.md) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。
- 分け方の決まり（1ファイル1クラス・1 SQL 1 リポジトリ・Workflow は受け渡すだけ・`Manager` を付けない など）は、手本の [04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) と同じである。

## 1. そのまま使う部品と、地方だけの部品の分け方

| 区分 | 何か | 置き場所 |
|---|---|---|
| そのまま使う共通の部品 | `RaceDatasetBuilder`・`RaceFeatureBuilder`・`FeatureBuilder`・1頭ごとのまとまり A〜H・J のクラス・`RacePayoutRepository`・`RaceResultSummary`・`RequiredInfoCheck`・`FieldOddsCheck`・`OddsInput`・`OddsResolver`・`LightGbmMulticlassModel`・`CatBoostMulticlassModel`・`EnsembleModel`・`TrainingWorkflow`・`ModelRepository`・多クラスの評価・`ClassTrainingReportTables`・`RacePredictionTable` | `src/yosou/shared/` |
| そのまま使う中央の荒れ具合の予想の部品 | `RaceSelector`・`BetType`・`UpsetLevel`・`UpsetLevelRule`（線引きの額を外から受ける）・`UpsetLevelLabeler`・`PAYOUT_COLUMNS`・まとまり A〜E を集約するクラス（`RaceConditionSummary`・`OddsShapeFeatures`・`FieldStrengthSpreadFeatures`・`FavoriteRiskFeatures`・`ConditionUpsetRateFeatures`）・`RACE_FEATURES`・`PredictionWorkflow`・`model_repositories()`・`UpsetThresholdSummary` | `src/yosou/upset_level/` |
| そのまま使う地方の決めごと | 事実表の元データ（`LOCAL_FACTS_SOURCE`）、出走別着度数地方の欄（`LOCAL_CAREER_LAYOUT`）、地方の土台の特徴量の一覧（`LOCAL_BASE_FEATURES`）、クラスの並び順の付け直し（`LOCAL_CLASS_ORDER_FIXES`） | `tools/共通/local_codes.py`・`src/yosou/local_form_aptitude_top3/`・`src/yosou/shared/` |
| そのまま使うトラックバイアスの部品 | `BiasRunRepository`・`RaceEntryRepository`・`RaceSlopes`・`DaySlopes`・`PriorSlopeTableBuilder`・`PriorSlopeTable`・`UsedSlopes`（中央）、`LocalBiasHistory`（地方。学習データの年ごとのリーク防止） | `src/yosou/track_bias/`・`src/yosou/local_track_bias/` |
| 地方だけの部品 | 線引き（`LocalUpsetRule`）、組み立て（`local_race_dataset_builder`）、学習データのとっておき（`TrainingDataCache`）、U のレースの値（`UsedSlopeFeatures`・`race_slopes_table`・`RaceUsedSlopes`）、過去の傾きの表の年ごとのとっておき（`PriorSlopeYearStore`）、発走前の1レースの入口（`LocalUpsetForecast`）、特徴量の一覧（`CATALOG`・`HORSE_CATALOG`）、時点の表示名、コマンド、初期値の設定ファイル | `src/yosou/local_upset_level/` |

**中央の荒れ具合の予想のパッケージを参照する理由。** 地方の全頭の予想は、中央の全頭の予想のパッケージを参照せず、共通で使う部品を `shared` に移した（[地方の全頭の予想の 04](../地方競馬の近走と適性から3着以内を予想/04-classes.md#1-共通の部品と地方だけの部品の分け方)）。この予想では、中央の荒れ具合の予想のパッケージ（`yosou.upset_level`）をそのまま参照する。理由は、使う部品（券種・荒れ具合・線引き・目的変数・まとまり A〜E・予測の流れ）が多く、どれも「荒れ具合の予想だけのもの」で、ほかの予想からは使われないためである（展開の予想も同じようにこのパッケージの `race_dataset_builder` を参照している）。参照の向きは `local_upset_level` → `upset_level` の一方向で、逆は無い（[15-decisions.md の 5](15-decisions.md#5-中央の荒れ具合の予想の部品をどう使うか)）。

## 2. パッケージ構成

```text
src/yosou/upset_level/              中央の荒れ具合の予想（そのまま使う部品。直さない）
├── dataset/                        RaceSelector・BetType・UpsetLevel・UpsetLevelRule・UpsetLevelLabeler・PAYOUT_COLUMNS
├── feature/                        まとまり A〜E を集約するクラスと RACE_FEATURES（49個）
├── workflow/                       PredictionWorkflow・model_repositories
└── evaluation/                     UpsetThresholdSummary（しきい値ごとの数え上げ）

src/yosou/local_upset_level/        地方のレースの荒れ具合を4段階で予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict）の引数。入口。元DB の既定は地方。学習の報告の「線引き」の表
├── workflow/                       発走前の1レースの入口（LocalUpsetForecast）、予測を出す時点と表示名、置き場所
├── dataset/                        地方の線引き（LocalUpsetRule）、RaceDatasetBuilder の組み立て、学習データのとっておき（TrainingDataCache）
├── feature/                        特徴量の一覧（CATALOG = 中央の 49個 ＋ U 2個）、U のレースの値（UsedSlopeFeatures・RaceUsedSlopes）
├── repository/                     過去の傾きの表の年ごとのとっておき（PriorSlopeYearStore）
├── setting/                        ハイパーパラメータの初期値のファイル
└── tests/                          この予想の組み立てのテスト。地方の合成DB だけを使う
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの。学習したモデルは、Git の対象外の `reports/地方のレースの荒れ具合を4段階で予想/models/<券種>/<時点>/` に保存する（券種は `win`・`quinella`・`trio`・`trifecta`、時点は `thursday`（出馬表）・`day_before`・`race_day`。中央と同じ `model_repositories()`）。学習データのとっておきと過去の傾きの表は `reports/地方のレースの荒れ具合を4段階で予想/cache/`。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `local_upset_level` → `upset_level`・`shared`・`local_form_aptitude_top3`（地方の決めごとだけ）・`track_bias`・`local_track_bias`。逆に参照しない | 片方の予想の都合が、もう片方に入り込まない |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `dataset` → `feature` → `repository` | 手本と同じ決まり |
| 線引きの額は `LocalUpsetRule` の1か所で持ち、目的変数（`UpsetLevelLabeler`）と E（`ConditionUpsetRateFeatures`）の両方に同じものを渡す | 線引きを変えたとき、目的変数と特徴量が食い違わない |
| U のレースの値は、学習（`race_slopes_table`）と予測（`RaceUsedSlopes`）で同じ列の名前の表にして、同じ `UsedSlopeFeatures` に渡す | 学習と予測で特徴量の作り方がずれない（[11-leak-prevention.md](11-leak-prevention.md#決まり) の 4・11） |
| 中央の荒れ具合の予想の部品は直さない。地方で違うところは、値（線引き・事実表・一覧・表）を外から渡すか、この予想のクラスで包む | 中央の動きが変わらない |

## 3. この予想だけのクラスの一覧

### command/ — コマンド

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンド（train・predict）を実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | `train`: 学習データを `TrainingDataCache` から読む（無ければ作って書く）。券種ごとに共通の `TrainingWorkflow` を回し、3つの時点のモデルを学習して保存する。報告は `ClassTrainingReportTables`（時点の表示名を渡す）と `UpsetThresholdTable` | `run(引数)` |
| `PredictCommand` | `predict`: 1レースの券種ごとの荒れ具合を `LocalUpsetForecast` で出し、`RacePredictionTable` で表にする | `run(引数)` |
| `PeriodArguments` | `train` の学習データの期間の引数。既定はウォームアップ 2016年・学習 2019年・検証 2025年7月・テスト 2026年から | `add_to(parser)`、`period_of(args)` |
| `UpsetThresholdTable` | `train` の報告のうち、検証データで時点ごとに「中荒れ以上の確率」のしきい値ごとのレース数・実際に中荒れ以上だった割合を並べる表（中央の `UpsetThresholdSummary` を時点ごとに回す） | `table()` |

### workflow/ — 発走前の1レースの入口と決めごと

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `LocalUpsetForecast` | これから走る（か終わった）1レースの、券種ごとの荒れ具合の確率を出す入口。`RaceUsedSlopes` で U のレースの値を出し、それを渡した `local_race_dataset_builder` と中央の `PredictionWorkflow` で予測する。`predict` と道具「地方の推奨買目」が使う | `run(接続, レースID, 時点, 渡されたオッズ, 券種)`、`upset_or_more(接続, レースID, 時点, 券種)`（券種 → 中荒れ以上の確率） |
| `TIMINGS`・`TIMING_LABELS`・`TIMING_CHOICES` | 予測を出す時点（3つ）と表示名（出馬表・前日・当日）、コマンドの説明の書き方 | ― |
| `DEFAULT_MODELS_DIR`・`DEFAULT_CACHE_DIR` | モデルと、学習データ・過去の傾きの表のとっておきの既定の置き場所 | ― |

### dataset/ — 学習データ・予測用データの決めごと

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `LocalUpsetRule`・`LOCAL_THRESHOLDS` | 地方の券種ごとの線引き。中央の `UpsetLevelRule` に地方の額を渡したもの | `levels_of(券種, 払戻)`、`thresholds_of(券種)`、`is_upset_or_more(券種, 払戻)` |
| `local_race_dataset_builder()` | 地方の部品を渡して共通の `RaceDatasetBuilder` を組み立てる関数（`dataset_assembly.py`）。ローダーに `LOCAL_FACTS_SOURCE` と出走別着度数地方の `CareerCountRepository`、1頭ごとの一覧に `HORSE_CATALOG`、レース単位の一覧に `CATALOG`、まとまり A〜E に `UsedSlopeFeatures` を足し、線引きに `LocalUpsetRule`、要る情報の案内に nvstore の文を渡す | `local_race_dataset_builder(接続, レースごとの使う傾きの表, 線引き=省略可)` |
| `TrainingDataCache` | 学習データを作って pickle にとっておく。元DB から全出走（`BiasRunRepository`）を読んで `LocalBiasHistory` で U を付け、`race_slopes_table` でレースごとの表にしてから `build_training_data` を呼ぶ。同じ期間のファイルがあれば読むだけ（`rebuild` で作り直す） | `path(期間)`、`load_or_build(接続を開く関数, 期間, rebuild)` |

### feature/ — 特徴量の一覧と U のレースの値

| 名前 | 仕事 | 主な public メソッド |
|---|---|---|
| `HORSE_CATALOG` | 集約の元になる1頭ごとの特徴量の一覧（地方の土台 A〜H ＋ J。調教は無い） | ― |
| `CATALOG` | この予想の特徴量の一覧（中央の `RACE_FEATURES` 49個 ＋ U 2個） | ― |
| `UsedSlopeFeatures` | U のレースの値（2個）。レースごとの使う傾きの表を受け取り、対象のレースの行を返す。`RaceFeatureGroup` を守る。表に無いレースは欠損値 | `build(レース単位の記録)` |
| `race_slopes_table()` | `LocalBiasHistory` の表（1行 = 1頭の U の5列）から、レースごとの使う傾き（index はレースID）を取る関数 | ― |
| `RaceUsedSlopes` | これから走る1レースの使う傾き（1行の表）。当日とその前の日の終わったレースの傾き（`RaceSlopes`・`DaySlopes`）と、年ごとの過去の傾きの表（`PriorSlopeYearStore`）を `UsedSlopes` で混ぜる | `of(レースID, 時点)` |

### repository/ — とっておき

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `PriorSlopeYearStore` | 「その年の1月1日より前のレースだけで作った過去の傾きの表」を `cache/過去の傾き-<年の始まり>.pkl` にとっておく。同じ元DB のものがあれば読むだけ。無ければ元DB の全出走から作る（1分ほど） | `path(年の始まり)`、`load(接続, 年の始まり)` |

## 4. 道具「地方の推奨買目」からの使われ方

発走前の通知の推奨買目（`tools/地方の推奨買目/`）は、3連複の買い方に「3連複の中荒れ以上の確率 0.6 以上」の条件を持つ（`TicketPlan.upset_min`）。`Recommender` は、その条件のある券種があるときだけ荒れ具合の部品（`UpsetSource`）から券種ごとの中荒れ以上の確率を受け取る。

| 使う場所 | 部品 | 確率の出し方 |
|---|---|---|
| 道具「地方の推奨買目」の `recommend.py` | `UpsetProbabilities`（`upset_probabilities.py`） | 渡された接続で `LocalUpsetForecast.upset_or_more()` を当日の時点で呼ぶ |
| 発走前の通知（`notify.py --local`） | `SavedUpsetProbabilities`（`tools/発走前の通知/`） | 計算せず、`<rid>.荒れ具合.json`（`LocalUpsetFile`）を読む。書くのは、発走前に全頭の予想を出す `local_predict.py` で、全頭の予想の `predict` と同じ接続のまま `UpsetProbabilities` で単勝・馬連・3連複・3連単の確率を出して書く（出せなければ理由を書く） |

発走前の通知が同じ接続で出すのは、どちらの予想も地方の全成績の事実表（一時表）を使い、作るのに数分かかるためである。接続を開くたびに作り直すと1レース数分かかり、しかも同じプロセスで作り直すたびに遅くなる。同じ接続なら事実表を作るのは1回で、荒れ具合の分は十秒ほどで済む。`local_predict.py` は毎回新しいプロセスで動くので、レースを重ねても遅くならない。判断の手順は [06-flowchart.md の図1](06-flowchart.md#図1-推奨買目が-3連複を買うかどうかの判断)、買い方の決まりは [買い方の 10](../買うレースと買い目を決める/10-local-recommended-tickets.md)。

## 5. コマンドの引数

コマンドは `train`（学習）・`predict`（1レースの予測）の2つで、リポジトリ直下から `uv run python -m yosou.local_upset_level <train か predict> …` で動かす。引数の名前と意味は、中央の荒れ具合の予想の [04 の「6. コマンドの引数」](../レースの荒れ具合を4段階で予想/04-classes.md#6-コマンドの引数) と同じにする。違いは次のとおり。

| 引数 | この予想での既定・意味 |
|---|---|
| `--models` | `reports/地方のレースの荒れ具合を4段階で予想/models`（中は `<券種>/<時点>/`） |
| `--db` | `../nvdata-store/nvdata.duckdb`（環境変数 `YOSOU_LOCAL_DB` があればそのパス）。読むだけ |
| `--timing` | `出馬表`・`前日`・`当日`（英語の `thursday`・`day_before`・`race_day` でもよい。`木曜` も `出馬表` として受ける） |
| `--warmup-from`・`--train-from`・`--valid-from`・`--test-from` | [08-training-data.md の「4. 期間の指定」](08-training-data.md#4-期間の指定)。既定は 2016-01-01・2019-01-01・2025-07-01・2026-01-01 |
| `train` の `--cache`・`--rebuild` | 学習データの pickle をとっておく場所（既定 `reports/地方のレースの荒れ具合を4段階で予想/cache`）と、あっても作り直す指示（[08-training-data.md の 5.](08-training-data.md#5-学習データのとっておき)） |
| `predict` の `--cache` | 過去の傾きの表をとっておく場所（既定は同じ `cache`）。無ければ元DB から作る |
| `--venue` | 競馬場の名前かコード（地方の名前: 大井・名古屋 など、または 30〜61） |
| `--odds`・`--bet` | 中央と同じ。前日・当日は全頭ぶん渡す（省略すると速報 0B30 の締め切り前のオッズか、終わったレースの確定オッズ）。`--bet` は券種を絞る |

`train` が出す表は、券種ごとに、学習データの期間・検証データでの当たり具合・混同行列・保存したモデル（`ClassTrainingReportTables`。時点は 出馬表・前日・当日 と出す）と、「荒れるレースだけ買う」使い方の線引きの表（`UpsetThresholdTable`。[16-evaluation.md の 4.](16-evaluation.md#4-使い方の線引き)）。中央の `train` が出す4つの基準との比べ（利用者の規則・1番人気のオッズだけ など）は出さない（基準との比べは研究で済ませた。[16-evaluation.md の 3.](16-evaluation.md#3-比べる基準)）。`predict` が出す表は中央と同じ（券種・固い・中荒れ・大荒れ・超荒れの確率・いちばん高いクラス・中荒れ以上の確率）。

引数の決まり（省略を受け付けない・誤りは1行で止まる・元DB は読む段だけ開く）も中央と同じである。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-06 |
