from __future__ import annotations

from abc import abstractmethod
from collections import deque

from . import text_preprocessing, debug_utils
from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme


class Range:
    """Base class for Ranges."""

    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end


class RubyRange(Range):
    """Abstract base class to define minimum interface for all Ruby Range subclasses."""

    def __init__(self, start: int, end: int, base: str, ruby: str):
        super().__init__(start, end)
        self.base = base
        self.ruby = ruby

    def open_len(self) -> int:
        return len(self.open())

    @abstractmethod
    def open(self) -> str:
        return NotImplemented

    @abstractmethod
    def close(self) -> str:
        return NotImplemented

    @abstractmethod
    def rt(self) -> str:
        return NotImplemented

    def inject(self, target: str) -> str:
        return target[: self.start] + str(self) + target[self.end :]

    def __str__(self) -> str:
        return f"{self.open()}{self.base}{self.rt()}{self.close()}"

    def __repr__(self) -> str:
        return f"Range: {self.start}-{self.end}. Value: {str(self)}"


class HtmlRubyRange(RubyRange):
    """Represents an html ruby and its range in parent string."""

    def open(self) -> str:
        return "<ruby>"

    def close(self) -> str:
        return "</ruby>"

    def rt(self) -> str:
        return f"<rt>{self.ruby}</rt>"


class TextRubyRange(RubyRange):
    """Represents a text ruby and its range in parent string."""

    def open(self) -> str:
        return " "

    def close(self) -> str:
        return ""

    def rt(self) -> str:
        return f"[{self.ruby}]"


class StatusRange(Range):
    """Represents a morph's status and range in parent string."""

    def __init__(self, start: int, end: int, status: str, morph: str):
        super().__init__(start, end)
        self.status = status
        self.morph = morph

    def open_len(self) -> int:
        """Len of the open tag, useful for setting string splice offsets."""
        return len(self.open())

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


