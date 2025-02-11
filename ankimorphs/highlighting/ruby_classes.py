from abc import abstractmethod

from ..highlighting.base_classes import Injector, Range


class Ruby(Range, Injector):
    """
    Abstract base class to define minimum interface for all Ruby Range subclasses.
    """

    def __init__(self, start: int, end: int, base: str, ruby: str):
        super().__init__(start, end)
        self.base = base
        self.ruby = ruby

    @abstractmethod
    def rt(self) -> str:
        """
        defines how the rt is injected
        """

    def inject(self, target: str) -> str:
        return target[: self.start] + str(self) + target[self.end :]

    def __str__(self) -> str:
        return f"{self.open()}{self.base}{self.rt()}{self.close()}"

    def __repr__(self) -> str:
        return f"Range: {self.start}-{self.end}. Value: {str(self)}"


class FuriganaRuby(Ruby):
    """
    Represents an html ruby and its range in parent string.
    """

    def open(self) -> str:
        return "<ruby>"

    def close(self) -> str:
        return "</ruby>"

    def rt(self) -> str:
        return f"<rt>{self.ruby}</rt>"


class KanjiRuby(Ruby):
    """
    Represents a kanji ruby and its range in parent string.
    """

    def open(self) -> str:
        return ""

    def close(self) -> str:
        return ""

    def rt(self) -> str:
        return ""


class KanaRuby(Ruby):
    """
    Represents a kana ruby and its range in parent string.
    """

    def open(self) -> str:
        return ""

    def close(self) -> str:
        return ""

    def rt(self) -> str:
        return ""

    def __str__(self) -> str:
        return self.ruby


class TextRuby(Ruby):
    """
    Represents a text ruby and its range in parent string.
    """

    def open(self) -> str:
        return " "

    def close(self) -> str:
        return ""

    def rt(self) -> str:
        return f"[{self.ruby}]"
