"""
utils
=====

Utility package for the Contactless Fingerprint Quality Assessment & Scoring
Pipeline.

Modules
-------
image_utils : Image I/O and low-level helper routines.
metrics     : The five core biometric quality metric functions.
scoring     : Normalization and composite score computation.
guidance    : Human-readable guidance message resolution.
"""

from . import image_utils
from . import metrics
from . import scoring
from . import guidance

__all__ = ["image_utils", "metrics", "scoring", "guidance"]

__version__ = "1.0.0"
