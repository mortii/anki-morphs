from __future__ import annotations

import re
from collections import deque

from . import text_preprocessing
from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme


class SpanElement:

    def __init__(
        self, morph_group: str, morph_status: str, start_index: int, end_index: int
    ):
        # it's crucial that the morph_group parameter originates from Match[str].group()
        # because that maintains the original letter casing, which we want to preserve
        # in the highlighted version of the text.
        self.morph_group: str = morph_group
        self.morph_status: str = morph_status
        self.start_index: int = start_index
        self.end_index: int = end_index


def get_highlighted_text(
    am_config: AnkiMorphsConfig,
    card_morphs: list[Morpheme],
    text_to_highlight: str,
) -> str:
    # To highlight morphs based on their learning status, we wrap them in html span elements.
    # The problem with this approach is that injecting html between morphs can break the functionality
    # of ruby characters (https://docs.ankiweb.net/templates/fields.html#ruby-characters).
    #
    # To prevent that problem, we have to first have to iterate over the string and extract the ruby characters
    # and return the filtered string. Next, we can run almost the same procedure with the found morphs: extract
    # them and filter the string. Once both of these passes are completed, we are left with a string that
    # only has non-word characters and text that did not match any morphs.
    #
    # Take, for example, the following (contrived) text:
    #   "Hello[ハロー] myy world!"
    #
    # The process would look like this:
    # 1. The "[ハロー]" part is found to be ruby characters and is therefore removed from the
    # string and stored in a dict along with its original position, leaving us with string:
    #   "Hello myy world!"
    #
    # 2. The words "Hello" and "world" are found to be morphs, and information about them and their original position
    # are stored as SpanElement objects in a list, and are then removed from the string and replaced
    # by whitespaces, leaving us with:
    #   "      myy      !"
    #
    # 3. We now have all the information we need to reassemble the string with the span elements that contain the morphs
    # and any ruby characters that directly followed them will be included in the spans.
    #
    # The final highlighted string could end up looking something like this:
    #   "<span morph-status="known">Hello[ハロー]</span> myy <span morph-status="unknown">world</span>!"

    # print(f"text_to_highlight: {text_to_highlight}")
    # print(f"text_to_highlight list: {list(text_to_highlight)}")

    ruby_character_dict, text_to_highlight = _extract_ruby_characters_and_filter_string(
        am_config, text_to_highlight
    )
    span_elements, text_to_highlight = _extract_span_elements_and_filter_string(
        am_config, card_morphs, text_to_highlight
    )
    # sorting the spans allows for iteration by a single index instead of looping
    # through the list every time we want to find an element
    span_elements.sort(key=lambda span: span.start_index)

    # the string has now been sufficiently stripped and split into its constituent parts,
    # and we can now reassemble it
    highlighted_text_list: list[str] = []
    index: int = 0
    previous_span_index: int = -1

    while index < len(text_to_highlight):

        span_element: SpanElement | None = _get_span_element(
            span_elements, previous_span_index
        )
        if (
            span_element is not None
            and span_element.start_index <= index < span_element.end_index
        ):
            span_string = span_element.morph_group

            if len(ruby_character_dict) > 0:
                # we need to do this in reverse order to preserve the indices
                global_string_index = span_element.end_index
                # this substring index is offset by +1 because it is used for string splicing
                sub_string_index = len(span_string)

                while global_string_index > span_element.start_index:
                    if global_string_index in ruby_character_dict:
                        span_string = (
                            span_string[:sub_string_index]
                            + ruby_character_dict[global_string_index]
                            + span_string[sub_string_index:]
                        )
                        # this entry is not needed anymore
                        del ruby_character_dict[global_string_index]

                    global_string_index -= 1
                    sub_string_index -= 1

            span_string = (
                f'<span morph-status="{span_element.morph_status}">{span_string}</span>'
            )
            highlighted_text_list.append(span_string)
            index = span_element.end_index

            # keep the index within range
            if previous_span_index < len(span_elements) - 2:
                previous_span_index += 1

        else:
            non_span_string = text_to_highlight[index]
            if len(ruby_character_dict) > 0:
                # add any ruby characters found in the subsequent index.
                # note: it can seem unnecessarily complicated to append
                # the ruby character in this else branch, but since the
                # if branch above can potentially also trigger on the
                # subsequent index _and_ that takes priority, it means that
                # this next ruby character might never be reached unless
                # we do it here.
                next_index = index + 1
                if next_index in ruby_character_dict:
                    non_span_string += ruby_character_dict[next_index]
                    # this entry is not needed anymore
                    del ruby_character_dict[next_index]

            highlighted_text_list.append(non_span_string)
            index += 1

    # print(f'highlighted text: {"".join(highlighted_text_list)}')
    return "".join(highlighted_text_list)


