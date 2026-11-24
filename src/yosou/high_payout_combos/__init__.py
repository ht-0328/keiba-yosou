"""高配当の組が当たるかを予想する。

中央競馬の5つの券種（ワイド・馬連・馬単・3連複・3連単）について、**高配当の組が当たる確率**を出す。
1行 = 1レース × 1券種 × 1つの組。材料は、5券種のオッズの板（市場の確率）と、馬ごとの予想（今の本番の予想の確率・印・危険な人気馬）。
モデルは、その券種のオッズから見た組の確率 q を出発点（基準）にして、そこからの上げ下げだけを学ぶ（LightGBM と CatBoost の平均）。
買うのは「オッズが高配当の線以上・上限未満で、期待値（確率 × オッズ）が 1.05 以上」の組。

## 対象の行と帯

オッズ（ワイドは最低オッズ）が「学ぶ下限」以上「上限」未満の組を、学習と予測の対象にする。買うのは「高配当の線」以上だけで、
学ぶ行は線より下まで広げてある（``dataset/default_bands.py``）。

| 券種 | 学ぶ下限 | 高配当の線 | 上限 |
|---|---|---|---|
| ワイド | 3倍 | 10倍 | 300倍 |
| 馬連 | 8倍 | 30倍 | 1,000倍 |
| 馬単 | 15倍 | 60倍 | 3,000倍 |
| 3連複 | 20倍 | 100倍 | 3,000倍 |
| 3連単 | 100倍 | 500倍 | 10,000倍 |

## 材料のまとまり（``feature/``。定義は各クラスの docstring）

| まとまり | 中身 | 例 |
|---|---|---|
| A. その券種の市場 | オッズ、市場の確率 q、3連単の市場から足し合わせた確率 t、その差 | ``log_odds``・``log_q``・``log_t``・``d_t`` |
| B. ほかの券種の市場 | 組に含まれる2頭・3頭の組の、ほかの券種での市場の確率 | 馬連の組の ``x_wide``（同じ2頭のワイド） |
| C. Harville | 予想の1着の確率と、単勝オッズから見た勝率から、Harville の式で出した組の確率 | ``log_hv``・``d_hv`` |
| D. 組の位置ごとの馬 | 組の馬ごとの 20個の材料（予想と市場の確率・その差と比・人気・印 …）を位置ごとに | ``pw0``・``pop1`` |
| E. 組のまとめ | 組の馬の材料の和・最小・最大・数 | ``s_pop``・``n_ls_in`` |
| F. レース | 頭数、1番人気の値、危険な人気馬の数、学ぶ帯の大きさ など | ``field``・``fav_odds``・``reg_n`` |

## フォルダ

| フォルダ | 中身 |
|---|---|
| ``command/`` | コマンド（tables・walk・train）の引数。入口 |
| ``workflow/`` | 流れ（組の表づくり・年ごとの学習と予測・本番のモデルの学習・1レースの予測） |
| ``evaluation/`` | 当たり具合（市場の確率との対数損失の比べ、買い目の年ごとの成績） |
| ``betting/`` | 買い目の決まり |
| ``dataset/`` | 帯、馬ごとの材料、レースごとの表、組の表づくり、払戻を付ける、外れの間引き、モデルに渡す形への詰め替え |
| ``feature/`` | 材料のまとまりごとのクラスと、券種ごとの材料の一覧 |
| ``repository/`` | 馬ごとの表・組の表・年ごとの予測・券種ごとの学習済みモデルのファイルの読み書き |
| ``setting/`` | ハイパーパラメータの初期値のファイル |
| ``tests/`` | テスト（合成のデータだけ） |

決まり: 1ファイルに1クラス。1クラスに1つの仕事。この予想だけの SQL は無い（元DB は ``yosou.shared.repository`` で読む）。
参照の向きは上から下へ一方向（``command`` → ``workflow`` → ``evaluation`` → ``betting`` → ``dataset`` → ``feature``。
``repository`` はファイルの読み書きだけで、``command``・``workflow``・``dataset`` から使う）。
モデルの学習・保存・読み込みと、市場の確率 q・t の計算は、共有の部品（``yosou.shared.ml_model``・``yosou.shared.combo_value``）を使う。

## この予想を使う道具から呼ぶもの

    from yosou.high_payout_combos import DEFAULT_BANDS, DEFAULT_VALUE_LINE, HighPayoutPredictor, HighPayoutRule, PredictionStore

    predictor = HighPayoutPredictor.load(models_folder)        # models/<券種の英名>/ を読む。無い券種は扱わない
    combos = predictor.predict(horses, boards)                  # 1レースの馬ごとの表と、券種 → 板（race_id・combo・odds）
    picks = HighPayoutRule(DEFAULT_BANDS, DEFAULT_VALUE_LINE).pick(combos)   # 買う組だけ
    predictions = PredictionStore(folder).load(ticket_type)     # walk の出力（年ごとの予測）を全部の年ぶん
"""

from .betting import HighPayoutRule
from .command.yosou_name import YOSOU_NAME
from .dataset import DEFAULT_BANDS, DEFAULT_VALUE_LINE, PayoutBand
from .repository import PredictionStore
from .workflow import HighPayoutPredictor

__all__ = [
    "YOSOU_NAME", "PayoutBand", "DEFAULT_BANDS", "DEFAULT_VALUE_LINE", "HighPayoutPredictor", "HighPayoutRule", "PredictionStore",
]
