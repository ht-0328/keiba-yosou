"""取得の画面（jvdata-store・nvdata-store のサーバー）の様子。"""

from __future__ import annotations

from dataclasses import dataclass

#: 取得の画面の処理の状態（``/api/task`` の ``status``）。
_SUCCEEDED, _FAILED = "succeeded", "failed"


@dataclass(frozen=True)
class StoreScreen:
    """取得の画面（サーバー）が動いているか、何を実行中か。``StoreScreenProbe`` が作る。

    ``name`` は聞いた相手（``jvdata-store`` か ``nvdata-store``）。``task_label`` は実行中か最後に実行した処理の名前
    （例: 速報の取得（2026-10-05））、``task_status`` は ``idle`` / ``running`` / ``succeeded`` / ``failed``。
    動いていなければ ``error`` にその理由。
    """

    name: str
    url: str
    running: bool
    app: str = ""
    db: str = ""
    task_label: str = ""
    task_status: str = ""
    task_running: bool = False
    finished_at: str | None = None
    error: str = ""

    def describe(self) -> str:
        """1行の説明（画面と CLI に出す）。"""
        if not self.running:
            return f"止まっている（{self.error}。{self.url}）。取得するには {self.name} の run.bat を実行する"
        if self.task_running:
            return f"動いている。実行中: {self.task_label}"
        if self.task_status == _SUCCEEDED:
            return f"動いている。最後の処理: {self.task_label}（完了 {self.finished_at}）"
        if self.task_status == _FAILED:
            return f"動いている。最後の処理: {self.task_label}（失敗 {self.finished_at}。ログは {self.name} の画面で見る）"
        return "動いている（処理なし）"
