"""元DB から読む部品。1つのクラスが1つの SQL を持つ。"""

from .stakes_grade_repository import StakesGradeRepository

__all__ = ["StakesGradeRepository"]
