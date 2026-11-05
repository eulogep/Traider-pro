"""Research layer: evidence about edges (labels, features, out-of-sample evaluation, robustness).

It never sends an order and never changes a stored run. See ``study.py`` for the protocol.
"""

from .robustness import run_robustness
from .study import StudySettings, list_studies, load_study, run_edge_study

__all__ = ["StudySettings", "list_studies", "load_study", "run_edge_study", "run_robustness"]
