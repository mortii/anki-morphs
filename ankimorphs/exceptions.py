class DefaultSettingsException(Exception):
    """Raised when the default settings are used and no note type is selected"""


class CancelledOperationException(Exception):
    """Raised when the user clicked 'x' on the recalc pop-up dialog"""


class EmptyFileSelectionException(Exception):
    """No file(s) selected"""
