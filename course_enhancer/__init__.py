"""Universal Course Enhancement Engine - core package.

LMS-independent by design: nothing in this package imports or references
Odoo (or any other LMS). See requirements_engine.py for the boundary layer
that translates this engine's output into LMS/Odoo implementation specs.
"""

__version__ = "0.1.0"