def _extract_ruby_characters_and_filter_string(
    am_config: AnkiMorphsConfig, text_to_highlight: str
) -> tuple[dict[int, str], str]:
    ruby_character_dict: dict[int, str] = {}

    # most users probably don't have ruby characters on their cards,
    # so we only want to do all this extra work of extracting and replacing
    # if they have activated the relevant pre-process option
    if not am_config.preprocess_ignore_bracket_contents:
        return ruby_character_dict, text_to_highlight

    while True:
        # matches first found, left to right
        match: re.Match[str] | None = re.search(
            text_preprocessing.square_brackets_regex, text_to_highlight
        )
        if match is None:
            break

        ruby_character_dict[match.start()] = match.group()

        # remove the found match from the string and repeat
        text_to_highlight = (
            text_to_highlight[: match.start()] + text_to_highlight[match.end() :]
        )

    return ruby_character_dict, text_to_highlight


def _extract_span_elements_and_filter_string(
    am_config: AnkiMorphsConfig, card_morphs: list[Morpheme], text_to_highlight: str
) -> tuple[list[SpanElement], str]:
    span_elements: list[SpanElement] = []

    # To avoid formatting a smaller morph contained in a bigger morph, we reverse sort
    # the morphs based on length and extract those first.
    morphs_by_size = sorted(
        card_morphs,
        key=lambda _simple_morph: len(_simple_morph.inflection),
        reverse=True,
    )

    for morph in morphs_by_size:
        # print(f"morph: {morph.lemma}, {morph.inflection}")
        learning_interval: int

        if am_config.evaluate_morph_inflection:
            learning_interval = getattr(morph, "highest_inflection_learning_interval")
        else:
            learning_interval = getattr(morph, "highest_lemma_learning_interval")

        assert learning_interval is not None

        if learning_interval == 0:
            morph_status = "unknown"
        elif learning_interval < am_config.interval_for_known_morphs:
            morph_status = "learning"
        else:
            morph_status = "known"

        # escaping special regex characters is crucial because morphs from malformed text
        # sometimes can include them, e.g. "?몇"
        regex_pattern: str = f"{re.escape(morph.inflection)}"
        morph_matches = re.finditer(
            regex_pattern, text_to_highlight, flags=re.IGNORECASE
        )

        for morph_match in morph_matches:
            start_index = morph_match.start()
            end_index = morph_match.end()
            morph_len = end_index - start_index

            # the morph_match.group() maintains the original letter casing of the
            # morph found in the text, which is crucial because we want everything
            # to be identical to the original text.
            span_elements.append(
                SpanElement(morph_match.group(), morph_status, start_index, end_index)
            )

            # we need to preserve indices, so we replace the morphs with whitespaces
            text_to_highlight = (
                text_to_highlight[:start_index]
                + "".join([" " for _ in range(morph_len)])
                + text_to_highlight[end_index:]
            )

    return span_elements, text_to_highlight


def _get_span_element(
    span_elements: list[SpanElement], previous_span_index: int
) -> SpanElement | None:
    try:
        return span_elements[previous_span_index + 1]
    except IndexError:
        # This exception should only happen when the span_elements
        # list is empty, which should be a rare occurrence. Catching
        # a rare exception is more efficient than checking with an
        # if statement every time.
        return None


class Range:
    """Base class for Ranges."""

    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end


class RubyRange(Range):
    """Represents a ruby and its range in parent string."""

    def __init__(self, start: int, end: int, kanji: str, kana: str):
        super().__init__(start, end)
        self.kanji = kanji
        self.kana = kana

    def prefix_len(self) -> int:
        return len("<ruby>")

    def open(self) -> str:
        return "<ruby>"

    def close(self) -> str:
        return "</ruby>"

    def rt(self) -> str:
        return f"<rt>{self.kana}</rt>"

    def rt_offset(self) -> int:
        return len(self.kanji) - 1

    def inject(self, text: str) -> str:
        return text[: self.start] + str(self) + text[self.end :]

    def __str__(self) -> str:
        return f"<ruby>{self.kanji}<rt>{self.kana}</rt></ruby>"

    def __repr__(self) -> str:
        return f"Range: {self.start}-{self.end}. Value: {self.kanji}[{self.kana}]."


