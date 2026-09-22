# 04 クラスとパッケージの設計

**この文書で決めること:** 「1行 = 1レース」「4クラス」「券種ごとのモデル」を、手本の予想と共通の部品（`src/yosou/shared/`）の上にどう載せるか。共通の部品に何を足し、何を変えるか。この予想だけに要るクラスは何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: 記録を集める・1頭ごとの特徴量を作る・設定を読む・モデルを保存する、のクラスは共通のものをそのまま使う。共通の部品に足すのは、①1頭ごとの特徴量をレース単位に集約して学習データを作る `RaceDatasetBuilder`・`RaceFeatureBuilder`、②4列の確率を返す多クラス分類のモデル（`LightGbmMulticlassModel`・`CatBoostMulticlassModel`）とその決まり `ClassProbabilityModel`、③払戻とレースの結果を読む2つのリポジトリ、④4クラスの当たり具合を測るクラス、である。変えるのは、`EnsembleModel` の平均の1行と、`TrainingWorkflow`・`TrainingData`・`RequiredInfoCheck` に差し替え口を足すところだけである。手本の予想だけが持つオッズの部品（`MarketFeatures`・`OddsInput`・`OddsResolver`）は `shared` に移す。この予想だけに作るのは、レースを選ぶ・荒れ具合を付ける・まとまり A〜E を集約する・券種ごとにモデルを回す、のクラスとコマンドである。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共通のクラスの一覧（どのクラスが何をするか）は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。この文書には、足すもの・変えるもの・この予想だけのものを書く。
- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ・エンコーダー）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を、集約・多クラス分類は [02-glossary.md](02-glossary.md) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. レース単位の学習データを作る仕組み

手本の `DatasetBuilder` は「記録を集める → 行（1頭）を選ぶ → 1頭ごとの特徴量を作る → 残す行を決める → 目的変数を付ける」の順で、1行 = 1頭の学習データを作る。この予想は 1行 = 1レースなので、次の3つのどれかにする必要がある。

