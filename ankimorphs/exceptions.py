class DefaultSettingsException(Exception):
    """Raised when the default settings are used and no note type is selected"""


class CardQueueEmptyException(Exception):
    """The new card queue has no more cards"""


class CancelledOperationException(Exception):
    """Raised when the user clicked 'x' on the recalc pop-up dialog"""


class EmptyFileSelectionException(Exception):
    """No file(s) selected"""


class SpacyNotInstalledException(Exception):
    # TODO: this might be obsolete
    """spaCy selected, but not installed"""


class FrequencyFileNotFoundException(Exception):
    """Selected frequency files not found"""

    def __init__(self, path: str):
        self.path = path
