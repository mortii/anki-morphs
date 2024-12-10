from __future__ import annotations

import re

import anki
from anki.template import TemplateRenderContext

from . import ankimorphs_config, ankimorphs_globals, text_preprocessing
from .ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from .ankimorphs_db import AnkiMorphsDB
from .morpheme import Morpheme
from .morphemizers import morphemizer as morphemizer_module
from .morphemizers import spacy_wrapper
from .morphemizers.morphemizer import Morphemizer, SpacyMorphemizer


def highlight_morphs_jit(
    field_text: str,
    field_name: str,
    filter_name: str,
    context: TemplateRenderContext,
) -> str:
    """Use morph learning progress to decorate the morphemes in the supplied text.
    Adds css classes to the output that can be styled in the card."""

    # Perf: Bail early if the user attempts to use this template filter on the already
    # formatted data.
    #
    if (
        filter_name != "am-highlight"
        or field_name == ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
    ):
        return field_text

    am_config_filter: AnkiMorphsConfigFilter | None = (
        ankimorphs_config.get_matching_filter(context.note())
    )

    if am_config_filter is None:
        return field_text

    morphemizer: Morphemizer | None = morphemizer_module.get_morphemizer_by_description(
        am_config_filter.morphemizer_description
    )

    if not morphemizer:
        return field_text

    am_config = AnkiMorphsConfig()

    card_morphs: list[Morpheme] = _get_morph_meta_for_text(
        morphemizer, field_text, am_config
    )

    if not card_morphs:
        return field_text

    return _rubify_with_status_fast(
        am_config,
        card_morphs,
        _dehtml(field_text),
    )


def _get_morph_meta_for_text(
    morphemizer: Morphemizer,
    field_text: str,
    am_config: AnkiMorphsConfig,
) -> list[Morpheme]:
    """Take in a string and gather the morphemes from it."""

    # If we were piped in after the `furigana` built-in filter, or if there is html in the source
    # data, we need to do some cleansing.
    #
    clean_text = _dehtml(field_text, am_config, True)

    if isinstance(morphemizer, SpacyMorphemizer):
        nlp = spacy_wrapper.get_nlp(
            morphemizer.get_description().removeprefix("spaCy: ")
        )

        morphs = text_preprocessing.get_processed_spacy_morphs(
            am_config, next(nlp.pipe([clean_text]))
        )
    else:
        morphs = text_preprocessing.get_processed_morphemizer_morphs(
            morphemizer, clean_text, am_config
        )

    morphs = list(set(morphs))

    if not morphs:
        return []

    with AnkiMorphsDB() as am_db:
        for morph in morphs:
            if am_config.evaluate_morph_inflection:
                morph.highest_inflection_learning_interval = (
                    am_db.get_highest_inflection_learning_interval(morph) or 0
                )
            else:
                morph.highest_lemma_learning_interval = (
                    am_db.get_highest_lemma_learning_interval(morph) or 0
                )

    return morphs


def _dehtml(
    text: str,
    am_config: AnkiMorphsConfig | None = None,
    clean_html: bool = False,
) -> str:
    """Prepare a string to be passed to a morphemizer. Specially process <ruby><rt> tags to extract
    kana to reconstruct kanji/kana ruby shorthand. Remove all html from the input string.
    """

    # Capture html ruby kana. The built in furigana filter will turn X[yz] into
    # <ruby><rb>X</rb><rt>yz</rt></ruby>, and if we blindly strip out all html we will loose
    # information on the kana Find <rt> tags and capture all text between them in a capture
    # group called kana, allow for any attributes or other decorations on the <rt> tag by
    # non-eagerly capturing all chars up to '>', so that the whole element can just be dropped.
    # non-eagerly capture one or more characters into the capture group named kana.
    #
    # Samples:
    # <ruby><rb>X</rb><rt>yz</rt></ruby> = " <ruby><rb>X</rb>[yz]</ruby>"
    # <ruby>X<rt>yz</rt></ruby> = " <ruby>X[yz]</ruby>"
    # <ruby>X<rt class='foo'>234</rt> = " <ruby>X[234]
    # <ruby>X<rt >>234</rt> = " <ruby>X[>234]
    # <ruby>X<rt></rt> = will not match
    #
    # ruby_longhand = r"(?P<ruby><ruby>)(?P<kanji>.*?)<rt[^>]*>(?P<kana>.+?)</rt>"
    ruby_longhand = r"(?:<ruby[^<]*>)(?:<rb>|.{0})(?P<kanji>.*?)(?:</rb>|.{0})<rt[^>]*>(?P<kana>.+?)</rt>(?P<after>.*?)(?:</ruby>)"

    # Emit the captured kana into square brackets, thus reconstructing the ruby shorthand "X[yz]".
    # Pad with a space so that we can retain the kanji/kana relationship
    #
    ruby_shorthand = r" \g<kanji>[\g<kana>]\g<after>"

    text = re.sub(ruby_longhand, ruby_shorthand, text, flags=re.IGNORECASE)

    if clean_html:
        text = anki.utils.strip_html(text)

    return text_preprocessing.get_processed_text(am_config, text) if am_config else text


