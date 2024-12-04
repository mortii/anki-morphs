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

    card_morphs: list[Morpheme] = get_morphemes(morphemizer, field_text, am_config)

    if not card_morphs:
        return field_text

    return rubify_with_status(
        am_config,
        card_morphs,
        dehtml(field_text),
    )


def get_morphemes(
    morphemizer: Morphemizer,
    field_text: str,
    am_config: AnkiMorphsConfig,
) -> list[Morpheme]:
    """Take in a string and gather the morphemes from it."""

    # If we were piped in after the `furigana` built-in filter, or if there is html in the source
    # data, we need to do some cleansing.
    #
    clean_text = dehtml(
        field_text,
        am_config.preprocess_ignore_bracket_contents,
        am_config.preprocess_ignore_round_bracket_contents,
        am_config.preprocess_ignore_slim_round_bracket_contents,
        True,
    )

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

    if am_config.preprocess_ignore_names_morphemizer:
        morphs = text_preprocessing.remove_names_morphemizer(morphs)

    if am_config.preprocess_ignore_names_textfile:
        morphs = text_preprocessing.remove_names_textfile(morphs)

    return update_morph_intervals(morphs, am_config)


def update_morph_intervals(
    morphs: list[Morpheme], am_config: ankimorphs_config.AnkiMorphsConfig
) -> list[Morpheme]:
    """Fetch just the data about the morphemes that are needed for the get_highlighted_text call."""

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


def dehtml(
    text: str,
    preprocess_ignore_bracket_contents: bool = False,
    preprocess_ignore_round_bracket_contents: bool = False,
    preprocess_ignore_slim_round_bracket_contents: bool = False,
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
        # Remove all other html tags. We do not want to forward these to the morphemizer.
        #
        text = anki.utils.strip_html(text)

    # Remove bracketed text if user specified not to process them.
    #
    skip_brackets = r"\[[^[]*\]|" if preprocess_ignore_bracket_contents else ""
    skip_parens = r"（[^（]*）|" if preprocess_ignore_round_bracket_contents else ""
    skip_slim_parens = (
        r"\([^(]*\)|" if preprocess_ignore_slim_round_bracket_contents else ""
    )

    pattern = f"{skip_brackets}{skip_parens}{skip_slim_parens}"
    if pattern:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text


def make_unprocessed_regex() -> str:
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


class MorphemeMeta:
    def __init__(self, morpheme: Morpheme, am_config: AnkiMorphsConfig):
        self.string = (
            morpheme.inflection
            if am_config.evaluate_morph_inflection
            else morpheme.lemma
        )
        self.status = MorphemeMeta.get_morph_status(
            morpheme,
            am_config.evaluate_morph_inflection,
            am_config.interval_for_known_morphs,
        )
        self.regex = MorphemeMeta.make_morph_regex(
            self.string,
            am_config.preprocess_ignore_bracket_contents,
            am_config.preprocess_ignore_round_bracket_contents,
            am_config.preprocess_ignore_slim_round_bracket_contents,
        )

    @classmethod
    def get_morph_status(
        cls,
        morpheme: Morpheme,
        evaluate_morph_inflection: bool,
        interval_for_known_morphs: int,
    ) -> str:
        """Get the morpheme's text status. Use the relevant interval based on the user's config."""

        learning_interval = (
            getattr(morpheme, "highest_inflection_learning_interval")
            if evaluate_morph_inflection
            else getattr(morpheme, "highest_lemma_learning_interval")
        )

        if learning_interval == 0:
            return "unknown"

        if learning_interval < interval_for_known_morphs:
            return "learning"

        return "known"

    @classmethod
    def make_morph_regex(
        cls,
        morph: str,
        preprocess_ignore_bracket_contents: bool,
        preprocess_ignore_round_bracket_contents: bool,
        preprocess_ignore_slim_round_bracket_contents: bool,
    ) -> str:
        """Construct the regex for finding morphemes. Each morpheme gets a custom regex that
        interpolates the possibility of a ruby between each character."""

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

        # Then we create a new string by inserting the furigana_regex pattern between each character of
        # the morph string. For example, if morph is "abc", this would generate:
        #
        # a(?![^\[]*\])(?:\[.*?\]|.{0})b(?![^\[]*\])(?:\[.*?\]|.{0})c
        #
        # This ensures that each character is tested for, with the optional possibility that there is
        # a ruby in the middle (or on the end) of it.

        # Finally, we surround the whole thing in lookaheads and lookbehinds. This will prevent us
        # from finding already processed morphs from prior iterations.
        #
        # f"(?<![^/span]>)(XXX)(?!<span>)"
        # The full regex pattern is wrapped in lookahead and lookbehind assertions where XXX is
        # described above.
        #
        # (?<![^/span]>): This is a negative lookbehind, ensuring that the matched morpheme is not
        # preceded by any sequence starting with /span>.
        #
        # (XXX): This is an unnamed capture group, which captures the matched morpheme pattern above.
        #
        # (?!<span>): This is a negative lookahead, which ensures that the morpheme is not followed
        # by the string <span>. This further ensures that we're not inside a <span></span> pair, and
        # covers off some edge cases.

        # Matching Examples
        # "abc"
        # "a[kana]bc"
        # "ab[kana]c"
        # "abc[kana]"

        # Non-Matching Examples
        # "<span>abc</span>"
        # "<span>abc[kana]</span>"
        # "a<span>b</span>c"
        # "a[[kana]]b"
        # "[kana]abc"

        furigana_regex = r"(?![^\[]*\])(?:\[.*?\]|.{0})"
        skip_brackets = r"<rt.*?</rt>|" if preprocess_ignore_bracket_contents else ""
        skip_parens = r"（[^（]*）|" if preprocess_ignore_round_bracket_contents else ""
        skip_slim_parens = (
            r"\([^(]*\)|" if preprocess_ignore_slim_round_bracket_contents else ""
        )
        morph_regex = (
            furigana_regex.join([re.escape(morph_char) for morph_char in morph])
            + furigana_regex
        )
        return rf"<span.*?</span>|{skip_brackets}{skip_parens}{skip_slim_parens}({morph_regex})"


def rubify_with_status(
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
        [rubify_part_with_status(part, morph_metas) for part in text.split(" ") if part]
    )


def make_morph_ruby(match_text: str, status: str) -> str:
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


def rubify_part_with_status(text: str, morph_metas: list[MorphemeMeta]) -> str:
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
                    + make_morph_ruby(match.group(1), morph_meta.status)
                    + text[match.end() :]
                )

    # Final pass, find all unprocessed pieces in the part, and tag them, in case our user wants
    # to style them. This typically includes punctuation and proper nouns.
    #
    for match in reversed(
        list(re.finditer(make_unprocessed_regex(), text, flags=re.IGNORECASE))
    ):
        if match.group(1):
            text = (
                text[: match.start()]
                + make_morph_ruby(match.group(1), "unprocessed")
                + text[match.end() :]
            )

    # Wrap the whole part in a ruby tag. This is the magic that lets rubies and morphemes play
    # nice.
    #
    text = "<ruby>" + text + "</ruby>"

    return text
