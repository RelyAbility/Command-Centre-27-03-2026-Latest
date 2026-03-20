"""
RAMP Lenses
===========

Lens builders enforce payload discipline for HOW and WHERE perspectives.
"""

from .how import HOWLens
from .where import WHERELens
from .helpers import (
    confidence_to_label,
    confidence_band_to_label,
    severity_to_band,
    priority_to_band,
    criticality_to_band
)

__all__ = [
    "HOWLens", 
    "WHERELens",
    "confidence_to_label",
    "confidence_band_to_label",
    "severity_to_band",
    "priority_to_band",
    "criticality_to_band"
]
