"""1走を文にする。"""

from __future__ import annotations

from .past_run import PastRun

#: 4角から着順までに順位がこれだけ動いたら「追い込んで」「順位を下げて」と書く。
POSITION_SWING = 5


class RunSentence:
    """1走の事実を定型の文にする。

    ``2026-06-21 レース名（G3 阪神 芝1600m 稍重 18頭）3着・1番人気・着差 +0.1秒。ミドルペースを後方（最初のコーナー 13番手）で運び、
    4角 14番手から追い込んで、上がり 33.9秒（3位/18頭）。騎手名 53kg、馬体重 476kg（-4）。`` の形。無い材料の部分は省く。
    """

    def of(self, run: PastRun) -> str:
        return "".join(part for part in (self._head(run), self._result(run), self._flow(run), self._who(run)) if part)

    def _head(self, run: PastRun) -> str:
        inside = [run.qualifier, run.venue, f"{run.surface}{run.distance_m}m", run.condition,
                  f"{run.field_size}頭" if run.field_size else ""]
        return f"{run.race_date.isoformat()} {run.label}（{' '.join(part for part in inside if part)}）"

    def _result(self, run: PastRun) -> str:
        if run.finish is None:
            return "着順なし（競走中止など）。"
        parts = [f"{run.finish}着"]
        if run.popularity is not None:
            parts.append(f"{run.popularity}番人気")
        if run.time_diff is not None:
            parts.append(f"着差 {run.time_diff:+.1f}秒")
        return "・".join(parts) + "。"

    def _flow(self, run: PastRun) -> str:
        rest = []
        if run.corner4 is not None:
            rest.append(f"4角 {run.corner4}番手{self._swing(run)}")
        if run.last3f is not None:
            rest.append(self._last3f(run))
        early = f"{run.early_zone}（最初のコーナー {run.first_corner_rank}番手）で運び" if run.early_zone else ""
        if run.pace_name and early:
            head = f"{run.pace_name}ペースを{early}"
        elif run.pace_name:
            head = f"{run.pace_name}ペースの中" if rest else f"{run.pace_name}ペースのレース"
        else:
            head = early
        segments = [part for part in (head, *rest) if part]
        return "、".join(segments) + "。" if segments else ""

    def _swing(self, run: PastRun) -> str:
        if run.finish is None or run.corner4 is None:
            return "から"
        if run.corner4 - run.finish >= POSITION_SWING:
            return "から追い込んで"
        if run.finish - run.corner4 >= POSITION_SWING:
            return "から順位を下げて"
        return "から"

    def _last3f(self, run: PastRun) -> str:
        if run.last3f_rank == 1:
            return f"上がり最速の {run.last3f:.1f}秒"
        if run.last3f_rank is not None and run.last3f_count:
            return f"上がり {run.last3f:.1f}秒（{run.last3f_rank}位/{run.last3f_count}頭）"
        return f"上がり {run.last3f:.1f}秒"

    def _who(self, run: PastRun) -> str:
        parts = []
        if run.jockey:
            parts.append(run.jockey + (f" {run.carried:.0f}kg" if run.carried is not None else ""))
        if run.body_weight is not None:
            change = f"（{run.weight_change:+d}）" if run.weight_change is not None else ""
            parts.append(f"馬体重 {run.body_weight}kg{change}")
        return "、".join(parts) + "。" if parts else ""
