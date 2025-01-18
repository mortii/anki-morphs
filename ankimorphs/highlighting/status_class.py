from ..highlighting.base_classes import Injector, Range


class Status(Range, Injector):
    """Represents a morph's status and range in parent string."""

    def __init__(self, start: int, end: int, status: str, morph: str):
        super().__init__(start, end)
        self.status = status
        self.morph = morph

    def open(self) -> str:
        return f'<span morph-status="{self.status}">'

    def close(self) -> str:
        return "</span>"

    def inject(self, target: str) -> str:
        """Put this morph into the given string."""

        return (
            target[: self.start]
            + self.open()
            + target[self.start : self.end]
            + self.close()
            + target[self.end :]
        )

    def __repr__(self) -> str:
        return f"Range: {self.start}-{self.end}. Status: {self.status}, Morph: {self.morph}"
