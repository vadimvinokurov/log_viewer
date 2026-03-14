"""Core package."""
from __future__ import annotations

from src.core.parser import LogParser
from src.core.filter_engine import FilterEngine
from src.core.simple_query_parser import SimpleQueryParser
from src.core.category_tree import CategoryTree, CategoryNode, build_category_display_nodes
from src.core.highlight_engine import HighlightEngine, HighlightPattern, HighlightRange
from src.core.statistics import StatisticsCalculator, LogStatistics

__all__ = [
    "LogParser",
    "FilterEngine",
    "SimpleQueryParser",
    "CategoryTree",
    "CategoryNode",
    "build_category_display_nodes",
    "HighlightEngine",
    "HighlightPattern",
    "HighlightRange",
    "StatisticsCalculator",
    "LogStatistics",
]