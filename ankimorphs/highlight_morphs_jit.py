from __future__ import annotations

import re

import anki
from anki.template import TemplateRenderContext

from . import (
    ankimorphs_config,
    ankimorphs_globals,
    text_highlighting,
    text_preprocessing,
)
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

    return text_highlighting.get_highlighted_text(am_config, card_morphs, field_text)


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

        all_morphs = text_preprocessing.get_processed_spacy_morphs(
            am_config, next(nlp.pipe([clean_field_text]))
        )
    else:
        all_morphs = text_preprocessing.get_processed_morphemizer_morphs(
            morphemizer, clean_field_text, am_config
        )

    return (
        update_morph_intervals(list(set(all_morphs)), am_config) if all_morphs else []
    )


def update_morph_intervals(
    morphs: list[Morpheme], am_config: ankimorphs_config.AnkiMorphsConfig
) -> list[Morpheme]:

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


def dehtml(field_text: str) -> str:
    """Prepare a string to be passed to a morphemizer. Specially process <ruby><rt> tags to extract
    kana to reconstruct kanji/kana shorthand. Remove all html tags from an input string.
    """

    # Capture html ruby kana. The built in furigana filter will turn X[yz] into
    # <ruby><rb>X</rb><rt>yz</rt></ruby>, and if we strip out all html we will loose information
    # on the kana Find <rt> tags and capture all text between them in a capture group
    # called kana, allow for any attributes or other decorations on the <rt> tag by non-eagerly
    # capturing all chars up to '>', so that the whole element can just be dropped. non-eagerly
    # capture one or more characters into the capture group named kana.
    #
    # Samples:
    # <ruby><rb>X</rb><rt>yz</rt></ruby> = <ruby><rb>X</rb>[yz]</ruby>
    # <rt class='foo'>234</rt> = [234]
    # <rt >>234</rt> = [>234]
    # <rt></rt> = will not match
    #
    ruby_longhand = r"<rt[^>]*>(?P<kana>.+?)</rt>"

    # Emit the captured kana into square brackets.
    #
    ruby_shorthand = r"[\g<kana>]"

    return anki.utils.strip_html(
        re.sub(ruby_longhand, ruby_shorthand, field_text, re.MULTILINE)
    )
