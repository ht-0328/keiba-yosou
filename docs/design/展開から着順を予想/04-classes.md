# 04 クラスとパッケージの設計

**この文書で決めること:** 7つの予想（前半の①先頭の馬・②序盤の位置・③前半のペース、後半の④4コーナーの位置・⑤上がりの速さ・⑥後半のペース、⑦着順）と、年ごとの的中率と回収率の確かめを、手本の予想と共通の部品（`src/yosou/shared/`）の上にどう載せるか。共通の部品に何を足し、何を変えるか。この予想だけに要るクラスは何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: 学習の流れは `DevelopmentTrainingWorkflow`、予測の流れは `DevelopmentPredictionWorkflow`、年ごとの確かめの流れは `BacktestWorkflow` が進める。** この3つは、ほかのクラスを順に呼んでデータを受け渡すだけで、自分では計算しない。1頭ごとの学習データは共通の `DatasetBuilder`、1レースごとの学習データは共通の `RaceDatasetBuilder` で、それぞれ1回だけ作る。予想ごとの学習データは、そこから特徴量の列を選び直し、前の組の予測（S・T）の列を足して作る（`KindStacker`）。1つの組の予想は、`GroupFitter` が決めた期間で学習して予測する。前の組の「学習に使っていない予測」は、`WalkForwardPredictor` が年ごとに `GroupFitter` を呼んで作り、学習・年ごとの確かめの両方がそれを使う。印・買い目・精算は `betting/` に置く。

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共通のクラスの一覧（どのクラスが何をするか）は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。レース単位の学習データを作る仕組み（`RaceDatasetBuilder`・`RaceFeatureBuilder`）は [荒れ具合の 04 の 1.](../レースの荒れ具合を4段階で予想/04-classes.md#1-レース単位の学習データを作る仕組み) を参照。この文書には、足すもの・変えるもの・この予想だけのものを書く。
- 用語の意味は [02-glossary.md](02-glossary.md) を参照。クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。
- プログラムを作りながら、この文書の最初の版（2026-09-26 の書き足しのとき）から変えたところは、最後の「作りながら変えたところ」にまとめた。

## 1. 7つの予想を、共通の部品の上にどう載せるか

| 予想 | 1行 | 予想ごとの学習データ | 目的変数の列 | モデルのクラス（LightGBM・CatBoost） | モデルの種類（`ModelFamily`） |
|---|---|---|---|---|---|
| ① 先頭の馬 | 1頭 | 1頭ごとの学習データの A〜I・K・L・M | 先頭（1/0） | `LightGbmWithinRaceModel`・`CatBoostWithinRaceModel`（共通の二値のモデルを包み、レースの中で合計 1 にそろえる） | `WITHIN_RACE` |
| ② 序盤の位置 | 1頭 | ①と同じ | 序盤の位置の区分（0〜2） | 共通の `LightGbmMulticlassModel`・`CatBoostMulticlassModel` | `MULTICLASS` |
| ③ ペースの区分 | 1レース | 1レースごとの学習データの R・P・Q | ペースの区分（0〜2） | 共通の `LightGbmMulticlassModel`・`CatBoostMulticlassModel` | `MULTICLASS` |
| ③ 前半タイム | 1レース | ③の区分と同じ | 前半タイムの基準との差（秒） | `LightGbmQuantileModel`・`CatBoostQuantileModel` | `QUANTILE` |
| ④ 4コーナーの位置 | 1頭 | 1頭ごとの学習データの全部（A〜I・K〜O）と S | 4コーナーの位置（0〜1） | `LightGbmRegressionModel`・`CatBoostRegressionModel` | `REGRESSION` |
| ⑤ 上がりの速さ | 1頭 | ④と同じ | 上がりの速さ（0〜1） | 同上 | `REGRESSION` |
| ⑥ 後半のペース | 1レース | 1レースごとの学習データの全部（R・P・Q・U）と、1レースごとの S | 後半タイムの基準との差（秒） | `LightGbmQuantileModel`・`CatBoostQuantileModel` | `QUANTILE` |
| ⑦ 着順 | 1頭 | ④と同じに T を足したもの | 1着（1/0） | `LightGbmWithinRaceModel`・`CatBoostWithinRaceModel`。2つの平均から、`OrderLambdaFitter` で λ を決める | `WITHIN_RACE` |
| ⑦ の比べる基準 | 1頭 | 1頭ごとの学習データの全部（S・T を入れない） | 1着（1/0） | ⑦と同じ | `WITHIN_RACE` |

- **学習データは2つだけ作る。** 1頭ごとの表（特徴量 111個）と、1レースごとの表（34個）である。元DB を読むのは、この2回だけである（`DatasetLoader`。作ったものは残し、元DB が変わっていなければ次からは読むだけ）。
- **予想ごとの学習データは、列を選び直して作る。** `KindStacker` が、予想ごとの特徴量の一覧（`DevelopmentModelKind` が持つ）に列を合わせ、後半と着順の予想には S・T の列を足す。目的変数は、共通の `TrainingData.with_label()` で持ち替える（その列が欠損値の行は、そのとき除かれる）。
- **4種類のモデルを、同じ手順で学習・予測する。** 学習は `KindTrainer`（種類ごとに LightGBM と CatBoost のクラスを選ぶ）、予測は `KindForecaster`（種類ごとに、2つのモデルの値の平均のしかたを選ぶ）が行う。共通の `TrainingWorkflow` は使わない。後半と着順の学習データには、年ごとに学習し直した前の組の予測が要り、共通の `TrainingWorkflow` の「1つの期間で学習して保存する」手順に合わないためである。
- **①⑦はモデルを包む。** 二値分類の学習は共通の `LightGbmModel`・`CatBoostModel` がそのまま行い、包んだクラスが、検証データの後半で温度を決めて、予測のときにレースの中で合計 1 にそろえる（[03-library-basics.md](03-library-basics.md#2-先頭の確率をレースの中で合計-1-にそろえる)）。包んだクラスも `ProbabilityModel` の決まりを守るので、共通の `EnsembleModel`・`ModelRepository` がそのまま使える。

## 2. 共通の部品に足すもの・変えるもの

| 置き場所 | 種類 | 部品 | 仕事・主な public メソッド | 理由・備考 |
|---|---|---|---|---|
| `tools/共通/facts.py`（事実表） | **変更**（列を足す） | 事実表 | 1〜3コーナーの順位（`corner1`〜`corner3`）、最初のコーナーの番号（`first_corner_no`）、記録されたコーナーの数（`corner_count`）、記録に2周目以降があるか（`corner_laps_over_one`）、最初のコーナーでの順位（`first_corner_rank`）、最初のコーナーの先頭の馬番（`first_corner_leader_no`。1頭に決まらなければ NULL）、前3ハロン（`first3f`）、レースの後3ハロン（`last3f_race`）、上がり3ハロンのある出走馬の数（`last3f_count`）を足す | 目的変数（10）と、過去走から作る特徴量（K・N）の元。列を足すだけなので、既存の道具と予想の値は変わらない |
| `shared/repository/` | **変更** | `EntryRepository` | 読む列に、上の列と `track_code`・`corner4`・`last3f`・`last3f_rank` を足す | 目的変数を付けるため（特徴量にはしない） |
| `shared/repository/` | **変更** | `PastRunRepository` | 読む列に、馬番・競馬場・コース・芝ダ・距離・最初のコーナーの番号と順位・周回・上がり3ハロン・上がりのある頭数・レースの後3ハロンを足す | K・N の元 |
| `shared/repository/` | **変更** | `PeopleDayRepository` | 日ごとの数に、最初のコーナーの記録がある騎乗の数（`early_starts`）・先頭の数（`early_leads`）・先団の数（`early_fronts`）を足す | K の騎手の先頭率・先団率 |
| `shared/repository/` | 追加 | `RaceEarlyRecordRepository` | `read(対象)`。対象の最初の開催日の 1095日前から最後の開催日までの平地のレースを、1行 = 1レースで読む（競馬場・コース・距離・クラス・出走頭数・最初のコーナー・先頭の馬番・前3ハロン・後3ハロン・成績が確定したか）。1つの SQL | M（コースの形）と、前半・後半タイムの基準の元。予測するレースは成績が無いので、条件の列だけ入る |
| `shared/feature/` | **変更** | `EntryRecords` | 列 `race_history`（上のリポジトリの表）を足す。既定は空の表 | M と全体の先頭率を、過去のレースの記録から作るため |
| `shared/dataset/` | **変更** | `EntryRecordsLoader`・`HistoryRecordsLoader`・`RaceRecordsLoader` | 作られるときに `RaceEarlyRecordRepository` を受け取れるようにする。受け取らなければ呼ばず、`race_history` は空 | ほかの予想は SQL が増えない |
| `shared/feature/` | **変更** | `FeatureBuilder` | 作られるときに、同じレースの馬どうしで比べるまとまりの並び（`field_groups`。既定は G だけ）を受け取れるようにする | L・O は、G と同じく、ほかのまとまりの特徴量を全頭で比べて作るため |
| `shared/feature/` | 追加 | `FieldFeatureGroup` | 比べるまとまりの決まり（`build(出走の行, ほかのまとまりの特徴量)`） | 上の `field_groups` の型 |
| `shared/dataset/` | **変更** | `TrainingData.with_label()` | クラスの並びも一緒に持ち替えられるようにする（`with_label(列名, クラスの並び=省略可)`） | 同じ学習データから、二値・3クラス・回帰の予想を作るため |
| `shared/dataset/` | **変更** | `RaceDatasetBuilder` | 払戻のリポジトリの口を、レースごとの結果の表を返す決まり `RaceResultSource`（`read(最初の日)`）にする。予測のときに何日前からの結果を読むか（`history_days`。既定は 365日）と、単勝オッズの確かめ（`field_odds_check`。オッズを使わない予想は None）を、作られるときに渡せるようにする | ③⑥は払戻ではなく前半・後半タイムを結果に使い、基準に3年を見るため。荒れ具合の予想は、払戻のリポジトリがそのまま `RaceResultSource` を守るので、動きは変わらない |
| `shared/feature/` | **変更** | `RaceRecords` | 列の名前 `payouts` を `race_results`（レースごとの結果）に変える | 払戻に限らなくなるため。荒れ具合の予想の呼び方も直した |
| `upset_level/feature/` → `shared/feature/` | **移す** | `RaceConditionSummary` | レースの条件（11個）を、レースの1頭目の値から作る | R にそのまま使う。予想のパッケージどうしは参照しない決まりなので、`shared` に移す |
| `shared/dataset/` | **変更** | `DatasetBuilder` | 予測用データの `market` の列に、その時点の単勝オッズを足す | 予測のときに、印の☆（単勝の期待値）を出すため。ほかの予想には、列が1つ増えるだけ |
| 研究 `馬券の買い方の検証` → `shared/` | **移す** | `TicketType`・`TicketTypeSpec`（`shared/betting/`）、`FinalOddsRepository`・`PayoutRepository`・`PayoutFlagRepository`・`RaceDayRange`（`shared/repository/`） | 7券種の確定オッズと払戻の明細と払戻のフラグを、期間ぶん読む。券種の値（単勝〜3連単、元DB の表の名前、組番の形） | 年ごとの確かめで、期待値と精算に使う。同じ仕事のクラスを2か所に置かないため、研究から `shared` に移し、研究（「馬券の買い方の検証」と「既存モデルの改善」）はそれを使うように直した。研究の券種と「荒れ具合の予想の券種」の対応は、研究の中の `upset_bet_of()` に移した |

**共通のクラスが、予想ごとの違いを知らずに済むようにする。** そのために、`shared` のインターフェースを、この予想のクラスが守る。

| インターフェース（`shared` にある） | 決まり（public メソッド） | この予想で守るクラス |
|---|---|---|
| `SampleSelector` | `training_samples`・`prediction_runners`・`keep_samples` | `EarlyRunnerSelector` |
| `TargetLabeler` | `label_name`・`build` | `HorseLabeler`（①②④⑤⑦ の5つの目的変数をまとめて付ける） |
| `RaceTargetLabeler` | `label_names`・`build` | `RaceLabeler`（③⑥） |
| `RaceResultSource`（新設） | `read(最初の日)` | `PaceRecordSource` |
| `FeatureGroup` | `build(記録)` | `EarlyHistoryFeatures`（K）・`CourseShapeFeatures`（M）・`ClosingHistoryFeatures`（N） |
| `FieldFeatureGroup`（新設） | `build(出走の行, ほかのまとまりの特徴量)` | `EarlyFieldComparisonFeatures`（L）・`ClosingFieldComparisonFeatures`（O） |
| `RaceFeatureGroup` | `build(レースの記録)` | 共通の `RaceConditionSummary`（R）、`PaceMaterialFeatures`（P）、`PaceBaselineFeatures`（Q）、`LateMaterialFeatures`（U） |
| `ProbabilityModel` | `fit`・`predict_proba`・`save`・`load` | `LightGbmWithinRaceModel`・`CatBoostWithinRaceModel`（①と⑦） |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない。予想のパッケージどうしも参照しない | 手本と同じ。片方の予想の都合が、もう片方に入り込まない |
| 1頭ごとの特徴量 A〜I は、共通の `FeatureBuilder` のまとまりをそのまま使い、この予想では書き直さない | 直す場所が1か所で済む |
| 前半・後半タイムの基準は `PaceBaseline` の1か所で作り、目的変数（`RaceLabeler`）と特徴量（Q・U）の両方がそれを使う | 基準を変えたとき、目的変数と特徴量が食い違わない |
| 順位を 0〜1 に直す計算（序盤・4コーナー・上がり・着順）は、`RelativeRank` の1か所で行う。序盤の位置の区分は `EarlyPosition` の1か所 | 過去の走と今回の走で、同じ物差しになる |
| 前の組の予測は、`WalkForwardPredictor` の1か所で作る。学習と年ごとの確かめは、同じものを使う | 学習と確かめで、S・T の作り方がずれない（[11-leak-prevention.md の決まり 11](11-leak-prevention.md#決まり)） |
| 前の組の予測の列の足し方は、`KindStacker` の1か所。学習データにも予測用データにも同じものを使う | 学習と予測で、特徴量の中身がずれない（[11-leak-prevention.md](11-leak-prevention.md#決まり) の 4） |
| 券種ごとの当たる確率は、3連単の確率の表から `TicketProbability` の1か所で出す | 券種の間で確率が食い違わない |

## 3. この予想だけのクラスの一覧

各フォルダの `__init__.py` の先頭にも、同じ「クラス → 仕事」の表を書いてある。

### workflow/ — 流れを進める

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `DevelopmentTrainingWorkflow` | 学習の流れ。時点ごとに、前半・後半の組の「学習に使っていない予測」（前の年まで）と、指定の年のモデルを学習して保存する。着順の組は、指定の年のモデルだけを学習する | `run(年, 時点の並び, 設定ファイルのパス)` → 保存したモデルの並び（`SavedModel`） |
| `DevelopmentPredictionWorkflow` | 予測の流れ。1頭ごと・1レースの予測用データを作り、前半 → 後半 → 着順の順に、その時点のモデルで予測して、前の組の予測を次の組の特徴量に足す。印と印どおりの買い目まで出し、`PredictionArchiveRepository` に残す | `run(レースID, 時点)` → `DevelopmentForecast` |
| `BacktestWorkflow` | 年ごとの確かめの流れ（[16-evaluation.md の 7.](16-evaluation.md#7-年ごとの的中率と回収率)）。学習データを作り、3つの組の予測を年ごとに作り、年ごとに印と買い目を作って精算し、表にする | `run(年の並び, 設定ファイルのパス)` → `BacktestReport` |
| `DatasetLoader` | 1頭ごと・1レースごとの学習データを作る（2017年1月から。ウォームアップは 2016年）。作ったものは `DatasetRepository` に残し、元DB が変わっていなければ読むだけ | `load(最後の年)` → `KindDatasets` |
| `DevelopmentModelKind`・`KindSpec` | 7つの予想と比べる基準（列挙）と、その決めごと（目的変数の列・1行が1レースか・モデルの種類・特徴量の一覧・予測の列・クラスの並び）。値はモデルを保存するフォルダの名前（`leader`・`position`・`pace_class`・`pace_time`・`corner4`・`closing`・`late_pace_time`・`finish`・`finish_plain`） | `spec`・`folder`・`parse(書き方)` |
| `ModelFamily` | モデルの種類（`WITHIN_RACE`・`MULTICLASS`・`QUANTILE`・`REGRESSION`） | ― |
| `ForecastGroup` | 3つの組（前半・後半・着順）と、組ごとの予想の並び、年ごとに学習し直すときの学習データの最初の年（2017・2018・2019年） | `kinds`・`first_train_year`・`label` |
| `WalkForwardSchedule`・`YearPeriod` | 予測する年ごとの、学習・検証・予測の期間（[16-evaluation.md の 7.](16-evaluation.md#7-年ごとの的中率と回収率)） | `periods(組, 年)`・`first_year(組)` |
| `KindStacker` | 1頭ごと（1レースごと）のデータを、予想の特徴量の一覧に合わせ、S・T の列を足す。学習データにも予測用データにも使う | `apply(予想, データ, 前半の予測, 後半の予測)` |
| `KindDatasets` | 1頭ごと・1レースごとの学習データを持ち、予想ごとの学習データを `KindStacker` で作る | `of(予想, 前半の予測, 後半の予測)`・`labeled(予想, データ)` |
| `KindTrainer` | 1つの予想の、LightGBM と CatBoost のモデルを学習する（モデルの種類ごとにクラスを選ぶ） | `fit(予想, 学習データ, 検証データ, 設定)` |
| `KindForecaster` | 1つの予想の2つのモデルで予測し、予測の列の表にする | `predict(予想, 2つのモデル, データ)` |
| `GroupFitter` | 1つの組の予想を、決めた期間で学習し、予測する年のサンプルを予測する。⑦ は検証データの後半で λ も決める。学習（train）は、受け取り口（`sink`）を渡して、学習したモデルを受け取る | `fit_predict(組, 期間, 学習データ, 前半の予測, 後半の予測, 時点, 設定, sink=省略可)` → `GroupForecast` |
| `WalkForwardPredictor` | 前の組の「学習に使っていない予測」を、年ごとに `GroupFitter` で作る。作った予測は、作った条件（設定・学習データの範囲・前の組の予測）と一緒に `OutOfSampleRepository` に残し、同じ条件なら読むだけにする | `predict(組, 年の並び, 学習データ, 前半の予測, 後半の予測, 時点, 設定)` |
| `KindModelStore` | 予想ごと・時点ごとの学習済みモデル（⑦ は λ も）を、共通の `ModelRepository` で読み書きする | `save(予想, 時点, 2つのモデル, 設定, λ)`・`load(予想, 時点)`・`load_lambda(時点)` |
| `RaceBetting` | 1レースの1着の確率から3連単の確率の表を作り、印（モデルと人気順）と、3つの買い方の買い目を作る | `tickets(レースID, 1レースの表, λ, 確定オッズ)` |
| `YearBetting` | 1年ぶんのレースの買い目を `RaceBetting` で作り、`TicketSettler` で精算する | `settle(年, 1年ぶんの表, 確定オッズ, 払戻, フラグ)` |
| `YearMarket` | 1年ぶんの、7券種の確定オッズと払戻の明細と払戻のフラグを読む（3連単のオッズは1年で千万行を超えるので、1年ずつ読む） | `read(接続, 年)` |
| `BacktestFrames` | 学習データと予測から、買い目を作る1年ぶんの表と、当たり具合を測る表を作る | `betting(年, 前半の予測, 着順の予測)`・`horses(…)`・`races(…)` |
| `DevelopmentForecast`・`BacktestReport`・`SavedModel` | 1レースの予測、年ごとの確かめの結果、保存したモデルの入れ物 | ― |

### dataset/ — 行を選ぶ・正解を付ける

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `EarlyRunnerSelector` | 学習データ・予測用データに入れる行を選ぶ。平地・出走馬・期間内の全頭を残す（[06-flowchart.md](06-flowchart.md#図3-学習データに入れる行の選び方)） | `training_samples`・`prediction_runners`・`keep_samples` |
| `EarlyPositionLabeler` | ① 先頭と ② 序盤の位置の区分を付ける（評価用に序盤の位置 0〜1 も） | `build(サンプルの行)` |
| `LateLabeler` | ④ 4コーナーの位置と ⑤ 上がりの速さを付ける | `build(サンプルの行)` |
| `FinishLabeler` | ⑦ 1着を付ける（同着の1着のレースは全頭を欠損値）。評価用に確定着順も | `build(サンプルの行)` |
| `HorseLabeler` | 上の3つをまとめて、1頭ごとの5つの目的変数を付ける（`TargetLabeler` を守る） | `label_name`・`build(サンプルの行)` |
| `RaceLabeler` | ③ ペースの区分・前半タイムの基準との差と、⑥ 後半タイムの基準との差を付ける（`RaceTargetLabeler` を守る） | `label_names`・`build(レースの行)` |
| `PaceRecordSource` | `RaceResultSource` を守る。`RaceEarlyRecordRepository` のレースの記録に、前半・後半の基準を付けて返す | `read(最初の日)` |
| `dataset_assembly.py` の `horse_dataset_builder()`・`race_dataset_builder()`・`horse_feature_builder()` | この予想の部品を渡して、共通の `DatasetBuilder`・`RaceDatasetBuilder`・`FeatureBuilder` を組み立てる関数 | ― |
| `label_names.py` | 目的変数と評価用の列の名前 | ― |

### feature/ — 特徴量を作る

| クラス | まとまり | 仕事 |
|---|---|---|
| `EarlyHistoryFeatures` | K（15個） | 過去走と騎手の日ごとの数から、序盤の位置取りの履歴を作る |
| `EarlyFieldComparisonFeatures` | L（9個） | K の値を、同じレースの全頭で比べる |
| `CourseShapeFeatures` | M（3個） | 過去のレースの記録から、コースの最初のコーナーの番号などを付ける |
| `ClosingHistoryFeatures` | N（10個） | 過去走から、末脚の履歴を作る |
| `ClosingFieldComparisonFeatures` | O（3個） | N の値を、同じレースの全頭で比べる |
| `PaceMaterialFeatures` | P（10個） | K・L を、レースに1つの値に集約する |
| `PaceBaselineFeatures` | Q（6個） | 前半タイムの基準と、M のコースの2個をレースに1つ付ける |
| `LateMaterialFeatures` | U（7個） | 後半タイムの基準と、N を集約したものをレースに1つ付ける |
| `EarlyForecastFeatures` | S（1頭ごと 9個・1レースごと 6個） | 前半の予想の結果から、S の列を作る |
| `LateForecastFeatures` | T（7個） | 後半の予想の結果から、T の列を作る |
| `StackedColumns` | ― | 特徴量の表を予想ごとの一覧の列に合わせ、S・T の列を足す。学習データでは、前の組の予測の無い行を外す |
| `GroupForecast` | ― | 1つの組の予測の入れ物（1頭ごとの表と1レースごとの表）と、予測の列の名前 |
| `RaceOrderStatistic` | ― | 同じレースの馬の値の、何番目に大きい（小さい）値。レースごとに関数を呼ばず、1回の並べ替えで出す |
| `feature_catalog.py` | ― | 特徴量の一覧。1回で作る `HORSE_CATALOG`（111個）・`RACE_CATALOG`（34個）と、予想ごとの一覧（[09-features.md](09-features.md) の表の写し） |

`feature/history/` — 過去の記録から数える部品（開催日より前のものだけを使う決まりを、ここで守る）

| クラス | 仕事 |
|---|---|
| `RelativeRank` | 順位と頭数から 0〜1 の値を出す。**序盤・4コーナー・上がり・着順の物差しの、ただ1つの置き場所** |
| `EarlyPosition` | 序盤の位置と区分（先団・中団・後方）。**序盤の位置の物差しの、ただ1つの置き場所** |
| `PaceBaseline` | 前半（か後半）タイムの基準を付ける（[06-flowchart.md の図2a](06-flowchart.md#図2a-基準の決め方)）。**基準の、ただ1つの置き場所** |
| `RaceBaselineLookup` | レースの表に前半・後半の基準と測る区間を付ける。予測するレース（記録にまだ無い）には、記録とそのレースの条件を合わせて付け直す |
| `RunLags` | 出走の行ごとに、前日までの過去走を新しい順に 10走ぶん横に並べる（「今回と同じ芝ダの走だけの平均」のように、今回のレースによって変わる値を出すため） |
| `LagStatistics` | 横に並べた過去走の、平均・最小・ばらつき・合計・日数の重み付きの平均・条件付きの平均 |
| `SmoothedRate` | 走った数の少ない馬の割合を、全体の割合に寄せる |
| `GlobalEarlyRate` | 前日までの 365日の、全体の先頭率・先団率（レースの記録から数える） |
| `DailyRate` | 騎手の日ごとの数から、前日までの 365日の割合（共通の `Top3Rate` と同じ作りで、数える列を選べるもの） |
| `EarlyRunSummary` | K のうち、馬の 13個 |
| `ClosingRunSummary` | N の 10個 |
| `CourseHistory` | コースごとの、前日までの 1095日のレースの記録のまとめ（M） |

### ml_model/ — レースの中でそろえるモデル・分位点回帰・回帰・2着3着の割り当て

| クラス | 仕事 |
|---|---|
| `WithinRaceModel` | 共通の二値のモデル1つを包む（①と⑦）。`fit` では、検証データを前半と後半に分け、前半で早期終了しながら中のモデルを学習し、後半で温度を決める。`predict_proba` では、raw スコアを温度で割ってレースごとに合計 1 にする。温度は、モデルのファイルの隣の小さな JSON に書く |
| `LightGbmWithinRaceModel`・`CatBoostWithinRaceModel` | 上のクラスで、中のモデルを `LightGbmModel`・`CatBoostModel` にしたもの |
| `RaceSoftmax`・`TemperatureFitter`・`ValidationHalves` | レースごとのソフトマックス、温度の候補（0.50〜2.00）から選ぶ、検証データを開催日で前半と後半に分ける |
| `RegressionModel`・`QuantileModel` | 回帰と分位点回帰のモデルに共通の決まり（`predict`・`predict_quantiles`） |
| `LightGbmRegressor`・`CatBoostRegressor` | 回帰と分位点回帰の中身。ライブラリの回帰のモデル1つと、共通のエンコーダー |
| `LightGbmRegressionModel`・`CatBoostRegressionModel` | ④⑤の回帰（`regression`・`RMSE`） |
| `LightGbmQuantileModel`・`CatBoostQuantileModel` | ③⑥の分位点回帰（LightGBM は 10%・50%・90% の3つのモデル、CatBoost は `MultiQuantile` の1つのモデル） |
| `RegressionEnsemble`・`QuantileEnsemble` | 2つのモデルの値を平均する（分位点は並べ直す） |
| `OrderProbability` | 1着の確率と λ から、3連単の全部の並びの確率と、各馬の 2着以内・3着以内の確率を出す（Harville の式） |
| `OrderLambdaFitter` | λ の候補（0.50〜1.00）から、実際の 2着・3着の馬に付けた条件付きの確率がいちばん高くなるものを選ぶ |
| `FinishForecaster` | ⑦ のアンサンブルと λ を持ち、1着・2着以内・3着以内の確率を出す。λ のファイル（`order_lambda.json`）を読み書きする |

### evaluation/ — 当たり具合

| クラス | 仕事 |
|---|---|
| `RaceMetrics` | レースの中で見る指標（レースごとのログ損失・確率1位の的中・レース内の順位相関・多クラスのログ損失）を、まとめて計算する |
| `StageYearMetrics` | ①〜⑥ の、年ごとの当たり具合と簡単な基準（[16-evaluation.md の 7.](16-evaluation.md#7-年ごとの的中率と回収率) の表4） |
| `StageBaselines` | ①〜③ のモデルによらない基準（先頭率をそろえただけ・推定脚質・前年までの割合・前走の区分や逃げそうな馬の数からの割合。[16-evaluation.md の 3.](16-evaluation.md#3-比べる基準)） |
| `FinishYearMetrics` | ⑦ の、年ごとの当たり具合（表3） |
| `PlaceCalibration` | 3着以内の確率の、帯ごとの実際の割合 |

### betting/ — 印・買い目・精算

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `TicketType` | `shared/betting/`（研究から移した） | 7つの券種を表す値（単勝〜3連単）。元DB の表の名前、組番の形、順番を問うか | `label`・`key`・`spec`・`parse(書き方)`・`of_key(鍵)` |
| `Ticket` | この予想 | 1つの買い目（レース・券種・馬番の並び・買い方の名前・金額 100円）。組番は払戻の表と同じ形（馬番を2桁ずつ。順番を問わない券種は小さい順） | `combo`・`frame(買い目の並び)` |
| `TicketProbability` | この予想 | 1レースの3連単の確率の表から、1つの券種の全部の買い目の当たる確率を出す（複勝は 7頭立て以下なら 2着以内） | `of(3連単の確率の表, 券種, 出走頭数)` |
| `Mark` | この予想 | 6つの印（◎○▲△☆注） | ― |
| `MarkAssigner`・`PopularityMarkAssigner` | この予想 | 1レースの馬に印を付ける（[06-flowchart.md の図4](06-flowchart.md#図4-印の付け方)）。比べる基準は、単勝オッズの低い順に ◎○▲△ | `assign(1レースの表)` |
| `MarkTicketRule` | この予想 | 印から、券種ごとの印どおりの買い目を作る（[16-evaluation.md の 8.](16-evaluation.md#8-券種ごとの買い方)） | `tickets(レースID, 印の表, 券種)` |
| `ExpectedValueTicketRule` | この予想 | 券種ごとに、当たる確率 × 確定オッズ が 1.0 以上の買い目を作る（複勝・ワイドは最低オッズ） | `tickets(当たる確率の表, 確定オッズの表, 券種)` |
| `TicketSettler` | この予想 | 買い目を払戻の表と照らし合わせて、払戻と当たったかを付ける（[06-flowchart.md の図5](06-flowchart.md#図5-買い目の精算)） | `settle(買い目の表, 払戻, フラグ)` |
| `ReturnSummary` | この予想 | 精算した買い目を、買い方 × 券種 × 年（と合計）ごとにまとめ、的中率・回収率・最大の払戻を除いた回収率を出す | `table(精算した買い目)` |

研究 `馬券の買い方の検証` にも、印と買い目を作るクラスと精算のクラスがある。そちらは研究の買い方（危険な人気馬を消すなど）に合わせた作りなので、この予想では `TicketType` と読み込みのリポジトリだけを共通にし、買い目と精算はこの予想の決まりで作った。

### command/ — コマンド

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | `train`: 時点ごとに7つの予想のモデルを学習して保存する。`--year`（既定は今年）・`--timings`（既定は3つ全部） | `add_parser(subparsers)`・`run(引数)` |
| `PredictCommand` | `predict`: 1レースの展開と着順を予測し、印と印どおりの買い目を出す | `add_parser(subparsers)`・`run(引数)` |
| `BacktestCommand` | `backtest`: 年ごとの確かめ。`--years`（既定 2020-2026）・`--config`（既定は速さのための `setting/backtest_settings.toml`） | `add_parser(subparsers)`・`run(引数)` |
| `BacktestTables` | 年ごとの確かめの結果を、表1〜4 と確率の当てはまりの表と条件の表にする | `tables()` |

### repository/ — ファイルの読み書き

| クラス | 読む・書くもの | 主な public メソッド |
|---|---|---|
| `DatasetRepository` | 1頭ごと・1レースごとの学習データ（`reports/race_development/datasets/`）。作った条件（元DB の更新日時と期間）と一緒に残す | `load(名前, 条件)`・`save(名前, 条件, データ)` |
| `OutOfSampleRepository` | 前の組の「学習に使っていない予測」（`reports/race_development/out_of_sample/<組>/<時点>/<年>.pkl`）。作った条件と一緒に残す | `load(組, 時点, 年, 条件)`・`save(…)` |
| `BacktestArtifactRepository` | 年ごとの確かめの、年ごとの精算の表と、結果の表（`reports/race_development/backtest/`） | `exists`・`load`・`save`・`save_text` |
| `PredictionArchiveRepository` | 予測のたびに、予測用データ（特徴量）と予測を書き足す（`reports/race_development/predictions/<開催日>/`）。上書きしない | `save(開催日, レースID, 時点, 予測した時刻, 表)` |

途中の結果は pickle で書く（この環境には parquet の道具（pyarrow）が無いため）。学習済みモデルは `KindModelStore`（共通の `ModelRepository`）が `reports/race_development/models/<予想>/<時点>/` に書く。どれも JV-Data から作ったもので、公開しないので Git の対象外に置く。

## 4. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `race_development`（race development = レースの展開）とする。

```text
src/yosou/shared/                   ほかの予想から使う部品（上の「2.」を足す・変える）
├── betting/                        TicketType を研究から移した
├── repository/                     RaceEarlyRecordRepository を足し、確定オッズと払戻のリポジトリを研究から移した。
│                                   EntryRepository・PastRunRepository・PeopleDayRepository に列を足した
├── dataset/                        RaceResultSource を足し、RaceDatasetBuilder・TrainingData.with_label・記録を集める部品を変えた
├── feature/                        FieldFeatureGroup を足し、EntryRecords・FeatureBuilder・RaceRecords を変え、RaceConditionSummary を移した
└── …                               ほかは変えない

src/yosou/race_development/         展開（前半と後半）から着順を予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict・backtest）の引数と、結果の表
├── workflow/                       学習・予測・年ごとの確かめの流れ（ほかを順に呼ぶだけ）、7つの予想と3つの組の値、
│                                   前の組の学習に使っていない予測を作る部品、買い目を作って精算する部品
├── evaluation/                     年ごとの当たり具合
├── betting/                        印・買い目・当たる確率・精算・回収率のまとめ
├── ml_model/                       レースの中でそろえるモデル、分位点回帰・回帰のモデル、2着・3着の割り当て
├── dataset/                        行を選ぶ・目的変数を付ける・レースごとの結果を読む
├── feature/                        まとまり K〜U、S・T を足す部品、特徴量の一覧
│   └── history/                    過去の記録から数える部品（順位の物差し・基準・過去走の並べ方など）
├── repository/                     学習データ・前の組の予測・年ごとの確かめ・予測の記録のファイル
├── setting/                        ハイパーパラメータの初期値と、年ごとの確かめの設定のファイル
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `race_development` → `shared`。`shared` から予想のパッケージを参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `evaluation` → `betting` → `ml_model` → `dataset` → `feature`。`workflow` は `repository` と `setting` を使う | 手本と同じ決まりに、`betting` を足した |
| 順位の物差し（`RelativeRank`・`EarlyPosition`）と基準（`PaceBaseline`）は、目的変数（`dataset`）と特徴量（`feature`）の両方が使うので、下の `feature/history/` に置く | 参照の向き（dataset → feature）を守ったまま、1か所に置くため |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |

## 5. 選ばなかった選び方で変わるクラス

[15-decisions.md](15-decisions.md) で選ばなかった選び方にしたとき、上の一覧がどう変わるかを残しておく。

| 選び方 | 変わるクラス |
|---|---|
| 先頭を CatBoost の `QuerySoftMax` で学習する（[15 の 1](15-decisions.md#1-先頭の確率の作り方)） | `CatBoostWithinRaceModel` の中身が `CatBoostRanker` になり、温度は要らなくなる。LightGBM には同じものが無いので、`LightGbmWithinRaceModel` は今のまま残る |
| 前半タイムの秒数を出さない（[15 の 6](15-decisions.md#6-前半タイムの秒数の出し方)） | `DevelopmentModelKind.PACE_TIME` と、S の「前半タイムの基準との差の予測」「前半タイムの予測の幅」が無くなる |
| ほかの予想と共通の特徴量を使わない（[15 の 7](15-decisions.md#7-ほかの予想と共通の特徴量-71個も使うか)） | `feature_catalog.py` の一覧から A〜I が抜ける。クラスは変わらない |
| コースの形の表を作る（[15 の 8](15-decisions.md#8-コースの形の表を最初の版に入れるか)） | コースの表を読むリポジトリと、表の値を付ける特徴量のクラスが増える |
| 後半を区分で当てる（[15 の 17](15-decisions.md#17-後半で何を当てるか) の②） | ④⑤ が `MULTICLASS` になり、回帰のクラス（`RegressionModel` など）が要らなくなる |

## 作りながら変えたところ

この文書の最初の版（2026-09-26 に後半と着順を書き足したとき）から、プログラムを作りながら変えたところ。「この構成は、作りながら動かしてよい」という決まりによる。

| 最初の版 | 作ったもの | 理由 |
|---|---|---|
| 予想ごとに共通の `TrainingWorkflow`、秒数は `PaceTimeTrainingWorkflow`、回帰は `RegressionTrainingWorkflow` で学習する | `KindTrainer`・`KindForecaster`・`GroupFitter` が、4種類のモデルを同じ手順で学習・予測する | 後半と着順の学習データには年ごとに学習し直した前の組の予測が要り、1つの期間で学習する `TrainingWorkflow` の手順に合わないため。学習（train）と年ごとの確かめ（backtest）で同じ部品を使える |
| 目的変数を付けるクラスは予想ごと（`EarlyPositionLabeler`・`PaceLabeler`・`LatePaceLabeler` など） | 1頭ごとは `HorseLabeler`、1レースごとは `RaceLabeler` が、まとめて付ける（1頭ごとの中身は3つのクラスに分けた） | 共通の `DatasetBuilder`・`RaceDatasetBuilder` は、目的変数の付け方を1つだけ受け取るため |
| `RaceResultSource` は `read(記録, 最初の日)`、荒れ具合の予想は `PayoutResultSource` で包む | `read(最初の日)`。払戻のリポジトリは、そのまま決まりを守る | 今の `RaceDatasetBuilder` の呼び方のままで済み、荒れ具合の予想を包む必要が無かった |
| `EarlyPosition`・`PaceBaseline` は `dataset/` | `feature/history/` | 特徴量（K・N・Q・U）からも使い、参照の向き（dataset → feature）を守るため |
| 当たり具合は `LeaderEvaluator`・`PaceTimeEvaluator`・`RegressionEvaluator`・`FinishEvaluator`・`DevelopmentBaselines` で、学習のたびに出す | 年ごとの確かめの表（`StageYearMetrics`・`FinishYearMetrics`・`PlaceCalibration`）で出す。学習（train）は、保存したモデルの表だけを出す | 学習のモデルは年ごとの確かめの最新の年のモデルと同じ作り方なので、当たり具合は年ごとの確かめで見れば足りる |
| 精算で、不成立の券種は賭け金を返す | 不成立・特払の券種は、そのレースでは買わない（見送り） | 研究「馬券の買い方の検証」と同じ扱いにし、比べやすくするため。回収率への影響はほぼ無い |
| 途中の結果は parquet | pickle | この環境に parquet の道具（pyarrow）が無いため |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
| 更新 | 2026-09-26 後半・着順・年ごとの確かめのクラスと、`betting/` を足した。`WithinRaceLeaderModel` を `WithinRaceModel` に改名した |
| 更新 | 2026-09-26 プログラムに合わせて書き直した（「作りながら変えたところ」） |
