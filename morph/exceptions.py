class NoteFilterFieldsException(Exception):
    """Exception raised when the user specified entry into "Fields" in note filter is not found"""

    def __init__(self, _field_name: str, _note_type: str):
        self.field_name = _field_name
        self.note_type = _note_type


class ProfileNotYetLoadedException(Exception):
    """Raised when the profile is not yet loaded"""
