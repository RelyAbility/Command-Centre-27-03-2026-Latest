"""
RAMP Verification Configuration
===============================

Configurable verification windows by state family and intervention type.
These settings determine how long to wait after intervention completion
before attempting verification, and minimum data requirements.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class OutcomeStatus(str, Enum):
    """Outcome verification status."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class VerificationConfig:
    """
    Configuration for verification of a specific state family / intervention type.
    
    Attributes:
        window_hours: Hours to wait after intervention before verification
        min_samples: Minimum post-action data points required
        min_window_coverage: Minimum % of window that must have data (0.0-1.0)
        max_retry_attempts: Maximum times to retry verification if insufficient data
        retry_interval_hours: Hours between retry attempts
    """
    window_hours: float
    min_samples: int
    min_window_coverage: float = 0.5
    max_retry_attempts: int = 3
    retry_interval_hours: float = 2.0


# Default verification configurations by state family
DEFAULT_CONFIGS: Dict[str, VerificationConfig] = {
    # ENERGY states - need longer window to capture operational patterns
    "ENERGY": VerificationConfig(
        window_hours=4.0,
        min_samples=8,
        min_window_coverage=0.5,
        max_retry_attempts=3,
        retry_interval_hours=2.0
    ),
    
    # OPERATIONAL states - can verify faster
    "OPERATIONAL": VerificationConfig(
        window_hours=2.0,
        min_samples=6,
        min_window_coverage=0.4,
        max_retry_attempts=4,
        retry_interval_hours=1.0
    ),
    
    # MAINTENANCE states - need longer observation
    "MAINTENANCE": VerificationConfig(
        window_hours=8.0,
        min_samples=12,
        min_window_coverage=0.6,
        max_retry_attempts=2,
        retry_interval_hours=4.0
    ),
    
    # PRODUCTION states - moderate window
    "PRODUCTION": VerificationConfig(
        window_hours=4.0,
        min_samples=10,
        min_window_coverage=0.5,
        max_retry_attempts=3,
        retry_interval_hours=2.0
    ),
}

# Override by intervention type (takes precedence over state family)
INTERVENTION_TYPE_CONFIGS: Dict[str, VerificationConfig] = {
    # Quick adjustments can be verified faster
    "ADJUSTMENT": VerificationConfig(
        window_hours=2.0,
        min_samples=6,
        min_window_coverage=0.4,
        max_retry_attempts=4,
        retry_interval_hours=1.0
    ),
    
    # Repairs need longer to confirm
    "REPAIR": VerificationConfig(
        window_hours=8.0,
        min_samples=16,
        min_window_coverage=0.6,
        max_retry_attempts=2,
        retry_interval_hours=4.0
    ),
    
    # Replacements need extended observation
    "REPLACEMENT": VerificationConfig(
        window_hours=24.0,
        min_samples=24,
        min_window_coverage=0.7,
        max_retry_attempts=2,
        retry_interval_hours=8.0
    ),
    
    # Calibration - quick to verify
    "CALIBRATION": VerificationConfig(
        window_hours=1.0,
        min_samples=4,
        min_window_coverage=0.3,
        max_retry_attempts=6,
        retry_interval_hours=0.5
    ),
    
    # Maintenance - standard window
    "MAINTENANCE": VerificationConfig(
        window_hours=4.0,
        min_samples=8,
        min_window_coverage=0.5,
        max_retry_attempts=3,
        retry_interval_hours=2.0
    ),
}


def get_verification_config(
    state_family: Optional[str] = None,
    intervention_type: Optional[str] = None
) -> VerificationConfig:
    """
    Get verification configuration for a state family / intervention type.
    
    Priority:
    1. Intervention type config (if exists)
    2. State family config (if exists)
    3. Default OPERATIONAL config
    
    Args:
        state_family: State family (ENERGY, OPERATIONAL, etc.)
        intervention_type: Intervention type (ADJUSTMENT, REPAIR, etc.)
        
    Returns:
        VerificationConfig for this combination
    """
    # Check intervention type first (takes precedence)
    if intervention_type:
        intervention_type_upper = intervention_type.upper()
        if intervention_type_upper in INTERVENTION_TYPE_CONFIGS:
            return INTERVENTION_TYPE_CONFIGS[intervention_type_upper]
    
    # Fall back to state family
    if state_family:
        state_family_upper = state_family.upper()
        if state_family_upper in DEFAULT_CONFIGS:
            return DEFAULT_CONFIGS[state_family_upper]
    
    # Default to OPERATIONAL config
    return DEFAULT_CONFIGS["OPERATIONAL"]
