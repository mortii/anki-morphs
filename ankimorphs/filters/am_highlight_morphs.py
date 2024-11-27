from __future__ import annotations

import re

from anki.template import TemplateRenderContext

from ..ankimorphs_config import (
    AnkiMorphsConfig,
    AnkiMorphsConfigFilter,
    get_matching_read_filter,
)
from ..ankimorphs_db import AnkiMorphsDB
from ..ankimorphs_globals import EXTRA_FIELD_HIGHLIGHTED
from ..morpheme import Morpheme
from ..morphemizers import spacy_wrapper
from ..morphemizers.morphemizer import (
    Morphemizer,
    SpacyMorphemizer,
    get_morphemizer_by_description,
)
from ..text_highlighting import get_highlighted_text
from ..text_preprocessing import (
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

    if filter_name != "am-highlight-morphs" or field_name == EXTRA_FIELD_HIGHLIGHTED:
        return field_text

    am_config_filter: AnkiMorphsConfigFilter | None = get_matching_read_filter(
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
    am_db = AnkiMorphsDB()

    # If we were piped in after the `furigana` built-in filter, we
    # need to do some unpacking.
    #
    derubified_field_text = dehtml(field_text)

    card_morphs: list[Morpheme] = get_morphemes(
        morphemizer, am_config, am_db, derubified_field_text
    )

    if not card_morphs:
        return field_text

    field_text = get_highlighted_text(am_config, card_morphs, field_text)

    return (
        field_text
        if not am_config.preprocess_ignore_bracket_contents
        else rubify(field_text)
    )


def get_morphemes(
    morphemizer: Morphemizer,
    am_config: AnkiMorphsConfig,
    am_db: AnkiMorphsDB,
    field_text: str,
) -> list[Morpheme]:
    if isinstance(morphemizer, SpacyMorphemizer):
        nlp = spacy_wrapper.get_nlp(
            morphemizer.get_description().removeprefix("spaCy: ")
        )

        morphs = list(
            set(get_processed_spacy_morphs(am_config, next(nlp.pipe([field_text]))))
        )
    else:
        morphs = list(
            set(get_processed_morphemizer_morphs(morphemizer, field_text, am_config))
        )

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


def rubify(field_text: str) -> str:
    ruby_shorthand = r" (?P<kanji>[^ ]+)\[(?P<kana>.+?)\]"
    ruby_longhand = r"<ruby><rb>\g<kanji></rb><rt>\g<kana></rt></ruby>"

    return re.sub(ruby_shorthand, ruby_longhand, field_text, re.MULTILINE)


def dehtml(field_text: str) -> str:
    ruby_longhand = r"<rt.*?>(?P<kana>.+?)</rt>"
    ruby_shorthand = r"[\g<kana>]"

    wrap_kana = re.sub(ruby_longhand, ruby_shorthand, field_text, re.MULTILINE)

    all_html_tags = r"<[^>]*>"
    return re.sub(all_html_tags, "", wrap_kana, re.MULTILINE)