def _make_unprocessed_regex() -> str:
    """Construct the regex for finding left over pieces of a part. Because this is run late in the
    process, the driver regex is different than the one in `make_morph_regex`."""

    # furigana_regex is a subpattern used to deal with rubies inside the target string.
    # 1 `(?![^\[]*\])`: A negative lookahead that ensures the pattern does not match inside square
    # brackets, preventing accidental matches inside rubies.
    # 2 `(?:\[.*?\]|.{0})`: A non-capturing group that matches:
    #     a Ruby inside square brackets (`\[.*?\]`)
    #     OR
    #     b An empty string (`.{0}`), effectively allowing for matches with no rubies present.
    #
    # So, furigana_regex matches either a ruby enclosed in square brackets or allows for zero
    # characters to match (empty match).

    # Finally, we surround the whole thing in lookaheads and lookbehinds. This will prevent us
    # from finding already processed morphs from prior iterations with some additional needs.
    #
    # f"(?<=/span>|<ruby>)(XXX)(?=<span|</ruby)"
    # The full regex pattern is wrapped in lookahead and lookbehind assertions where XXX is
    # described above.
    #
    # (?<=/span>|<ruby>): This is a positive lookbehind, ensuring that the pattern is
    # preceded by any sequence starting with /span> or <ruby>.
    #
    # (XXX): This is an unnamed capture group, which captures the pattern above.
    #
    # (?=<span|</ruby): This is a positive lookahead, which ensures that the pattern is followed
    # by the string <span> or </ruby. This covers off the cases where the first or last part
    # is unprocessed.

    # Matching Examples
    # <ruby>abc</ruby>
    # <ruby>abc[kana]</ruby>
    # <ruby>abc<span>other morph</span></ruby>
    # <ruby>abc[kana]<span>other morph</span></ruby>

    # Non-Matching Examples
    # <div>abc[kana]</div>
    # <span>abc</span>
    # abc[kana]

    return r"<span.*?</span>|<rt.*?</rt>|<[^<]*>|([^<]*)"


class Range:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end


class RubyRange(Range):
    def __init__(self, start: int, end: int, kanji: str, kana: str):
        super().__init__(start, end)
        self.kanji = kanji
        self.kana = kana

    def prefix_len(self) -> int:
        return len("<ruby>")

    def open(self) -> str:
        return f"<ruby>"

    def close(self) -> str:
        return "</ruby>"

    def rt(self) -> str:
        return f"<rt>{self.kana}</rt>"

    def rt_offset(self) -> int:
        return len(self.kanji) - 1

    def __str__(self) -> str:
        return f"<ruby>{self.kanji}<rt>{self.kana}</rt></ruby>"

    def __repr__(self) -> str:
        return f"Range: {self.start}-{self.end} => {self.kanji}[{self.kana}]."


class StatusRange(Range):
    def __init__(self, start: int, end: int, status: str):
        super().__init__(start, end)
        self.status = status

    def open(self) -> str:
        return f'<span morph-status="{self.status}">'

    def close(self) -> str:
        return "</span>"

    def __repr__(self) -> str:
        return f"Range: {self.start}-{self.end}. Status: {self.status}."


