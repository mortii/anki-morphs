from __future__ import annotations

import re

from anki.template import TemplateRenderContext

from .ankimorphs_config import (
    AnkiMorphsConfig,
    AnkiMorphsConfigFilter,
    get_matching_filter,
)
from .ankimorphs_db import AnkiMorphsDB
from .ankimorphs_globals import EXTRA_FIELD_HIGHLIGHTED
from .morpheme import Morpheme
from .morphemizers import spacy_wrapper
from .morphemizers.morphemizer import (
    Morphemizer,
    SpacyMorphemizer,
    get_morphemizer_by_description,
)
from .text_highlighting import get_highlighted_text
from .text_preprocessing import (
    get_processed_morphemizer_morphs,
    get_processed_spacy_morphs,
)


def am_highlight_morphs(
    field_text: str,
    field_name: str,
    filter_name: str,
    context: TemplateRenderContext,
) -> str:
    """Use morph learning progress to decorate the morphemes in the supplied text.
    Adds css classes to the output that can be styled in the card."""

    if filter_name != "am-highlight" or field_name == EXTRA_FIELD_HIGHLIGHTED:
        return field_text

    am_config_filter: AnkiMorphsConfigFilter | None = get_matching_filter(
        context.note()
    )

    if am_config_filter is None:
        return field_text

    morphemizer: Morphemizer | None = get_morphemizer_by_description(
        am_config_filter.morphemizer_description
    )

    if not morphemizer:
        return field_text

    am_config = AnkiMorphsConfig()

    card_morphs: list[Morpheme] = get_morphemes(morphemizer, am_config, field_text)

    if not card_morphs:
        return field_text

    return get_highlighted_text(am_config, card_morphs, field_text)


def get_morphemes(
    morphemizer: Morphemizer,
    am_config: AnkiMorphsConfig,
    field_text: str,
) -> list[Morpheme]:
    """Take in a string and gather the morphemes from it."""

    # If we were piped in after the `furigana` built-in filter, or if there is html in the source
    # data, we need to do some unpacking.
    #
    clean_field_text = dehtml(field_text)

    if isinstance(morphemizer, SpacyMorphemizer):
        nlp = spacy_wrapper.get_nlp(
            morphemizer.get_description().removeprefix("spaCy: ")
        )

        all_morphs = get_processed_spacy_morphs(
            am_config, next(nlp.pipe([clean_field_text]))
        )
    else:
        all_morphs = get_processed_morphemizer_morphs(
            morphemizer, clean_field_text, am_config
        )

    return get_morph_stats(list(set(all_morphs)), am_config)


def get_morph_stats(
    morphs: list[Morpheme], am_config: AnkiMorphsConfig
) -> list[Morpheme]:
    if not morphs:
        return []

    am_db = AnkiMorphsDB()

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


def dehtml(field_text: str) -> str:
    """Prepare a string to be passed to a morphemizer. Remove all html tags from an input string.
    Specially process <ruby><rt> tags to extract kana to reconstruct kanji/kana shorthand.
    """

    # Capture html ruby kana. Find <rt> tags and capture all text between them in a capture group
    # (kana), allow for any attributes or other decorations on the <rt> tag by non-eagerly
    # capturing all chars up to '>'. non eagerly capture one or more characters into kana.
    #
    ruby_longhand = r"<rt[^>]*>(?P<kana>.+?)</rt>"

    # Emit the captured kana into square brackets.
    #
    ruby_shorthand = r"[\g<kana>]"

    wrap_kana = re.sub(ruby_longhand, ruby_shorthand, field_text, re.MULTILINE)

    # Capture all angle bracketed characters.
    #
    all_html_tags = r"<[^>]*>"

    # Remove all angle bracketed characters. This effectively removes all html and leaves a
    # clean(er) string to pass to the morphemizer.

    return re.sub(all_html_tags, "", wrap_kana, re.MULTILINE)
