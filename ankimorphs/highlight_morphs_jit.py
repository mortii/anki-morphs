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

    card_morphs: list[Morpheme] = get_morphemes(morphemizer, am_config, field_text)

    if not card_morphs:
        return field_text

    return rubify_with_status(dehtml(field_text, False), card_morphs, am_config)


def get_morphemes(
    morphemizer: Morphemizer,
    am_config: AnkiMorphsConfig,
    field_text: str,
) -> list[Morpheme]:
    """Take in a string and gather the morphemes from it."""

    # If we were piped in after the `furigana` built-in filter, or if there is html in the source
    # data, we need to do some cleansing.
    #
    clean_text = dehtml(field_text, am_config.preprocess_ignore_bracket_contents)

    if isinstance(morphemizer, SpacyMorphemizer):
        nlp = spacy_wrapper.get_nlp(
            morphemizer.get_description().removeprefix("spaCy: ")
        )

        all_morphs = text_preprocessing.get_processed_spacy_morphs(
            am_config, next(nlp.pipe([clean_text]))
        )
    else:
        all_morphs = text_preprocessing.get_processed_morphemizer_morphs(
            morphemizer, clean_text, am_config
        )

    return (
        update_morph_intervals(list(set(all_morphs)), am_config) if all_morphs else []
    )


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


def dehtml(text: str, preprocess_ignore_bracket_contents: bool) -> str:
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
    ruby_longhand = r"(?P<ruby><ruby>)(?P<kanji>.*?)<rt[^>]*>(?P<kana>.+?)</rt>"

    # Emit the captured kana into square brackets, thus reconstructing the ruby shorthand "X[yz]".
    # Pad with a space so that we can retain the kanji/kana relationship
    #
    ruby_shorthand = r" \g<ruby>\g<kanji>[\g<kana>]"

    # Remove all other html tags. We do not want to forward these to the morphemizer.
    #
    text = anki.utils.strip_html(re.sub(ruby_longhand, ruby_shorthand, text))

    # Remove brackets if user specified not to process them.
    #
    if preprocess_ignore_bracket_contents:
        text = re.sub(r"\[.*?\]", "", text)

    return text


def get_morph_status(
    morpheme: Morpheme, evaluate_morph_inflection: bool, interval_for_known_morphs: int
) -> str:
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


def sort_by_inflection_len(morphemes: list[Morpheme]) -> list[Morpheme]:
    return sorted(
        morphemes,
        key=lambda _morph: len(_morph.inflection),
        reverse=True,
    )


def make_morph_regex(morph: str) -> str:
    furigana_regex = r"(?![^\[]*\])(?:\[.*?\]|.{0})"
    return f"(?<![^/span]>)(?P<morph>{furigana_regex.join(morph) + furigana_regex})(?!<span>)"


def make_unprocessed_regex() -> str:
    furigana_regex = r"(?![^\[]*\])(?:\[.*?\]|.{0})"
    return f"(?<=/span>|<ruby>)(?P<unprocessed>[^>]+{furigana_regex})(?=<span|</ruby)"


def rubify_with_status(
    text: str,
    morphemes: list[Morpheme],
    am_config: AnkiMorphsConfig,
) -> str:
    return "\n".join(
        [
            rubify_part_with_status(part, morphemes, am_config)
            for part in text.split(" ")
            if part
        ]
    )


def make_morph_ruby(match_text: str, morph_status: str) -> str:
    morph_status_attr = f' morph-status="{morph_status}"'
    furigana = r"\[(?P<kana>.*?)\]"
    ruby = rf"<rt{morph_status_attr}>\g<kana></rt>"
    status_span_open = f"<span{morph_status_attr}>"
    status_span_close = "</span>"

    (morph_ruby, match_count) = re.subn(
        furigana,
        status_span_close + ruby + status_span_open,
        match_text,
    )

    return (
        status_span_open
        + (morph_ruby if match_count > 0 else match_text)
        + status_span_close
    )


def rubify_part_with_status(
    text: str,
    morphemes: list[Morpheme],
    am_config: AnkiMorphsConfig,
) -> str:

    for morpheme in sort_by_inflection_len(morphemes):
        morph_status = get_morph_status(
            morpheme,
            am_config.evaluate_morph_inflection,
            am_config.interval_for_known_morphs,
        )

        for match in reversed(
            list(re.finditer(make_morph_regex(morpheme.inflection), text))
        ):
            text = (
                text[: match.start()]
                + make_morph_ruby(match.group(0), morph_status)
                + text[match.end() :]
            )

    text = "<ruby>" + text + "</ruby>\n"

    for match in reversed(list(re.finditer(make_unprocessed_regex(), text))):
        text = (
            text[: match.start()]
            + make_morph_ruby(match.group(0), "unprocessed")
            + text[match.end() :]
        )

    return text