class Whole:
    def __init__(self, string: str, morph_metas: list[MorphemeMeta]):
        self._highlighted: str | None = None
        self.no_rubies: str = string
        self.rubies: list[RubyRange] = []
        self.statuses: list[StatusRange] = []

        self._tag_rubies()
        self._tag_morphemes(self.no_rubies.lower(), morph_metas)

    def _tag_rubies(self) -> None:
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

    def _tag_morphemes(
        self, status_matcher: str, morph_metas: list[MorphemeMeta]
    ) -> None:
        for morph_meta in sorted(
            morph_metas, key=lambda meta: len(meta.string), reverse=True
        ):
            while True:
                start = status_matcher.find(morph_meta.string)

                if start == -1:
                    break

                end = start + len(morph_meta.string)

                self.statuses.append(StatusRange(start, end, morph_meta.status))
                status_matcher = (
                    status_matcher[:start]
                    + (" " * (end - start))
                    + status_matcher[end:]
                )

            self.statuses = sorted(self.statuses, key=lambda range: range.start)

    def highlighted(self) -> str | None:
        if self._highlighted:
            return self._highlighted

        self._highlighted = self.no_rubies

        if self.rubies or self.statuses:
            self._process()

        return self._highlighted

    def _process(self) -> None:
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
                print("There are only statuses.")
                self._highlighted = (
                    self._highlighted[: stat.start]
                    + stat.open()
                    + self.no_rubies[stat.start : stat.end]
                    + stat.close()
                    + self._highlighted[stat.end :]
                )
                stat = None
                continue

            # If there are only rubies.
            #
            if stat is None:
                print("There are only rubies.")
                self._highlighted = (
                    self._highlighted[: ruby.start]
                    + str(ruby)
                    + self._highlighted[ruby.end :]
                )
                ruby = None
                continue

            # If there is no overlap between ruby and status, process the latest one.
            #
            if ruby.end <= stat.start or ruby.start >= stat.end:
                print("There is no overlap between ruby and status.")
                if ruby.start > stat.start:
                    print("Ruby is later.")
                    self._highlighted = (
                        self._highlighted[: ruby.start]
                        + str(ruby)
                        + self._highlighted[ruby.end :]
                    )
                    ruby = None
                else:
                    print("Status is later.")
                    self._highlighted = (
                        self._highlighted[: stat.start]
                        + stat.open()
                        + self.no_rubies[stat.start : stat.end]
                        + stat.close()
                        + self._highlighted[stat.end :]
                    )
                    stat = None
                continue

            # If the status is the same as the ruby
            #
            if ruby.start == stat.start and ruby.end == stat.end:
                print("The status is the same as the ruby.")

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
                print("The ruby is completely inside the status.")
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
                        stat = None
                        break
                    else:
                        ruby = self.rubies.pop()
                        ruby.start += len(stat.open())
                        ruby.end += len(stat.open())
                        self._highlighted = (
                            self._highlighted[: ruby.start]
                            + str(ruby)
                            + self._highlighted[ruby.end :]
                        )
                stat = None
                ruby = None
                continue

            # If the status is completely inside the ruby
            #
            if ruby.start <= stat.start and ruby.end >= stat.end:
                print("The status is completely inside the ruby.")
                self._highlighted = (
                    self._highlighted[: ruby.start]
                    + str(ruby)
                    + self._highlighted[ruby.end :]
                )
                stat.start += ruby.prefix_len()
                stat.end += ruby.prefix_len()
                self._highlighted = (
                    self._highlighted[: stat.start]
                    + stat.open()
                    + self._highlighted[stat.start : stat.end]
                    + stat.close()
                    + self._highlighted[stat.end :]
                )
                stat = None

                # Pull and process statuses until the next status is outside of this ruby.
                #
                while self.statuses:
                    print("next")
                    if self.statuses[-1].end <= ruby.start:
                        print("out")
                        ruby = None
                        break
                    else:
                        print("in")
                        stat = self.statuses.pop()
                        stat.start += ruby.prefix_len()
                        stat.end += ruby.prefix_len()
                        self._highlighted = (
                            self._highlighted[: stat.start]
                            + stat.open()
                            + self._highlighted[stat.start : stat.end]
                            + stat.close()
                            + self._highlighted[stat.end :]
                        )
                ruby = None
                stat = None
                continue

            # If the ruby starts then status starts, ruby ends, status ends
            #
            if ruby.start < stat.start and ruby.end < stat.end:
                print("The ruby starts then status starts, ruby ends, status ends.")
                print(self._highlighted)
                print(ruby)
                print(stat)
                print(ruby.start)
                print(stat.start)
                print(ruby.end)
                print(stat.end)
                self._highlighted = (
                    self._highlighted[: ruby.start]
                    + ruby.open()
                    + self._highlighted[ruby.start : stat.start]
                    + stat.open()
                    + self._highlighted[stat.start : stat.start + ruby.rt_offset()]
                    + stat.close()
                    + ruby.rt()
                    + ruby.close()
                    + stat.open()
                    + self._highlighted[ruby.end : stat.end]
                    + stat.close()
                    + self._highlighted[stat.end :]
                )

                ruby = None
                stat = None
                continue

            # If the status starts then ruby starts, status ends, ruby ends
            #
            if ruby.start > stat.start and ruby.end > stat.end:
                print("The status starts then ruby starts, status ends, ruby ends.")
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

            print("errrr what the what?")


