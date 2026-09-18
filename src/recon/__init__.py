"""RECON — task-conditioned semantic change detection.
Agents don't need more data. They need to know what changed.
Primitive: recon.inspect(source, previous, current, objective, sensitivity)
"""
from .diff import structural_diff, normalize_records
from .semantics import classify_change, impact_score
from .filter import task_relevance
from .engine import inspect

__all__ = ["inspect", "structural_diff", "normalize_records", "classify_change", "impact_score", "task_relevance"]
__version__ = "0.1.0"
