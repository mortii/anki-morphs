class DefaultSettingsException(Exception):
    """Raised when the default settings are used and no note type is selected"""


class CancelledRecalcException(Exception):
    """Raised when the user clicked 'x' on the recalc pop-up dialog"""