| 置き方 | 変わるもの | 評価 |
|---|---|---|
| **(i) `RaceDatasetBuilder` を `DatasetBuilder` の隣に新設し、1頭ごとの `FeatureBuilder` の出力を `RaceFeatureBuilder` がレース単位に集約する** | 既存の `DatasetBuilder`・`FeatureBuilder`・記録を集めるクラスは無変更 | **採用**（[15-decisions.md](15-decisions.md#11-共通部品の置き方)） |
| (ii) `SampleSelector.keep_samples()` で集約する | ― | 不可。`keep_samples()` は出走の行しか受け取らず、特徴量を見られない |
| (iii) `DatasetBuilder` に「行をまとめる部品」を差し込む | `DatasetBuilder` の ID 列・評価用の列（1頭前提の定数）も差し替え式にする | 3つの予想が使う入口を触るので避ける |

(i) の流れ（`RaceDatasetBuilder.build_training_data(期間)`。図は [05-sequence.md](05-sequence.md#図1-学習)）:

1. 共通の `HistoryRecordsLoader.load(ウォームアップの始まり)` で、1頭ごとの記録を集める（手本と同じ）。
2. `RaceSelector.training_samples(出走の行, 学習データの始まり)` で、平地・出走馬・期間内の全頭を残す。行は減らさない。
3. `RaceFeatureBuilder.build(記録, 当日)` が、中で共通の `FeatureBuilder.build(記録, 当日)` を呼んで1頭ごとの特徴量（手本の A〜J と、人気馬の J）を作り、まとまり A〜E の `RaceFeatureGroup` を順に呼んで、レースIDごとに集約する（[05-sequence.md](05-sequence.md#図3-1頭ごとの特徴量をレース単位に集約する)）。
4. `RacePayoutRepository.read(対象)`・`RaceResultRepository.read(対象)` で、払戻と結果を 1行 = 1レースで読み、レースIDで結合する。
5. `UpsetLevelLabeler.build(レースの行)` で、券種ごとの荒れ具合（4列）を付ける。
6. `TrainingData`（ID 列・特徴量・目的変数 4列・評価用の列・特徴量の一覧・クラスの並び 0〜3）を返す。

予測（`build_prediction_data(レースID, 時点, オッズ)`）は、共通の `RaceRecordsLoader.load(レースID, オッズ)` から同じ 2〜3 を通り、`RequiredInfoCheck` にレース用の案内を渡して、1行の予測用データを返す。**時点で列を絞るのは、レース単位の特徴量の一覧（`columns_for(時点)`）だけで行う。** 1頭ごとの特徴量を先に絞ると、D の「1番人気の馬体重の増減」を作る段で元の列が無くなるためである。

## 2. 共通の部品に足すもの・変えるもの

| 置き場所 | 種類 | 部品 | 仕事・主な public メソッド | 備考 |
|---|---|---|---|---|
| `shared/ml_model/` | 追加 | `ClassProbabilityModel`（インターフェース） | `from_settings(設定, クラスの数)`・`fit(学習データ, 検証データ)`・`predict_proba(データ)`（行数 × クラスの数）・`tree_count`・`save(パス)`・`load(パス, 設定)` | `ProbabilityModel` と同じ名前の並び。戻り値の形だけ違う |
| `shared/ml_model/` | 追加 | `LightGbmMulticlassModel` | `objective="multiclass"`、`num_class` はクラスの数。エンコーダーは共通の `LightGbmEncoder` | [12-lightgbm.md](12-lightgbm.md) |
| `shared/ml_model/` | 追加 | `CatBoostMulticlassModel` | `loss_function="MultiClass"`。エンコーダーは共通の `CatBoostEncoder` | [13-catboost.md](13-catboost.md) |
| `shared/ml_model/` | 追加 | `class_member_types.py` の `CLASS_MEMBER_TYPES` | 上の2つの並び | 二値分類の `MEMBER_TYPES` と同じ役 |
| `shared/ml_model/` | **変更** | `EnsembleModel.combine()` | 確率を重ねて平均するところを、1列でも 4列でも平均できる形（`np.stack(…, axis=0).mean(axis=0)`）にする | 今の `np.vstack` は 4列の表を縦につないでしまう。既存3予想の結果は変わらない（[03-library-basics.md](03-library-basics.md#この予想で違う点)） |
| `shared/dataset/` | 追加 | `RaceDatasetBuilder` | `build_training_data(期間)`・`build_prediction_data(レースID, 時点, オッズ=省略可)` | 上の「1.」 |
| `shared/dataset/` | 追加 | `RaceTargetLabeler`（インターフェース） | `label_names`（目的変数の列名の並び）・`build(レースの行)` | 1頭用の `TargetLabeler` は列名が1つなので、レース用を別に作る |
| `shared/dataset/` | **変更** | `TrainingData` | `class_labels`（既定 `(0, 1)`）を足す。`with_label(列名)` で、目的変数にする列を持ち替えた複製を返す | 多クラスの `num_class` と、券種ごとの学習に使う。既定値付きなので、既存3予想は変えない |
| `shared/dataset/` | **変更** | `RequiredInfoCheck` | 作られるときに、足りない情報ごとの案内文を受け取れるようにする（既定は今の4つ） | レース単位では「全頭の単勝オッズ」の案内になる |
| `shared/feature/` | 追加 | `RaceFeatureGroup`（インターフェース） | `build(出走の行, 1頭ごとの特徴量)` → 1行 = 1レースの表 | まとまり A〜E が守る |
| `shared/feature/` | 追加 | `RaceFeatureBuilder` | `build(記録, 時点)`。中で `FeatureBuilder.build(記録, 当日)` を呼び、まとまりごとに集約し、レース用の `FeatureCatalog.columns_for(時点)` で列を絞る | 上の「1.」 |
| `shared/feature/history/` | 追加 | `ConditionUpsetRate` | `of(日ごとの表)`。条件の鍵 × 券種ごとに、前日までの 365日の中荒れ以上の割合 | 共通の `Top3Rate`（日ごとの累計を `AsOfLookup.latest(days_before=1)` で引く）と同じ作り。鍵と分子を替えるだけ |
| `shared/repository/` | 追加 | `RacePayoutRepository` | `read(対象)`。`hr` のフラグと4券種の払戻（同着は最大）・払戻の人気順を、1行 = 1レースで読む。1つの SQL | 目的変数と E と評価用の列の元 |
| `shared/repository/` | 追加 | `RaceResultRepository` | `read(対象)`。事実表から、勝ち馬の人気・1〜3着の人気の和・1番人気の確定着順と確定オッズ・確定の出走頭数を、1行 = 1レースで読む | 評価用の列 |
| `shared/evaluation/` | 追加 | `ClassMetricCalculator` | `accuracy`・`macro_f1`・`confusion_matrix`・`mean_class_gap`・`log_loss`・`cumulative_auc(境のクラス)` | [16-evaluation.md](16-evaluation.md#2-評価指標)。二値用の `MetricCalculator` は、複勝の払戻の列を必ず読むので使えない |
| `shared/evaluation/` | 追加 | `ClassEvaluation`・`ClassModelEvaluator` | 1つの時点・1つのモデルの当たり具合の値／`evaluate(時点, アンサンブル, データ)` | |
| `shared/command/` | 追加 | `ClassTrainingReportTables`・`RacePredictionTable` | `tables()`／`table()`。期間ごとのクラスの割合と 4クラスの指標の表／「券種 × 4つの確率・いちばん高いクラス・中荒れ以上の確率」の表 | 二値用の `TrainingReportTables` は目的変数の平均を出すので使えない |
| `shared/workflow/` | **変更** | `TrainingWorkflow` | 作られるときに `member_types`（既定は二値の `MEMBER_TYPES`）と `evaluator`（既定は `ModelEvaluator`）を受け取れるようにする | 「どの予想か」の if 文を書かずに差し替える。券種ごとの学習は、この予想の `TrainCommand` が `with_label()` で列を持ち替えて `train()` を券種の数だけ呼ぶ |
| `form_aptitude_top3` → `shared/feature/group/`・`shared/dataset/` | **移す** | `MarketFeatures`・`OddsInput`・`OddsResolver` | まとまり B・D の材料（単勝オッズ・人気順位・オッズから見た勝率）と、`--odds` の受け取り・予測に使うオッズの決め方 | 穴馬の予想が人気の部品を移したのと同じやり方（[穴馬の 04](../穴馬が3着以内に入るかを予想/04-classes.md#1-共通の部品とこの予想だけの部品の分け方)）。手本の予想も、移したあとの形に直す |

**共通のクラスが、予想ごとの違いを知らずに済むようにする。** そのために、`shared` のインターフェースを、この予想のクラスが守る。

| インターフェース（`shared` にある） | 決まり（public メソッド） | この予想で守るクラス |
|---|---|---|
| `SampleSelector` | `training_samples`・`prediction_runners`・`keep_samples` | `RaceSelector` |
| `RaceTargetLabeler`（新設） | `label_names`・`build` | `UpsetLevelLabeler` |
| `RaceFeatureGroup`（新設） | `build(出走の行, 1頭ごとの特徴量)` | `RaceConditionSummary`・`OddsShapeFeatures`・`FieldStrengthSpreadFeatures`・`FavoriteRiskFeatures`・`ConditionUpsetRateFeatures` |
| `ClassProbabilityModel`（新設） | `fit`・`predict_proba`・`save`・`load` | 共通の `LightGbmMulticlassModel`・`CatBoostMulticlassModel` をそのまま使う |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない。予想のパッケージどうしも参照しない | 手本と同じ。片方の予想の都合が、もう片方に入り込まない |
| 1頭ごとの特徴量は、共通の `FeatureBuilder` で作り、この予想では書き直さない | 学習と予測で、集約する元の値が手本の予想と同じになる。直す場所が1か所で済む |
| 荒れ具合の線引きは `UpsetLevelRule` の1か所で持ち、目的変数（`UpsetLevelLabeler`）と E（`ConditionUpsetRate`）の両方がそれを使う | 線引きを変えたとき、目的変数と特徴量が食い違わない |
| 券種は、モデルと保存先を分けるだけで、学習データと特徴量は分けない | 特徴量は券種によらず同じ。学習データを4回作らない |
| 学習データ・予測用データは、同じ `RaceDatasetBuilder` と `RaceFeatureBuilder` で作る | 学習と予測で、特徴量の中身がずれないようにする（[11-leak-prevention.md](11-leak-prevention.md#決まり) の 4） |

## 3. この予想だけのクラスの一覧

### dataset/ — レースを選ぶ・荒れ具合を付ける

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `RaceSelector` | 学習データ・予測用データに入れる行を選ぶ。平地・出走馬・期間内の全頭を残し、行は減らさない（[06-flowchart.md](06-flowchart.md#図1-学習データに入れるレースの選び方と4クラスの付け方)）。`keep_samples` はそのまま返す | `training_samples(出走の行, 学習データの始まり)`・`prediction_runners(出走の行, レースID)`・`keep_samples(特徴量の付いた行)` | 共通の `FlatRunnerFilter` |
| `BetType` | 券種を表す値（列挙。単勝・馬連・3連複・3連単）。`--bet` の文字を読む。目的変数の列名（「荒れ具合（単勝）」など）と保存先のフォルダ名を持つ | `label`・`column_name`・`parse(書き方)`・`all()` | ― |
| `UpsetLevel` | 荒れ具合を表す値（列挙。固い = 0、中荒れ = 1、大荒れ = 2、超荒れ = 3） | `label`・`value` | ― |
| `UpsetLevelRule` | 券種ごとの線引き（3つの額）を持つ値。**線引きの唯一の置き場所**（[10-target.md](10-target.md#券種ごとの線引き)） | `level_of(券種, 払戻)`・`levels_of(券種, 払戻の列)`・`is_upset_or_more(券種, 払戻)` | `UpsetLevel` |
| `UpsetLevelLabeler` | 払戻の列から、券種ごとの荒れ具合（4列）を付ける。発売なし・不成立・特払は欠損値、同着は最大の払戻（[10-target.md](10-target.md#作り方)） | `label_names`・`build(レースの行)` | `UpsetLevelRule`・`BetType` |
| `race_column_names.py` の定数 | 目的変数・評価用の列の名前（「荒れ具合（単勝）」「3連単の払戻」「1番人気の確定着順」「利用者の規則に当てはまるか」など） | ―（値） | ― |
| `dataset_assembly.py` の `race_dataset_builder()` | この予想の部品（`RaceSelector`・`UpsetLevelLabeler`・`CATALOG`・まとまり A〜E）を渡して、共通の `RaceDatasetBuilder` を組み立てる | `race_dataset_builder(接続)` | 上のクラスと共通の `RaceDatasetBuilder` |

### feature/ — まとまり A〜E を集約する

どれも `RaceFeatureGroup` を守り、1頭ごとの特徴量の表（共通の `FeatureBuilder` の出力）と出走の行を受け取って、1行 = 1レースの表を返す。

| クラス | まとまり | 集約のしかた | 呼ぶクラス |
|---|---|---|---|
| `RaceConditionSummary` | A（11個） | レースの1頭目の値をそのまま。特別戦か・ハンデ戦かは出走の行から作る | ― |
| `OddsShapeFeatures` | B（10個） | 単勝オッズと市場勝率を、小さい順の N 番目・最大・数・合計・エントロピーに集約 | ― |
| `FieldStrengthSpreadFeatures` | C（10個） | 近走・前走・騎手の値を、差・標準偏差・中央値・割合・数に集約 | ― |
| `FavoriteRiskFeatures` | D（10個） | 単勝オッズが最小の馬の値を取り出す。オッズが無ければ全部欠損値 | ― |
| `ConditionUpsetRateFeatures` | E（8個） | 条件の鍵（競馬場・芝ダ・距離帯、クラス）ごとに、前日までの 365日の中荒れ以上の割合を付ける | 共通の `ConditionUpsetRate`・`UpsetLevelRule`・`RacePayoutRepository` の結果 |
| `feature_catalog.py` の `RACE_FEATURES`・`CATALOG` | ― | この予想の特徴量の一覧（`Feature(名前, まとまり, 型, いつから分かるか)` × 49）。[09-features.md](09-features.md) の表の写し | 共通の `FeatureCatalog` |

### evaluation/ — 比べる基準

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `UserRuleBaseline` | 利用者の規則（1番人気 4.0倍以上かつ 2〜5番人気の最大 10倍未満）を「中荒れ以上」の予想とみなして、的中率と再現率を出す（[16-evaluation.md](16-evaluation.md#3-比べる基準)） | `evaluate(データ)` |

### workflow/ — 流れを進める

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PredictionWorkflow` | 予測の流れを進める。オッズを決め、予測用データ（1行）を作り、券種ごとにその時点のモデルを読み込み、4つの確率を平均し、券種 × 4確率の表にする | `run(レースID, 時点, 渡されたオッズ=省略可, 券種=省略可)` | 共通の `OddsResolver`・`RaceDatasetBuilder`・`ModelRepository`・`EnsembleModel`、`BetType` |
| `prediction_timings.py` の `TIMINGS` | この予想が学習し、予測を出す時点（木曜・前日・当日）の並び | ―（値） | ― |

`PredictionWorkflow` は、ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない。**学習の流れ（`TrainingWorkflow`）は共通のものを使う。** 券種ごとに回すのは `TrainCommand` で、学習データを1回読み（`read_training_data()`）、券種ごとに `with_label(列名)` で目的変数を持ち替え、その券種の保存先を持つ `ModelRepository` を渡して `train()` を呼ぶ。

### command/ — コマンド

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `CommandLine` | この予想 | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | この予想 | `train`: 学習する。期間の引数から `TrainingPeriod` を作る。`--bet` で券種を絞れる（既定は4つ全部）。学習データを1回作り、券種 × 時点のモデルを学習する | `add_parser(subparsers)`・`run(引数)` |
| `PredictCommand` | この予想 | `predict`: 1レースの荒れ具合を予測する。`--odds 馬番:オッズ` で全頭の単勝オッズを受け取って `OddsInput` にし、`--bet` を `BetType` にする | `add_parser(subparsers)`・`run(引数)` |
| `CommonArguments` | `shared` | 2つのサブコマンドに共通の引数（`--models` `--db` `--format` `--out`） | `add_to(parser)` |
| `ClassTrainingReportTables`・`RacePredictionTable` | `shared` | 上の「2.」 | `tables()`・`table()` |

## 4. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `upset_level`（upset = 荒れ、level = 段階）とする。

```text
src/yosou/shared/                   4つの予想から使う部品
├── repository/                     データの読み書き。1 SQL につき 1 リポジトリ（払戻とレースの結果を読むものを足す）
├── dataset/                        学習データ・予測用データを作る（レース単位に作る RaceDatasetBuilder、オッズの部品を足す）
├── feature/                        1頭ごとの特徴量（まとまり A〜J。市場の評価を含む）と、レース単位に集約する RaceFeatureBuilder
│   ├── group/                      1頭ごとのまとまりごとに1クラス（MarketFeatures を足す）
│   └── history/                    過去の記録から数える部品（ConditionUpsetRate を足す）
├── ml_model/                       LightGBM・CatBoost（二値と多クラス）・エンコーダー・平均
├── setting/                        設定ファイルを読む
├── evaluation/                     当たり具合を測る（二値用と多クラス用）
├── workflow/                       学習の流れ（TrainingWorkflow）
├── command/                        コマンドの部品のうち、予想に依らないもの
└── tests/                          共通の部品のテストと、テスト用の合成のシーズン

src/yosou/upset_level/              レースの荒れ具合を4段階で予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict）の引数
├── workflow/                       予測の流れ（ほかを順に呼ぶだけ）と、予測を出す時点
├── dataset/                        レースを選ぶ・券種・荒れ具合・線引き・目的変数を付ける
├── feature/                        まとまり A〜E を集約するクラスと、この予想の特徴量の一覧
├── evaluation/                     利用者の規則の基準
├── setting/                        ハイパーパラメータの初期値のファイル
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`UpsetLevelRule` → `upset_level_rule.py`）。学習したモデルは、Git の対象外の `reports/upset_level/models/<券種>/<時点>/` に保存する（券種ごとに `ModelRepository` を1つ作り、置き場所を変える。`ModelRepository` は変えない）。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `upset_level` → `shared`。`shared` から予想のパッケージを参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `evaluation` → `dataset` → `feature` | 手本と同じ決まり |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 5. 選ばなかった選び方で変わるクラス

[15-decisions.md](15-decisions.md) で選ばなかった選び方にしたとき、上の一覧がどう変わるかを残しておく。

| 選び方 | 変わるクラス |
|---|---|
| 二値分類3つの積み重ね（[15 の 3](15-decisions.md#3-目的変数の載せ方)） | 多クラスのモデル2つと `ClassProbabilityModel` は要らず、共通の `LightGbmModel`・`CatBoostModel` を使う。`UpsetLevelLabeler` が券種 × 3つの境（中荒れ以上・大荒れ以上・超荒れ）の 12列を付け、`TrainCommand` が 12回 `train()` を回す。`PredictionWorkflow` に、3つの累積確率の差から4つの確率を作り、負の値を丸めるクラスが増える |
| 対数払戻の回帰（同上） | 回帰用のモデル2つと、その決まり・評価のクラスが新しく要る。`UpsetLevelLabeler` は払戻の対数を付け、`PredictionWorkflow` に、予測した対数払戻を線引きでクラスに直すクラスが増える |
| 3連単だけのモデル（[15 の 6](15-decisions.md#6-券種ごとに別のモデルにするか)） | `TrainCommand` が `train()` を1回だけ呼ぶ。`BetType` は残し、ほかの券種の列は評価用の列になる。`PredictionWorkflow` は1券種の表を返す |
| E の鍵を増やす（[15 の 8](15-decisions.md#8-過去の荒れ率の鍵と券種の数)） | `ConditionUpsetRateFeatures` に鍵を足し、`CATALOG` の E の個数を増やす。クラスは増えない |
| 利用者の規則を特徴量に入れる（[15 の 9](15-decisions.md#9-利用者の規則を特徴量に入れるか)） | `OddsShapeFeatures` に 1/0 の列を1つ足し、`CATALOG` を 50個にする |
| 券種ごとにハイパーパラメータを変える（[15 の 14](15-decisions.md#14-券種ごとにハイパーパラメータを変えられるようにするか)） | 共通の `HyperparameterSettings` に、券種の表を重ねる段（`SettingsOverlay` の呼び出しが1段増える）を足す |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-23 |
