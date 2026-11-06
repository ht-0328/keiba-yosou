# 05 学習と予測のやりとり（シーケンス図）

**この文書で示すこと:** 学習と予測のとき、利用者・nvdata-store・元DB と、[04-classes.md](04-classes.md) のクラスが、どの順に、どのメソッドを呼ぶか。

**結論: 流れは「学習」と「予測」の2つに分かれる。** 学習は `TrainCommand` が `TrainingDataCache` に学習データを1回作らせ（2回目からは読むだけ）、券種ごとに共通の `TrainingWorkflow` を回して、3つの時点ごとに多クラス分類の LightGBM と CatBoost を学習させて保存する。予測は `LocalUpsetForecast` が進め、まずそのレースの当日の馬場傾向のレースの値（U）を出し、それを渡した `RaceDatasetBuilder` と中央の `PredictionWorkflow` で券種ごとの4つの確率を出す。中央の荒れ具合の予想と違うのは、学習データに U を付けてとっておくこと、予測の前に U を出すこと、推奨買目から呼ばれることである。

- 図に出てくるものと図の読み方（凡例）は [地方の全頭の予想の 05 の「図に出てくるもの」](../地方競馬の近走と適性から3着以内を予想/05-sequence.md#図に出てくるもの) と [手本の 05 の「図の読み方」](../近走と適性から3着以内を予想/05-sequence.md#図の読み方) を参照。この予想で増えるのは、`TrainingDataCache`・`LocalBiasHistory`・`RaceUsedSlopes`・`PriorSlopeYearStore`・`LocalUpsetForecast`・`UpsetProbabilities`（道具「地方の推奨買目」）である。
- 1頭ごとの特徴量をレース単位に集約するやりとり、記録を集めるやりとり、予測に使うオッズの決め方は中央と同じで、[中央の荒れ具合の 05 の図3](../レースの荒れ具合を4段階で予想/05-sequence.md#図3-1頭ごとの特徴量をレース単位に集約する)・[手本の 05 の図3・図4](../近走と適性から3着以内を予想/05-sequence.md#図3-記録を集めるリポジトリとのやりとり)・[手本の 06 の図2](../近走と適性から3着以内を予想/06-flowchart.md#図2-予測に使うオッズの決め方) を参照。
- public メソッドの中の判断（if 文による分かれ道）は [06-flowchart.md](06-flowchart.md) を参照。2種類の図の使い分けは [01-overview.md](01-overview.md#図の使い分け) を参照。

## 図1. 学習

```mermaid
sequenceDiagram
    actor U as 利用者
    participant TC as TrainCommand
    participant CA as TrainingDataCache
    participant DB as 元DB
    participant BR as BiasRunRepository
    participant BH as LocalBiasHistory
    participant D as RaceDatasetBuilder
    participant F as pickle のファイル
    participant W as TrainingWorkflow
    participant MR as ModelRepository
    U->>TC: train（期間、券種、設定ファイルのパス、--cache、--rebuild）
    TC->>CA: load_or_build（元DB を開く関数、期間）
    alt とっておいたファイルがある（--rebuild でない）
        CA->>F: 読む（学習データ-<ウォームアップの始まり>-<学習データの始まり>.pkl）
        F-->>CA: 学習データ
    else 無い
        CA->>BR: read（ウォームアップの始まり。既定は 2016年1月1日）
        BR->>DB: SQL（地方・平地の全出走: 馬番・頭数・4コーナーの順位・単勝オッズ・着順）
        BR-->>CA: 出走の表
        CA->>BH: of（当日、出走の表）
        BH->>BH: レースごとの傾きを出し、年ごとに「その年より前のレースだけの過去の傾きの表」と先に終わったレースの傾きで U を付ける（11 の 11）
        BH-->>CA: 1行 = 1頭の U の表
        CA->>CA: race_slopes_table（レースごとの使う内の傾き・使う前の傾き）
        CA->>D: build_training_data（期間）（local_race_dataset_builder で組み立てたもの。UsedSlopeFeatures にレースごとの表を渡す）
        D->>D: 記録を集め、レースを選び、払戻を読み、A〜E と U を作り、地方の線引きで4クラスを付ける（中央の 05 の図1）
        D-->>CA: 学習データ（1行 = 1レース。特徴量 51個、目的変数 4列）
        CA->>F: 書く
    end
    CA-->>TC: 学習データ
    loop 4つの券種（単勝・馬連・3連複・3連単）ごと
        TC->>W: train（学習データ.with_label（券種の列）、設定ファイルのパス）
        loop 3つの時点（出馬表・前日・当日）ごと
            W->>W: その時点の列だけで LightGbmMulticlassModel と CatBoostMulticlassModel を学習させる（12・13）
            W->>MR: save（時点、2つのモデル、設定）
            MR-->>W: 保存した（reports/地方のレースの荒れ具合を4段階で予想/models/<券種>/<時点>/）
        end
        W-->>TC: その券種の学習の結果
        TC->>TC: 検証データで、しきい値ごとの数え上げを作る（UpsetThresholdTable。16 の 4）
    end
    TC-->>U: 券種ごとの学習の結果の表
```

**説明。** 利用者が `train` を実行する。`TrainCommand` は、まず `TrainingDataCache` に学習データを求める。とっておいたファイルがあればそれを読み、無ければ元DB から作る。作るときは、地方・平地の全出走を読み（`BiasRunRepository`）、`LocalBiasHistory` でリークを防ぐ決まり（年ごとの過去の傾きの表と、先に終わったレースの傾き）で U を付け、レースごとの使う傾きの表（`race_slopes_table`）にして `UsedSlopeFeatures` に渡す。学習データそのものは、中央の荒れ具合の予想と同じ `RaceDatasetBuilder` が作る（1頭ごとの記録を集める → レースを選ぶ → 払戻を読む → レース単位の特徴量 51個 → 地方の線引きで荒れ具合 4列）。元DB を開くのはこの段だけで、学習のあいだはロックを持たない。

学習は券種ごとに共通の `TrainingWorkflow` を1回ずつ回す（中央と同じ。多クラス用のモデルの並び `CLASS_MEMBER_TYPES` と評価 `ClassModelEvaluator` を渡す）。出馬表・前日のモデルには、その時点で使う列だけを渡す（[07-prediction-timing.md](07-prediction-timing.md#時点ごとに使う特徴量)）。U は当日から分かる列なので、当日のモデルだけに渡る。

## 図2. 予測

発走前（か終わったあと）に、1レースの券種ごとの荒れ具合を出すときの流れ。`predict` コマンドと、道具「地方の推奨買目」の両方が `LocalUpsetForecast` を呼ぶ。

```mermaid
sequenceDiagram
    actor U as 利用者
    participant NS as nvdata-store
    participant DB as 元DB
    participant R as Recommender（地方の推奨買目）
    participant UP as UpsetProbabilities
    participant LF as LocalUpsetForecast
    participant RU as RaceUsedSlopes
    participant PS as PriorSlopeYearStore
    participant BR as BiasRunRepository
    participant W as PredictionWorkflow
    participant D as RaceDatasetBuilder
    participant MR as ModelRepository
    participant E as EnsembleModel
    U->>NS: nvstore sync（出馬表 RACE・出走別着度数地方 SNAP・マスタ DIFN）
    NS->>DB: 書き込む
    opt 前日と当日だけ
        U->>NS: nvstore realtime（開催日。出馬表の更新と当日の成績 0B15・天候馬場 0B14・馬体重 0B11、そのレースの全賭式のオッズ 0B30）
        NS->>DB: 馬場状態・馬体重・先に終わったレースの結果・締め切り前のオッズを書き込む
    end
    alt predict コマンド
        U->>LF: run（接続、レースID、時点、--odds で渡したオッズ、--bet の券種）
    else 発走前の通知の推奨買目（当日の時点）
        R->>UP: of（接続、レースID、荒れ具合の条件のある券種）
        UP->>LF: upset_or_more（接続、レースID、当日、券種）
    end
    LF->>RU: of（レースID、時点）
    RU->>DB: SQL（そのレースの鍵と条件。RaceEntryRepository）
    RU->>PS: load（接続、その年の1月1日）
    alt とっておいた表がある（同じ元DB）
        PS->>PS: 読む（cache/過去の傾き-<年の始まり>.pkl）
    else 無い
        PS->>BR: read（全部）
        BR->>DB: SQL（地方・平地の全出走）
        PS->>PS: レースごとの傾きを出し、年の始まりより前のレースだけで過去の傾きの表を作って書く
    end
    PS-->>RU: 過去の傾きの表
    RU->>BR: read（開催日の前の日から）
    BR->>DB: SQL（開催日とその前の日の終わったレースの出走）
    BR-->>RU: 出走の表（2日ぶん）
    RU->>RU: 終わったレースの傾き → 当日の傾き（DaySlopes。時点で数え方が変わる）→ 使う傾き（UsedSlopes）
    RU-->>LF: 使う内の傾き・使う前の傾き（1行）
    LF->>W: run（レースID、時点、渡されたオッズ、券種）（local_race_dataset_builder に1行の表を渡して組み立てたもの）
    W->>W: 使うオッズを決める（手本の 06 の図2）
    W->>D: build_prediction_data（レースID、時点、オッズ）
    D->>D: 記録を集め、払戻（前日までの 365日）を読み、A〜E と U を作り、要る情報を確かめる（中央の 05 の図2・06 の図2）
    D-->>W: 予測用データ（1行 = 1レース）
    loop 券種ごと
        W->>MR: load（時点）
        MR-->>W: その券種・その時点の 2つのモデル
        W->>E: predict_proba（予測用データ）
        E-->>W: 4つの確率（2つのモデルの平均）
    end
    W-->>LF: 券種 × 固い・中荒れ・大荒れ・超荒れ・いちばん高いクラス・中荒れ以上の確率
    alt predict コマンド
        LF-->>U: 荒れ具合の表（RacePredictionTable。時点は 出馬表・前日・当日 と出す）
    else 推奨買目
        LF-->>UP: 表
        UP-->>R: 券種 → 中荒れ以上の確率
        R->>R: 3連複を買うかを決める（06-flowchart.md の図1）
    end
```

**説明。** 利用者（か発走前の通知）は、まず nvdata-store で出馬表と速報を取り込む。当日の速報 0B15 には、その日に先に終わったレースの結果（着順・4コーナーの順位）が入るので、取り込んでおくと当日の馬場傾向にその日のレースが数えられる（取り込んでいなければ、前の日のレースと過去の傾きだけで出す）。

`LocalUpsetForecast.run()` は、まず `RaceUsedSlopes` にそのレースの U のレースの値を出させる。過去の傾きの表は `PriorSlopeYearStore` が年ごとにとっておいたもの（その年の1月1日より前のレースだけで作る。学習データと同じ決めごと）、当日の傾きは開催日とその前の日の終わったレースの傾きだけを毎回数える（2日ぶんなので速い）。次に、その1行の表を `UsedSlopeFeatures` に渡して組み立てた `RaceDatasetBuilder` と、中央と同じ `PredictionWorkflow` で予測する。オッズの決め方・記録の集め方・要る情報の確かめ方・券種ごとのモデルの読み方は中央の荒れ具合の予想と同じである。

道具「地方の推奨買目」の `Recommender` は、荒れ具合の条件のある券種（3連複）があるときだけ、`UpsetProbabilities` を通して `upset_or_more()` を当日の時点で呼ぶ。モデルが無い・馬体重がまだ無い、などで出せなければ、`Recommender` は 3連複だけを対象外にして理由を添える（[06-flowchart.md の図1](06-flowchart.md#図1-推奨買目が-3連複を買うかどうかの判断)）。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-06 |
