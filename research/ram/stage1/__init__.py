"""Stage-1 RAM skeleton (design capacity ≤50 names).

Hard runtime cap remains aligned with Stage-0 until this package has its own
evidence note and tests. Do not import stage1 risk functions into production
paths until STAGE_GATES.md Stage-1 checklist is complete.
"""

from .covariance import MAX_STAGE1_DESIGN_UNIVERSE

__all__ = ["MAX_STAGE1_DESIGN_UNIVERSE"]