class TextHighlighter:
    """Represents an expression to highlight. Tracks 2 sets of data, one for rubies the other
    for morph status. all the magic happens in _process() where we merge them together on top
    of the base string."""

    def __init__(
        self,
        expression: str,
        morphs_and_statuses: list[MorphAndStatus],
        ruby_range_type: type[RubyRange],
    ):
        self._highlighted: str | None = None
        self.expression: str = expression
        self.rubies: deque[RubyRange] = deque()
        self.statuses: deque[StatusRange] = deque()

        self._tag_rubies(ruby_range_type)
        self._tag_morphemes(self.expression.lower(), morphs_and_statuses)

        debug_utils.dev_print(f"stripped expression: {self.expression}")
        debug_utils.dev_print(f"self.rubies: {self.rubies}")
        debug_utils.dev_print(f"self.statuses: {self.statuses}")

    def _tag_rubies(self, ruby_range_type: type[RubyRange]) -> None:
        """Populate internal deque of found ruby locations."""

        end = 0

        while True:
            match = text_preprocessing.ruby_regex.search(self.expression, pos=end)

            if not match:
                break

            end = match.start() + len(match.group(1))

            self.rubies.append(
                ruby_range_type(match.start(), end, match.group(1), match.group(2))
            )
            self.expression = (
                self.expression[: match.start()]
                + match.group(1)
                + self.expression[match.end() :]
            )

    def _tag_morphemes(
        self, expression: str, morphs_and_statuses: list[MorphAndStatus]
    ) -> None:
        """Populate internal deque of found morph locations."""

        for morph_and_status in sorted(
            morphs_and_statuses, key=lambda meta: len(meta.morph), reverse=True
        ):
            while True:
                start = expression.find(morph_and_status.morph)

                if start == -1:
                    break

                end = start + len(morph_and_status.morph)

                self.statuses.append(
                    StatusRange(
                        start, end, morph_and_status.status, morph_and_status.morph
                    )
                )
                expression = (
                    expression[:start] + (" " * (end - start)) + expression[end:]
                )

        self.statuses = deque(sorted(self.statuses, key=lambda _range: _range.start))

    def highlighted(self) -> str:
        """Get the highlighted string. Pull from cache if present."""

        if not self._highlighted:
            self._highlighted = self.expression or ""

            if self._highlighted and (self.rubies or self.statuses):
                self._process()

        return self._highlighted

    def _process(self) -> None:  # pylint:disable=too-many-branches, too-many-statements
        """Process the text in self._highlighted, now that all the metadata has been gathered."""

        ruby: RubyRange | None = None
        status: StatusRange | None = None

        while_counter = -1

        while self._highlighted is not None:

            debug_utils.dev_print(f"self._highlighted: {self._highlighted}")

            while_counter += 1
            debug_utils.dev_print(f"while counter: {while_counter}")

            if ruby is None and self.rubies:
                ruby = self.rubies.pop()

            if status is None and self.statuses:
                status = self.statuses.pop()

            if ruby is None and status is None:
                break

            # If there are only statuses.
            if ruby is None:
                debug_utils.dev_print("Scenario 1: There are only statuses.")
                # Ignore is here because (surprisingly) mypy can not tell the
                # only path that leads here requires stat to be non-None.
                self._highlighted = status.inject(self._highlighted)  # type: ignore[union-attr]
                status = None
                continue

            # If there are only rubies.
            if status is None:
                debug_utils.dev_print("Scenario 2: There are only rubies.")
                self._highlighted = ruby.inject(self._highlighted)
                ruby = None
                continue

            debug_utils.dev_print(f"current ruby: {repr(ruby)}")
            debug_utils.dev_print(f"current status: {repr(status)}")

            # If there is no overlap between ruby and status, process the latest one.
            if ruby.end <= status.start or ruby.start >= status.end:
                debug_utils.dev_print(
                    "Scenario 3: There is no overlap between ruby and status."
                )
                if ruby.start > status.start:
                    self._highlighted = ruby.inject(self._highlighted)
                    ruby = None
                else:
                    self._highlighted = status.inject(self._highlighted)
                    status = None
                continue

            # If the status is the same as the ruby
            if ruby.start == status.start and ruby.end == status.end:
                debug_utils.dev_print("Scenario 4: The status is the same as the ruby.")
                self._highlighted = (
                    self._highlighted[: status.start]
                    + status.open()
                    + str(ruby)
                    + status.close()
                    + self._highlighted[status.end :]
                )
                ruby = None
                status = None
                continue

            # If the ruby is completely inside the status
            if ruby.start >= status.start and ruby.end <= status.end:
                debug_utils.dev_print(
                    "Scenario 5: The ruby is completely inside the status."
                )
                self._highlighted = (
                    self._highlighted[: status.start]
                    + status.open()
                    + self._highlighted[
                        status.start : status.start + ruby.start - status.start
                    ]
                    + str(ruby)
                    + self._highlighted[ruby.end : status.end]
                    + status.close()
                    + self._highlighted[status.end :]
                )
                ruby = None

                # Pull and process rubies until the next ruby is outside of this status.
                while self.rubies:
                    if self.rubies[-1].end <= status.start:
                        break

                    ruby = self.rubies.pop()
                    ruby.start += status.open_len()
                    ruby.end += status.open_len()
                    self._highlighted = ruby.inject(self._highlighted)

                status = None
                ruby = None
                continue

            # If the status is completely inside the ruby
            if ruby.start <= status.start and ruby.end >= status.end:
                debug_utils.dev_print(
                    "Scenario 6: The status is completely inside the ruby."
                )
                if isinstance(ruby, HtmlRubyRange):
                    debug_utils.dev_print("html path")
                    self._highlighted = ruby.inject(self._highlighted)
                    status.start += ruby.open_len()
                    status.end += ruby.open_len()
                    self._highlighted = status.inject(self._highlighted)
                    status = None

                    # Pull and process statuses until the next status is outside of this ruby.
                    while self.statuses:
                        if self.statuses[-1].end <= ruby.start:
                            break

                        status = self.statuses.pop()
                        status.start += ruby.open_len()
                        status.end += ruby.open_len()
                        self._highlighted = status.inject(self._highlighted)

                elif isinstance(ruby, TextRubyRange):
                    debug_utils.dev_print("text path")
                    status.status = "undefined"
                    self._highlighted = (
                        self._highlighted[: ruby.start]
                        + status.open()
                        + str(ruby)
                        + status.close()
                        + self._highlighted[ruby.end :]
                    )

                    status = None

                    # Pull and process statuses until the next status is outside of this ruby.
                    while self.statuses:
                        if self.statuses[-1].end <= ruby.start:
                            break

                        status = self.statuses.pop()

                ruby = None
                status = None
                continue

            # If the ruby starts then status starts, ruby ends, status ends
            if ruby.start < status.start and ruby.end < status.end:
                debug_utils.dev_print(
                    "Scenario 7: The ruby starts then status starts, ruby ends, status ends."
                )
                if isinstance(ruby, HtmlRubyRange):
                    debug_utils.dev_print("html path")
                    self._highlighted = (
                        self._highlighted[: ruby.start]
                        + ruby.open()
                        + self._highlighted[ruby.start : status.start]
                        + status.open()
                        + self._highlighted[
                            status.start : status.start
                            + (status.end - status.start)
                            - (status.end - ruby.end)
                        ]
                        + status.close()
                        + ruby.rt()
                        + ruby.close()
                        + status.open()
                        + self._highlighted[ruby.end : status.end]
                        + status.close()
                        + self._highlighted[status.end :]
                    )
                    status = None

                    # Pull and process statuses until the next status is outside of this ruby.
                    while self.statuses:
                        if self.statuses[-1].end <= ruby.start:
                            break

                        status = self.statuses.pop()
                        status.start += ruby.open_len()
                        status.end += ruby.open_len()
                        self._highlighted = status.inject(self._highlighted)

                elif isinstance(ruby, TextRubyRange):
                    debug_utils.dev_print("text path")
                    status.status = "undefined"
                    self._highlighted = (
                        self._highlighted[: ruby.start]
                        + status.open()
                        + str(ruby)
                        + self._highlighted[ruby.end : status.end]
                        + status.close()
                        + self._highlighted[status.end :]
                    )
                    status = None

                    # Pull and process statuses until the next status is outside of this ruby.
                    while self.statuses:
                        if self.statuses[-1].end <= ruby.start:
                            break

                        status = self.statuses.pop()

                ruby = None
                status = None
                continue

            debug_utils.dev_print(
                "Made it past all possible cases. This should not be possible."
            )

            # Just in case, to prevent infinite loop, we're disposing of the current pieces
            ruby = None
            status = None


