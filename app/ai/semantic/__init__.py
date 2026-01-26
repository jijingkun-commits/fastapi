"""
Semantic Layer for Data Agent

This module provides utilities for managing the semantic layer:
- Loading semantic models from YAML
- Metric resolution and SQL template generation
- Schema metadata management
"""

from .vanna_client import get_vanna, VannaClient

__all__ = ["get_vanna", "VannaClient"]
