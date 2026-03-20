"""
RAMP Lens Helpers
=================

Central, consistent mappings for all HOW lens transformations.
These MUST be used across all HOW responses to ensure Lens Contract compliance.

The HOW lens must NOT expose:
- Raw numeric scores (priority, severity, confidence)
- Baseline values or internal calculation inputs
- Score components or calculation internals

The HOW lens MUST expose:
- Bands (priority_band, severity_band)
- Confidence labels (strong, moderate, low, insufficient)
- Drivers and action-relevant context only
"""


def confidence_to_label(confidence: float) -> str:
    """
    Convert raw confidence score to human-readable label.
    
    This is the SINGLE authoritative mapping for confidence labels.
    All HOW responses must use this function.
    
    Mapping:
        >= 0.80 → "strong"
        >= 0.60 → "moderate"  
        >= 0.40 → "low"
        < 0.40  → "insufficient"
    
    Args:
        confidence: Raw confidence score (0.0 - 1.0)
        
    Returns:
        Human-readable confidence label
    """
    if confidence is None:
        return "unknown"
    if confidence >= 0.80:
        return "strong"
    elif confidence >= 0.60:
        return "moderate"
    elif confidence >= 0.40:
        return "low"
    return "insufficient"


def confidence_band_to_label(confidence_band: str) -> str:
    """
    Convert confidence band to label.
    
    Mapping:
        HIGH → "strong"
        MEDIUM → "moderate"
        LOW → "low"
        INSUFFICIENT → "insufficient"
    
    Args:
        confidence_band: Band string (HIGH, MEDIUM, LOW, INSUFFICIENT)
        
    Returns:
        Human-readable confidence label
    """
    if confidence_band is None:
        return "unknown"
    band = confidence_band.upper()
    if band == "HIGH":
        return "strong"
    elif band == "MEDIUM":
        return "moderate"
    elif band == "LOW":
        return "low"
    return "insufficient"


def severity_to_band(severity_score: float) -> str:
    """
    Convert raw severity score to band.
    
    This is for internal use when band is not already stored.
    
    Mapping:
        >= 8 → "CRITICAL"
        >= 6 → "HIGH"
        >= 4 → "MEDIUM"
        < 4  → "LOW"
    
    Args:
        severity_score: Raw severity score (1-10)
        
    Returns:
        Severity band
    """
    if severity_score is None:
        return "UNKNOWN"
    if severity_score >= 8:
        return "CRITICAL"
    elif severity_score >= 6:
        return "HIGH"
    elif severity_score >= 4:
        return "MEDIUM"
    return "LOW"


def priority_to_band(priority_score: float) -> str:
    """
    Convert raw priority score to band.
    
    This is for internal use when band is not already stored.
    
    Mapping:
        >= 80 → "CRITICAL"
        >= 60 → "HIGH"
        >= 40 → "MEDIUM"
        < 40  → "LOW"
    
    Args:
        priority_score: Raw priority score (0-100)
        
    Returns:
        Priority band
    """
    if priority_score is None:
        return "UNKNOWN"
    if priority_score >= 80:
        return "CRITICAL"
    elif priority_score >= 60:
        return "HIGH"
    elif priority_score >= 40:
        return "MEDIUM"
    return "LOW"


def criticality_to_band(criticality_score: float) -> str:
    """
    Convert raw criticality score to band.
    
    Mapping:
        >= 80 → "CRITICAL"
        >= 60 → "HIGH"
        >= 40 → "MEDIUM"
        < 40  → "LOW"
    
    Args:
        criticality_score: Raw criticality score (0-100)
        
    Returns:
        Criticality band
    """
    if criticality_score is None:
        return "UNKNOWN"
    if criticality_score >= 80:
        return "CRITICAL"
    elif criticality_score >= 60:
        return "HIGH"
    elif criticality_score >= 40:
        return "MEDIUM"
    return "LOW"
