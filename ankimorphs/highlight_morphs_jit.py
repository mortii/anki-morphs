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

    field_text = text_highlighting.get_highlighted_text(
        am_config, card_morphs, field_text
    )

    return (
        correct_ruby_learning_status(field_text)
        if am_config.preprocess_ignore_bracket_contents
        else field_text
    )


def get_morphemes(
    morphemizer: Morphemizer,
    am_config: AnkiMorphsConfig,
    field_text: str,
) -> list[Morpheme]:
    """Take in a string and gather the morphemes from it."""

    # If we were piped in after the `furigana` built-in filter, or if there is html in the source
    # data, we need to do some unpacking.
    #
    clean_text = dehtml(field_text)

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


def dehtml(text: str) -> str:
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

    # Emit the captured kana into square brackets, thus reconstructing the ruby shorthand "X[yz]".
    #
    ruby_shorthand = r"[\g<kana>]"

    # Remove all other html tags, we do not want to forward these to the morphemizer.
    #
    return anki.utils.strip_html(re.sub(ruby_longhand, ruby_shorthand, text))


def correct_ruby_learning_status(field_text: str) -> str:
    """If rubies exist and there are morph-statuses, they're in the wrong place.
    We need to update the html to move them into the correct location."""

    # Find ruby tags, with or without attributes.
    #
    rubies_with_status = r"<ruby[^>]*>.*?morph-status.*?</ruby>"
    matches = list(re.finditer(rubies_with_status, field_text))

    # Iterate in reverse order to avoid index issues after replacements.
    #
    for match in reversed(matches):
        start, end = match.span()
        replacement = rubifiy_morph_status(match.group(0))
        field_text = field_text[:start] + replacement + field_text[end:]

    return field_text


def rubifiy_morph_status(text: str) -> str:
    """For a ruby tag, shuffle the morph-status attribute into the right place."""

    # Find the first morph-status in the ruby
    #
    morph_status_attr = r"\s+morph-status=\"[^\"]*\""
    match = re.search(morph_status_attr, text)

    morph_status: str | None = match.group() if match else None

    if not morph_status:
        return text

    # Remove all morph statuses in this ruby
    #
    text = re.sub(morph_status_attr, "", text)

    # Add the found morph status to the ruby.
    #
    ruby_tag = r"(?P<ruby_tag><ruby[^>]*)>"
    ruby_replace = r"\g<ruby_tag>" + f"{morph_status}>"

    return re.sub(ruby_tag, ruby_replace, text)
