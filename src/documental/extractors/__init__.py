"""Extractores por familia documental."""

from .otros import EXTRACTORS, extract_clinico, extract_generic, extract_pagare, get_extractor

__all__ = ["EXTRACTORS", "extract_clinico", "extract_generic", "extract_pagare", "get_extractor"]
