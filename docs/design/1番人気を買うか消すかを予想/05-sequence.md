# 05 学習・評価・予測のやりとり（シーケンス図）

**この文書で示すこと:** 学習・1年ごとの評価・予測のとき、利用者・jvdata-store・元DB と、[04-classes.md](04-classes.md) のクラスが、どの順に、どのメソッドを呼ぶか。

**結論: 流れは「学習」「1年ごとの評価」「予測」の3つに分かれる。** どれもコマンド（`train`・`evaluate`・`predict`）から始まる。学習は `SimilarityTraining` が進め、単位を決めてから、単位ごとに3つのグループのモデルを作る。1年ごとの評価は `YearlyEvaluation` が進め、評価する年ごとに学習し直して、その年の1番人気を判定する。予測は `PredictionWorkflow` が進め、保存したモデルの一式で1レースの1番人気を判定する。

- 図に出てくるもの（利用者・jvdata-store・元DB・クラス・保存したファイル）と、図の読み方（凡例）は [手本の 05 の「図に出てくるもの」](../近走と適性から3着以内を予想/05-sequence.md#図に出てくるもの) と [「図の読み方」](../近走と適性から3着以内を予想/05-sequence.md#図の読み方) を参照。ライブラリ（`NearestNeighbors`）の呼び出しは [13-closeness-score.md](13-closeness-score.md#3-点数を出すやりとりシーケンス図) に描く。
- public メソッドの中の判断（if 文による分かれ道）は [06-flowchart.md](06-flowchart.md) を参照。2種類の図の使い分けは [01-overview.md](01-overview.md#図の使い分け) を参照。
- **リポジトリとのやりとりは、手本とまったく同じである。** 学習データを集める流れは [手本の 05 の図3](../近走と適性から3着以内を予想/05-sequence.md#図3-記録を集めるリポジトリとのやりとり)、1レースの記録を集めて速報を反映する流れは [手本の 05 の図4](../近走と適性から3着以内を予想/05-sequence.md#図4-1レースの記録を集める速報の反映) を参照。この文書では描き直さない。

## 図1. 学習

`train` コマンドで、本番の予測に使うモデルの一式を作るときの流れ。

```mermaid
sequenceDiagram
    actor U as 利用者
    participant C as TrainCommand
    participant S as BuyOrFadeSettings
    participant R as TrainingDataReader
    participant D as DatasetBuilder
    participant T as SimilarityTraining
    participant M as CourseUnitMap
    participant US as UnitSimilarity
    participant MR as SimilarityModelRepository
    U->>C: train（--config 設定ファイル、省略可）
    C->>S: load（設定ファイルのパス）
    S-->>C: 方針（初期値に設定ファイルを重ねたもの）
    C->>R: read（元DB への接続）
    R->>D: build_training_data（学習の最初の年の1月1日から）
    D->>D: 記録を集め、特徴量を作り、1番人気の行だけ残し、グループの列を付ける（06-flowchart.md の図1）
    D-->>R: 学習データ（1行 = 1レースの1番人気）
    R-->>C: 学習データ（ここで元DB を閉じる）
    C->>T: train（学習データ）
    T->>T: 方針の時点の特徴量の列にする
    T->>M: from_rows（特徴量、min_rows）
    M-->>T: 単位の決め方（06-flowchart.md の図3）
    loop 単位ごと
        T->>US: fit（その単位の特徴量、グループの列）
        US->>US: 行列にする物差しを作り、3つのグループのモデルを作る（13-closeness-score.md の 3.）
        US-->>T: その単位の3つのモデル
    end
    T-->>C: モデルの一式（単位の決め方・単位ごとのモデル・方針）
    C->>MR: save（一式）
    MR-->>C: 保存した（models の pickle と settings.json）
    C-->>U: 単位ごとのグループの頭数の表と、保存した場所
```

**説明。** 学習データは、方針の「学習の最初の年」（2017年）の1月1日から、元DB の最後の開催日までの1番人気である。その前の年はウォームアップ（過去走の特徴量の計算にだけ使う）。元DB を使うのは学習データを読む段だけで、コマンドはそこで元DB を閉じてから学習する（手本と同じ）。

**この予想の「学習」とは、次の3つを作って保存することである。** k近傍法には、LightGBM のような「木を足していく」学習は無い。

1. 単位の決め方（どの芝ダ・距離をどの単位にするか）。
2. 単位ごとに、距離に使う行列の作り方（中央値・標準化の物差し・カテゴリの値の一覧・重み）。単位の3つのグループを合わせた全頭から作る。
3. 単位ごと・グループごとに、そのグループの馬だけを覚えた k近傍のモデルと、点数の物差し（単位の1番人気全員の距離の並び）。

## 図2. 1年ごとの評価

`evaluate` コマンドで、評価する年（2019〜2026年）ごとに学習し直して判定し、成績の表を出すときの流れ。

```mermaid
sequenceDiagram
    actor U as 利用者
    participant C as EvaluateCommand
    participant R as TrainingDataReader
    participant Y as YearlyEvaluation
    participant T as SimilarityTraining
    participant J as FavoriteJudgement
    participant E as EvaluationTables
    U->>C: evaluate（--config、--rows-out、--out、省略可）
    C->>R: read（元DB への接続）
    R-->>C: 学習データ（学習の最初の年から元DB の最後まで。ここで元DB を閉じる）
    C->>Y: run（学習データ）
    loop 評価する年ごと
        Y->>Y: 学習の最初の年からその前年までと、その年に分ける
        Y->>T: train（その前年までの行）
        T-->>Y: その年の評価に使うモデルの一式（図1と同じ作り方）
        Y->>J: judge（その年の1番人気の特徴量）
        J-->>Y: 1番人気ごとの単位・3つの点数・判定
    end
    Y-->>C: 判定した1番人気の表（年・単位・点数・判定・グループ・払戻）
    C->>E: tables（判定した1番人気の表）
    E-->>C: 年ごと・判定ごと・単位ごとの表
    C-->>U: 表（--rows-out を渡せば、1頭ずつの表を CSV でも書く）
```

**説明。** 評価する年のデータは、その年の学習に入らない。単位の決め方も、評価の年ごとに、その年の学習データの頭数で決め直す。表の見方は [16-evaluation.md](16-evaluation.md#3-表の見方) を参照。1頭ずつの表は JV-Data から作ったものなので、`reports/` の下に置く。

## 図3. 予測

前日か当日に、1レースの1番人気を判定するときの流れ。時点と判定の線は、学習したときの方針を使う。

```mermaid
sequenceDiagram
    actor U as 利用者
    participant JS as jvdata-store
    participant DB as 元DB
    participant C as PredictCommand
    participant MR as SimilarityModelRepository
    participant W as PredictionWorkflow
    participant OR as OddsResolver
    participant PA as PopularityApplier
    participant D as DatasetBuilder
    participant J as FavoriteJudgement
    U->>JS: jvstore sync（出馬表・出走別着度数・調教）
    JS->>DB: 書き込む
    U->>JS: jvstore realtime（開催日）
    JS->>DB: 馬場状態・出馬表の変更・締め切り前のオッズ（当日は馬体重も）を書き込む
    U->>C: predict（rid か --date --venue --race、--pops、--odds）
    C->>MR: load（）
    MR-->>C: モデルの一式（方針を含む）
    C->>W: run（レースID、渡された人気、渡されたオッズ）
    W->>OR: resolve（レースID、渡されたオッズ）
    OR-->>W: 馬番 → 単勝オッズ（手本の 06 の図2）
    W->>PA: resolve（レースID、渡された人気、オッズ）
    PA-->>W: 馬番 → 人気（渡されなければオッズの小さい順）
    W->>D: build_prediction_data（レースID、方針の時点、人気、オッズ）
    D->>D: 記録を集め、特徴量を作り、1番人気の行だけ残す（手本の 05 の図4）
    D-->>W: 予測用データ（1番人気の行）
    W->>J: judge（1番人気の特徴量）
    J->>J: 単位を決め、その単位の3つのモデルで点数を出し、判定する（13-closeness-score.md の 3.・4.）
    J-->>W: 単位・3つの点数・判定
    W-->>C: 1番人気の判定
    C-->>U: 表（馬番・馬名・単位・3つの点数・判定）
```

**説明。** 人気は、利用者が `--pops 馬番:人気` で渡すか、`--odds 馬番:オッズ` で渡したオッズの小さい順か、元DB の締め切り前のオッズで決まる（[07-prediction-timing.md](07-prediction-timing.md#予測のときの1番人気の決め方)）。予測用データの作り方は学習と同じ `DatasetBuilder` なので、学習と予測で特徴量の中身がずれない。判定は、評価と同じ `FavoriteJudgement` で行う。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-25 |
| 更新 | 2026-09-25: k近傍法の設計に作り直した。同日、実装したクラスとコマンドに合わせて書き直した（評価を1年ごとの評価にした） |
