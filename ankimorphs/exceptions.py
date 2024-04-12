class DefaultSettingsException(Exception):
    """Raised when the default settings are used and no note type is selected"""


class AnkiNoteTypeNotFound(Exception):
    """User tried to get Anki data that doesn't exist"""


class AnkiFieldNotFound(Exception):
    """User tried to get Anki data that doesn't exist"""


class CardQueueEmptyException(Exception):
    """The new card queue has no more cards"""


class CancelledOperationException(Exception):
    """Raised when the user clicked 'x' on the recalc pop-up dialog"""


class EmptyFileSelectionException(Exception):
    """No file(s) selected"""


class MorphemizerNotFoundException(Exception):
    """Selected Morphemizer(s) not found on the system"""

    def __init__(self, morphemizer_name: str):
        self.morphemizer_name = morphemizer_name


class FrequencyFileNotFoundException(Exception):
    """Selected frequency files not found"""

    def __init__(self, path: str):
        self.path = path