class MorphAndStatus:
    """A class to track morpheme data relevant to highlighting."""

    def __init__(
        self,
        morpheme: Morpheme,
        evaluate_morph_inflection: bool,
        interval_for_known_morphs: int,
    ):
        self.morph = morpheme.inflection.lower()
        self.status = MorphAndStatus.get_status_for_morph(
            morpheme,
            evaluate_morph_inflection,
            interval_for_known_morphs,
        )

    @staticmethod
    def get_status_for_morph(
        morpheme: Morpheme,
        evaluate_morph_inflection: bool,
        interval_for_known_morphs: int,
    ) -> str:
        """Get the morpheme's status. Use the relevant interval based on the user's config."""

        if evaluate_morph_inflection:
            learning_interval = getattr(
                morpheme, "highest_inflection_learning_interval", 0
            )
        else:
            learning_interval = getattr(morpheme, "highest_lemma_learning_interval", 0)

        if learning_interval == 0:
            return "unknown"

        if learning_interval < interval_for_known_morphs:
            return "learning"

        return "known"


def get_highlighted_text(
    am_config: AnkiMorphsConfig,
    morphemes: list[Morpheme],
    text: str,
    use_html_rubies: bool = False,
) -> str:
    """Highlight a text string based on found morphemes. Supports rubies.
    See test cases for exhaustive examples."""

    debug_utils.dev_print(f"input text: {text}")

    morphs_and_statuses = [
        MorphAndStatus(
            morpheme,
            am_config.evaluate_morph_inflection,
            am_config.interval_for_known_morphs,
        )
        for morpheme in morphemes
    ]

    debug_utils.dev_print_morphs(morphemes)

    ruby_range_type: type[RubyRange] = TextRubyRange
    if use_html_rubies:
        ruby_range_type = HtmlRubyRange

    highlighted_text = TextHighlighter(
        text, morphs_and_statuses, ruby_range_type
    ).highlighted()

    debug_utils.dev_print(f"output text: {highlighted_text}")
    debug_utils.dev_print("")

    return highlighted_text