class StatusRange(Range):
    """Represents a morph's status and range in parent string."""

    def __init__(self, start: int, end: int, status: str):
        super().__init__(start, end)
        self.status = status

    def open_len(self) -> int:
        """Len of the open tag, useful for setting string splice offsets."""
        return len(self.open())

    def open(self) -> str:
        return f'<span morph-status="{self.status}">'

    def close(self) -> str:
        return "</span>"

    def inject(self, text: str) -> str:
        """Put this morph into the given string."""

        return (
            text[: self.start]
            + self.open()
            + text[self.start : self.end]
            + self.close()
            + text[self.end :]
        )

    def __repr__(self) -> str:
        return f"Range: {self.start}-{self.end}. Status: {self.status}."


class Expression:
        """Represents an expression to highlight. Tracks 2 sets of data, one for rubies the other 
        for morph status. all the magic happens in _process() where we merge them together on top 
        of the base string."""

    def __init__(self, text: str, morph_metas: list[MorphemeMeta]):
        self._highlighted: str | None = None
        self.no_rubies: str = text
        self.rubies: deque[RubyRange] = deque()
        self.statuses: deque[StatusRange] = deque()

        self._tag_rubies()
        self._tag_morphemes(self.no_rubies.lower(), morph_metas)

    def _tag_rubies(self) -> None:
        """Populate internal deque of found ruby locations."""

        while True:
            match = re.search(text_preprocessing.ruby_regex, self.no_rubies)

            if not match:
                break

            self.rubies.append(
                RubyRange(
                    match.start(),
                    match.start() + len(match.group(1)),
                    match.group(1),
                    match.group(2),
                )
            )
            self.no_rubies = (
                self.no_rubies[: match.start()]
                + match.group(1)
                + self.no_rubies[match.end() :]
            )

    def _tag_morphemes(self, haystack: str, morph_metas: list[MorphemeMeta]) -> None:
        """Populate internal deque of found morph locations."""

        for morph_meta in sorted(
            morph_metas, key=lambda meta: len(meta.text), reverse=True
        ):
            while True:
                start = haystack.find(morph_meta.text)

                if start == -1:
                    break

                end = start + len(morph_meta.text)

                self.statuses.append(StatusRange(start, end, morph_meta.status))
                haystack = haystack[:start] + (" " * (end - start)) + haystack[end:]

        self.statuses = deque(sorted(self.statuses, key=lambda range: range.start))

    def highlighted(self) -> str:
        """Get the highlighted string. Pull from cache if present."""

        if not self._highlighted:
            self._highlighted = self.no_rubies or ""

            if self._highlighted and (self.rubies or self.statuses):
                self._process()

        return self._highlighted

    def _process(self) -> None:  # pylint:disable=too-many-branches, too-many-statements
        """Process the text in self._highlighted, now that all the metadata has been gathered."""

        ruby: RubyRange | None = None
        stat: StatusRange | None = None

        while self._highlighted is not None:
            if ruby is None and self.rubies:
                ruby = self.rubies.pop()

            if stat is None and self.statuses:
                stat = self.statuses.pop()

            if ruby is None and stat is None:
                break

            # If there are only statuses.
            #
            if ruby is None:
                # print("There are only statuses.")
                self._highlighted = stat.inject(self._highlighted)  # type: ignore[union-attr]
                stat = None
                continue

            # If there are only rubies.
            #
            if stat is None:
                # print("There are only rubies.")
                self._highlighted = ruby.inject(self._highlighted)
                ruby = None
                continue

            # If there is no overlap between ruby and status, process the latest one.
            #
            if ruby.end <= stat.start or ruby.start >= stat.end:
                # print("There is no overlap between ruby and status.")
                if ruby.start > stat.start:
                    self._highlighted = ruby.inject(self._highlighted)
                    ruby = None
                else:
                    self._highlighted = stat.inject(self._highlighted)
                    stat = None
                continue

            # If the status is the same as the ruby
            #
            if ruby.start == stat.start and ruby.end == stat.end:
                # print("The status is the same as the ruby.")
                self._highlighted = (
                    self._highlighted[: stat.start]
                    + stat.open()
                    + str(ruby)
                    + stat.close()
                    + self._highlighted[stat.end :]
                )
                ruby = None
                stat = None
                continue

            # If the ruby is completely inside the status
            #
            if ruby.start >= stat.start and ruby.end <= stat.end:
                # print("The ruby is completely inside the status.")
                self._highlighted = (
                    self._highlighted[: stat.start]
                    + stat.open()
                    + self._highlighted[
                        stat.start : stat.start + ruby.start - stat.start
                    ]
                    + str(ruby)
                    + self._highlighted[ruby.end : stat.end]
                    + stat.close()
                    + self._highlighted[stat.end :]
                )
                ruby = None

                # Pull and process rubies until the next ruby is outside of this status.
                #
                while self.rubies:
                    if self.rubies[-1].end <= stat.start:
                        break

                    ruby = self.rubies.pop()
                    ruby.start += stat.open_len()
                    ruby.end += stat.open_len()
                    self._highlighted = ruby.inject(self._highlighted)

                stat = None
                ruby = None

                continue

            # If the status is completely inside the ruby
            #
            if ruby.start <= stat.start and ruby.end >= stat.end:
                # print("The status is completely inside the ruby.")
                self._highlighted = ruby.inject(self._highlighted)
                stat.start += ruby.prefix_len()
                stat.end += ruby.prefix_len()
                self._highlighted = stat.inject(self._highlighted)
                stat = None

                # Pull and process statuses until the next status is outside of this ruby.
                #
                while self.statuses:
                    if self.statuses[-1].end <= ruby.start:
                        break

                    stat = self.statuses.pop()
                    stat.start += ruby.prefix_len()
                    stat.end += ruby.prefix_len()
                    self._highlighted = stat.inject(self._highlighted)

                ruby = None
                stat = None
                continue

            # If the ruby starts then status starts, ruby ends, status ends
            #
            if ruby.start < stat.start and ruby.end < stat.end:
                # print("The ruby starts then status starts, ruby ends, status ends.")
                self._highlighted = (
                    self._highlighted[: ruby.start]
                    + ruby.open()
                    + self._highlighted[ruby.start : stat.start]
                    + stat.open()
                    + self._highlighted[
                        stat.start : stat.start
                        + (stat.end - stat.start)
                        - (stat.end - ruby.end)
                    ]
                    + stat.close()
                    + ruby.rt()
                    + ruby.close()
                    + stat.open()
                    + self._highlighted[ruby.end : stat.end]
                    + stat.close()
                    + self._highlighted[stat.end :]
                )

                stat = None

                # Pull and process statuses until the next status is outside of this ruby.
                #
                while self.statuses:
                    if self.statuses[-1].end <= ruby.start:
                        break

                    stat = self.statuses.pop()
                    stat.start += ruby.prefix_len()
                    stat.end += ruby.prefix_len()
                    self._highlighted = stat.inject(self._highlighted)

                ruby = None
                stat = None
                continue

            # If the status starts then ruby starts, status ends, ruby ends
            #
            if ruby.start > stat.start and ruby.end > stat.end:
                # print("The status starts then ruby starts, status ends, ruby ends.")
                self._highlighted = (
                    self._highlighted[: stat.start]
                    + stat.open()
                    + self._highlighted[stat.start : ruby.start]
                    + stat.close()
                    + ruby.open()
                    + stat.open()
                    + self._highlighted[ruby.start : ruby.start + ruby.rt_offset()]
                    + stat.close()
                    + self._highlighted[stat.end : ruby.end]
                    + ruby.rt()
                    + ruby.close()
                    + self._highlighted[ruby.end :]
                )
                ruby = None
                stat = None
                continue

            # print("errrr what the what?")


