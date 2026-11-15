# 05 学習と予測のやりとり（シーケンス図）

**この文書で示すこと:** 学習と予測のとき、利用者・jvdata-store・元DB と、[04-classes.md](04-classes.md) のクラスが、どの順に、どのメソッドを呼ぶか。

**結論: 流れは「学習」と「予測」の2つに分かれ、手本の予想とほぼ同じである。** 学習は共通の `TrainingWorkflow` が進め、時点ごと・目的変数ごとに LightGBM と CatBoost を学習させて保存する。手本と違うのは、学習データに行の重み（`GradedRaceWeighter`）が付き、2つのモデルが重みを使って学ぶことと、記録を集めるときに重賞の材料を読む呼び出しが2つ増えること（図3）である。予測は `GradedRacePrediction` が組み立てた共通の `PredictionWorkflow` が進め、重賞でないレースはそこで止まる。

- 図に出てくるものと、図の読み方（凡例）は [手本の 05 の「図に出てくるもの」](../近走と適性から3着以内を予想/05-sequence.md#図に出てくるもの) と [「図の読み方」](../近走と適性から3着以内を予想/05-sequence.md#図の読み方) を参照。この予想で増えるのは、`GradedRaceWeighter`・`GradedRunnerSelector`・`GradedRaceFeatures`・`GradedRacePrediction`・`GradedCareerRepository` と、引退した予想から共通に移す `StakesTendencyRepository`・`StakesTendencyFeatures` である。
- public メソッドの中の判断（if 文による分かれ道）は [06-flowchart.md](06-flowchart.md) を参照。2種類の図の使い分けは [01-overview.md の「図の使い分け」](01-overview.md#図の使い分け) を参照。
- **リポジトリとのやりとりは、手本とほぼ同じである。** 学習データを集める流れは [手本の 05 の図3](../近走と適性から3着以内を予想/05-sequence.md#図3-記録を集めるリポジトリとのやりとり)、1レースの記録を集めて速報を反映する流れは [手本の 05 の図4](../近走と適性から3着以内を予想/05-sequence.md#図4-1レースの記録を集める速報の反映) を参照。この予想では、その並びの最後に、この文書の図3の呼び出しが2つ増える。

## 図1. 学習

1つの材料・1つの目的変数の学習。`train` は、手本と同じく、材料（馬の力の材料と今の材料）ごと・目的変数（3着以内と1着）ごとにこの流れを動かす。

```mermaid
sequenceDiagram
    actor U as 利用者
    participant C as TrainCommand
    participant GS as GradedWeightSettings
    participant W as TrainingWorkflow
    participant D as DatasetBuilder
    participant L as HistoryRecordsLoader
    participant RS as GradedRunnerSelector
    participant F as FeatureBuilder
    participant T as Top3TargetBuilder
    participant GW as GradedRaceWeighter
    participant S as PeriodSplitter
    participant MR as ModelRepository
    participant VT as GradedValidationTables
    U->>C: train（--config、期間の引数）
    C->>GS: load（設定ファイルのパス、初期値のファイル）
    GS-->>C: 重賞の行の重み（初期値 5）
    C->>W: read_training_data()
    W->>D: build_training_data（期間）
    D->>L: load（ウォームアップの始まり）
    L->>L: リポジトリを順に呼んで記録を集める（手本の 05 の図3 と、この文書の図3）
    L-->>D: 出走の記録（graded_career・stakes_tendency の表付き）
    D->>RS: training_samples（出走の行、学習データの始まり）
    RS-->>D: サンプルにする行（平地の全頭。手本と同じ）
    D->>F: build（記録、当日）
    F->>F: GradedRaceFeatures が W の14個、StakesTendencyFeatures が K の51個を作る（09-features.md）
    F-->>D: 特徴量
    D->>T: build（サンプルにする行）
    T-->>D: 目的変数（3着以内と1着の列）
    D->>GW: weights（サンプルにする行）
    GW->>GW: 重賞の行は重み、ほかは 1（06-flowchart.md の図1）
    GW-->>D: 行ごとの重み
    D-->>W: 学習データ（重み付き）
    W-->>C: 学習データ
    C->>C: 元DB を閉じる
    C->>W: train（学習データ、設定ファイルのパス）
    W->>S: split（学習データ）
    S-->>W: 学習・検証・テストのデータ（重みも同じ行で分ける）
    loop 学習する時点ごと（今の材料は当日、馬の力の材料は木曜・前日）
        W->>W: LightGbmModel を作り、その時点の列と重みで学習させる（12-lightgbm.md の 1.）
        W->>W: CatBoostModel も同じように学習させる（13-catboost.md の 1.）
        W->>MR: save（時点、2つのモデル、設定）
        MR-->>W: 保存した
    end
    W->>W: 検証データの全行で当たり具合を確かめる（手本と同じ）
    W-->>C: 学習の結果
    C->>VT: tables（学習の結果）
    VT-->>C: 検証データのうち重賞の行だけの当たり具合
    C-->>U: 学習の結果と、重賞の行だけの当たり具合
```

**説明。** 利用者が `train` を実行すると、`TrainCommand` はまず `GradedWeightSettings` で重賞の行の重みを読み（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)）、組み立ての関数（`graded_race_assembly.py`）に渡して `DatasetBuilder` を作る。学習データを作る順（記録を集める・入れる行を選ぶ・特徴量を作る・目的変数を付ける）は手本と同じで、最後に `GradedRaceWeighter` が行ごとの重みを付ける段が増える。入れる行は手本と同じく中央の平地の全頭で、重賞の行だけに重みが付く（[08-training-data.md](08-training-data.md)）。

手本と同じところ: 元DB は学習データを読む段だけ開く。1着のモデルは `WinTargetData` で目的変数と基準を持ち替えた学習データで学ぶ（重みは持ち越す）。当日の3着以内のモデルには `FinishPowerFreeData` で Q を外して渡す。木曜のモデルには展開の予想の結果（P）を足す。当日の券種オッズなしのモデルは `PoolFreeData` で N を外して学ぶ。モデルは、4つ（木曜・前日・当日・当日の券種オッズなし）× 目的変数2つ × LightGBM と CatBoost で 16個になる。

## 図2. 予測

木曜・前日・当日のどれかの時点で、1つの重賞を予測するときの流れ。

```mermaid
sequenceDiagram
    actor U as 利用者
    participant JS as jvdata-store
    participant DB as 元DB
    participant GP as GradedRacePrediction
    participant W as PredictionWorkflow
    participant OR as OddsResolver
    participant D as DatasetBuilder
    participant L as RaceRecordsLoader
    participant RS as GradedRunnerSelector
    participant F as FeatureBuilder
    participant MR as ModelRepository
    participant E as EnsembleModel
    U->>JS: jvstore sync（出走馬名表・出馬表・出走別着度数・調教）
    JS->>DB: 書き込む
    opt 前日と当日だけ
        U->>JS: jvstore realtime（開催日。当日は全券種の速報オッズも）
        JS->>DB: 馬場状態・出馬表の変更・締め切り前のオッズ（当日は馬体重も）を書き込む
    end
    U->>GP: run（接続、レースID、時点、--odds で渡したオッズ）
    GP->>GP: 時点で DatasetBuilder・材料を足す関数・モデルの置き場所を選ぶ
    GP->>W: run（レースID、時点、オッズ）
    W->>OR: resolve（レースID、渡されたオッズ）
    OR-->>W: 馬番 → 単勝オッズ（手本の 06 の図2）
    W->>D: build_prediction_data（レースID、時点、オッズ）
    D->>L: load（レースID、オッズ）
    L->>L: 速報を読み、出走馬の記録を集める（手本の 05 の図4 と、この文書の図3）
    L-->>D: 出走の記録（graded_career・stakes_tendency の表付き）
    D->>RS: prediction_runners（出走の行、レースID）
    RS->>RS: 平地の重賞でなければ ValueError（06-flowchart.md の図2）
    RS-->>D: 予測する馬の行
    D->>F: build（記録、時点）
    F-->>D: その時点で使う特徴量（W・K を含む）
    D-->>W: 予測用データ（1行 = 1頭。重みは無い）
    W->>W: 材料（P・S・T）を足し、当日に券種のオッズが無ければ券種オッズなしのモデルにする（手本と同じ）
    W->>MR: load（時点）
    MR-->>W: その時点の LightGbmModel と CatBoostModel（3着以内）
    W->>E: predict_proba（予測用データ）
    E-->>W: 1頭ずつの3着以内に入る確率（2つの平均）
    W->>W: 1着のモデル（models/1着/）でも同じ手順で予測する
    W->>W: 前日・当日なら、複勝の期待値と単勝の期待値を足す
    W-->>GP: 1頭ずつの確率と期待値
    GP-->>U: 出走馬ごとの「3着以内に入る確率」「1着になる確率」と期待値（高い順の表）
```

**説明。** 予測は手本の図2と同じ流れで、違うのは2つだけである。1つは、`GradedRunnerSelector.prediction_runners()` が、渡されたレースが平地の重賞でなければ止めること（このモデルは重賞を重く見て学んだもので、重賞の印と買い目に使うため。重賞でないレースは手本で予想する）。もう1つは、記録を集めるときに重賞の材料を読む2つの呼び出し（図3）が増えることである。予測用データに重みは付かない（重みは学習のときだけ使う）。予測に使うオッズの決め方と、要る情報が欠けているときの止め方は手本と同じである（[手本の 07 の「予測のときのオッズの与え方」](../近走と適性から3着以内を予想/07-prediction-timing.md#予測のときのオッズの与え方)）。

## 図3. 重賞の材料を読む

図1・図2の「リポジトリを順に呼んで記録を集める」（手本の 05 の図3・図4）の並びの最後に増える呼び出しを示す。学習でも予測でも同じで、違うのは「対象」（学習では期間内の全部の出走、予測では1レース）だけである。

```mermaid
sequenceDiagram
    participant L as EntryRecordsLoader
    participant GC as GradedCareerRepository
    participant ST as StakesTendencyRepository
    participant DB as 元DB
    L->>GC: read（対象）
    GC->>DB: SQL（対象の出走ごとに、その馬の開催日より前の出走から、重賞の実績と前走の格を数える）
    DB-->>GC: 行
    GC-->>L: graded_career の表（1行 = 対象の出走）
    L->>ST: read（対象）
    ST->>DB: SQL（重賞の対応表の一時表が無ければ作る）
    DB-->>ST: 対応表（rid → 特別競走番号・グレード）
    ST->>DB: SQL（対象の重賞ごとに、それより前の開催の出走馬を並べる）
    DB-->>ST: 行
    ST-->>L: stakes_tendency の表（対象のレース × 過去の開催の1頭で1行）
```

**説明。** `GradedCareerRepository` はこの予想で足すリポジトリで、事実表の列（グレードコード・クラス名・確定着順・開催日）から、対象の出走ごとにその馬の過去の出走を数える。数えるのは開催日より前の出走だけである（[11-leak-prevention.md](11-leak-prevention.md#決まり) の 7）。`StakesTendencyRepository` は引退した予想のものをそのまま使い、SQL も `tools/共通/stakes.py` のままである（[引退した予想の 05 の図3](../重賞の傾向と近走から3着以内を予想/05-sequence.md#図3-重賞の傾向を読む)）。対象のうち重賞でないレースの行には、過去の開催の行が返らない（そのレースの K と、W の「同じ重賞の経験」は欠損値になる）。帯に分けて数える・同じ重賞の経験を引くのは SQL ではなく、`StakesTendencyFeatures`・`SameStakesHistory`（図1）で、学習と予測で同じクラスを通る。

## これから作るところ

| 図の中の部分・関係するもの | 今の状態 |
|---|---|
| `shared` に足す・変えるもの（`SampleWeighter`・`TrainingData` の重み・重みを渡す学習・`GradedCareerRepository`・`EntryRecords` の `graded_career`・ローダーの変更・K の部品の移し替え・`TrainPeriodArguments` の移し替え） | これから作る（[04-classes.md の 2](04-classes.md#2-shared-に足す変えるもの)） |
| この予想のパッケージ（`src/yosou/graded_race_top3_win/`） | これから作る（[04-classes.md の 4](04-classes.md#4-この予想だけのクラスの一覧)） |
| `StakesTendencyRepository` と SQL（`tools/共通/stakes.py`） | ある（引退した予想で作った） |
| 7つの区切りでの確かめ（研究「既存モデルの改善」の重賞の区切り `STAKES_WINDOWS`） | 区切りと比べ方の仕組みはある。この予想を学び直して予測を残す入口を足す（[16-evaluation.md の 4](16-evaluation.md#4-1年ずつの7つの区切りでの確かめ)） |
| 印と期待度の成績、印からの全券種の買い目の回収率（道具「印の成績」） | 道具はある。重賞だけに絞って、この予想の予測を読めるようにする（[16-evaluation.md の 5](16-evaluation.md#5-印と期待度の成績)） |
| 形の候補の数え上げと、券種の形・レースごとの券種の選び方を前半の年で選び、後半の年で確かめる入口 | これから作る。研究「重賞の買い方」の5回目として足す（[16-evaluation.md の 6](16-evaluation.md#6-印からの買い目の確かめ)） |
| 本番の買い方への入れ方（道具「今週の予想」・発走前の通知で、平地の重賞の確率をこの予想に替え、選んだ券種と形で買う。財布・金額） | **これから作る。** 買い方の設計書（[買うレースと買い目を決める](../買うレースと買い目を決める/01-overview.md)）の 03 の 4・07 の 5・08 の 2 を直す話で、16 の確かめで採用が決まってから行う。今の「3連単（重賞）」との関係は [15-decisions.md の 14](15-decisions.md#14-今の本番の3連単重賞との関係) で決める |
| 学習済みモデル（`reports/重賞に特化して3着以内と1着を予想/models/`） | `train` を実行すると作られる |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-14 |
