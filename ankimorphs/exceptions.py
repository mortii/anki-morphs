class DefaultSettingsException(Exception):
    """Raised when the default settings are used and no note type is selected"""


class NamesTextfileNotFoundException(Exception):
    """
    Raised when ignore names found in 'names.txt' is selected, but the
    file is not found
    """

    def __init__(self, path: str):
        self.path = path


class CancelledRecalcException(Exception):
    """Raised when the user clicked 'x' on the recalc pop-up dialog"""
