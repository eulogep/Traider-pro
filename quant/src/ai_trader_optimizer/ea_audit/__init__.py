"""Offline behavioural audit of MetaTrader 5 Expert Advisors from their exported deal reports.

No terminal, no broker, no order: the owner uploads the report file exported from MT5.
"""

from .analysis import ANALYSIS_VERSION, THRESHOLDS, analyse
from .report import ReportFormatError, parse_report

__all__ = ["ANALYSIS_VERSION", "THRESHOLDS", "ReportFormatError", "analyse", "parse_report"]