class MorphemeMeta:
    """A class to track morpheme data relevant to highlighting."""

    def __init__(self, morpheme: Morpheme, am_config: AnkiMorphsConfig):
        self.text = (
            morpheme.inflection
            if am_config.evaluate_morph_inflection
            else morpheme.lemma
        ).lower()

        self.status = MorphemeMeta.get_morph_status(
            (
                getattr(morpheme, "highest_inflection_learning_interval", 0)
                if am_config.evaluate_morph_inflection
                else getattr(morpheme, "highest_lemma_learning_interval", 0)
            ),
            am_config.interval_for_known_morphs,
        )

    @staticmethod
    def get_morph_status(
        learning_interval: int,
        interval_for_known_morphs: int,
    ) -> str:
        """Get the morpheme's status. Use the relevant interval based on the user's config."""

        if learning_interval == 0:
            return "unknown"

        if learning_interval < interval_for_known_morphs:
            return "learning"

        return "known"


def alt_get_highlighted_text(
    am_config: AnkiMorphsConfig,
    morphemes: list[Morpheme],
    text: str,
) -> str:
    """Highlight a text string based on found morphemes. Supports rubies.
    See test cases for exhaustive examples."""

    return Expression(
        text, [MorphemeMeta(morpheme, am_config) for morpheme in morphemes]
    ).highlighted()