class MorphemeMeta:
    def __init__(self, morpheme: Morpheme, am_config: AnkiMorphsConfig):
        self.string = (
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
        self.regex = re.escape(self.string)

    @staticmethod
    def get_morph_status(
        learning_interval: int,
        interval_for_known_morphs: int,
    ) -> str:
        """Get the morpheme's text status. Use the relevant interval based on the user's config."""

        if learning_interval == 0:
            return "unknown"

        if learning_interval < interval_for_known_morphs:
            return "learning"

        return "known"


def _rubify_with_status_fast(
    am_config: AnkiMorphsConfig,
    morphemes: list[Morpheme],
    text: str,
) -> str:

    morph_metas: list[MorphemeMeta] = [
        MorphemeMeta(morpheme, am_config) for morpheme in morphemes
    ]

    return Whole(text, morph_metas).highlighted()


def _rubify_with_status(
    am_config: AnkiMorphsConfig,
    morphemes: list[Morpheme],
    text: str,
) -> str:
    """Split the incoming string into parts to be processed, after processing, join them back
    together with newlines. Each split part will become an html ruby. This allows the complex
    interaction between furigana notation and morpheme detection to work in harmony. Present
    each of the found parts to the function that will do the work.
    """

    morph_metas: list[MorphemeMeta] = [
        MorphemeMeta(morpheme, am_config) for morpheme in morphemes
    ]

    # Sort morphemes by their length, descending. We do this so that we do not find shorter morphs
    # inside larger ones. Use the configuration to see how the user wants to sort (by lemma or inflection).
    morph_metas = sorted(morph_metas, key=lambda meta: len(meta.string), reverse=True)

    return "\n".join(
        [
            _rubify_part_with_status(part, morph_metas)
            for part in text.split(" ")
            if part
        ]
    )


def _make_morph_ruby(match_text: str, status: str) -> str:
    """Format match text with a morph status. Wrap it in a span to indicate the morph-status. If
    a ruby is present, escape out of the new span for the ruby, then start a new one for the rest
    of the contents."""

    morph_status = f' morph-status="{status}"'
    # Similar to other furigana_regex, except capture the kana so it can be added to the <rt> tags.
    #
    furigana = r"(?![^\[]*\])\[(?P<kana>.*?)\]"
    ruby = rf"<rt{morph_status}>\g<kana></rt>"
    status_span_open = f"<span{morph_status}>"
    status_span_close = "</span>"

    # Replace all occurrences of kana in this piece, annotating with the status supplied. Note
    # that we need to "pop out" of the current span so that the <rt> tags can apply to the outer
    # <ruby> for the part.
    #
    (morph_ruby, match_count) = re.subn(
        furigana,
        status_span_close + ruby + status_span_open,
        match_text,
        flags=re.IGNORECASE,
    )

    # Always wrap this piece in a status span.
    #
    # If we made no other changes, then return the original match_text, else we'll have left over
    # cruft (in the form of span tags) we dont need from our regex attempt.
    #
    return (
        (
            status_span_open
            + (morph_ruby if match_count > 0 else match_text)
            + status_span_close
        )
        .removeprefix(f"{status_span_open}{status_span_close}")
        .removesuffix(f"{status_span_open}{status_span_close}")
    )


def _rubify_part_with_status(text: str, morph_metas: list[MorphemeMeta]) -> str:
    """Take in a part for processing, find all morphemes in this part and format them. Wrap the
    entire part in a ruby. Post-process to tag all pieces that do not have a morpheme.
    """

    for morph_meta in morph_metas:
        # Reverse sort the matches so we can replace safely.
        #
        # Make a specially crafted regex for this morpheme and test for it.
        #
        for match in reversed(
            list(re.finditer(morph_meta.regex, text, flags=re.IGNORECASE))
        ):

            if match.group(1):
                # If found, format it, and splice it back into the source string.
                #
                text = (
                    text[: match.start()]
                    + _make_morph_ruby(match.group(1), morph_meta.status)
                    + text[match.end() :]
                )

    # Final pass, find all unprocessed pieces in the part, and tag them, in case our user wants
    # to style them. This typically includes punctuation and proper nouns.
    #
    for match in reversed(
        list(re.finditer(_make_unprocessed_regex(), text, flags=re.IGNORECASE))
    ):
        if match.group(1):
            text = (
                text[: match.start()]
                + _make_morph_ruby(match.group(1), "unprocessed")
                + text[match.end() :]
            )

    # Wrap the morphs we matched ruby tags. This is the magic that lets rubies and morphemes play
    # nice.
    #
    # Look for anything not processed already. That'll be html. Make sure it's outside our ruby
    # tags. Bit of a hack to remove </ruby><ruby>, but to do that just in regex would be
    # incredibly opaque.
    #
    return re.sub(
        r"(<span morph-status.*?</span>(?!<span)|<rt.*?</rt>(?!<rt))",
        r"<ruby>\1</ruby>",
        text,
    ).replace("</ruby><ruby>", "")
