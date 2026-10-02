"""学習のスレッド数を設定に入れる。"""

from __future__ import annotations

from yosou.shared.setting import HyperparameterSettings


class TrainingThreads:
    """予想のハイパーパラメータの設定のうち、学習のスレッド数（LightGBM の ``n_jobs``・CatBoost の ``thread_count``）だけを変える。

    同じマシンでほかの学習が全部のコアを使っていると、スレッドの取り合いで止まったように遅くなるため、数を絞る。
    スレッド数は木の作り方（学習の結果）を変えない。ほかのハイパーパラメータは予想の初期値のまま。
    """

    def __init__(self, threads: int) -> None:
        if threads < 1:
            raise ValueError(f"スレッド数は 1 以上にしてください: {threads}")
        self._threads = threads

    def apply(self, settings: HyperparameterSettings) -> HyperparameterSettings:
        values = settings.to_dict()
        values["lightgbm"]["params"]["n_jobs"] = self._threads
        values["catboost"]["params"]["thread_count"] = self._threads
        return HyperparameterSettings.from_dict(values)
