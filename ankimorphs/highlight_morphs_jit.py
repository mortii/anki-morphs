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

    field_text = text_highlighting.get_highlighted_text(
        am_config, card_morphs, field_text
    )

    # If the user has specified to preprocess_ignore_bracket_contents, and in the case where we are
    # run after the anki built in furigana filter, it's likely that we have false positive matches
    # in the kana part of the html rubies. If they're not preprocess_ignore_bracket_contents, then
    # it's likely that they WANT the inflections to be highlighted differently than the kanji.
    #
    return (
        post_process_learning_status(field_text)
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
    # <ruby><rb>X</rb><rt>yz</rt></ruby> = <ruby><rb>X</rb>[yz]</ruby>
    # <rt class='foo'>234</rt> = [234]
    # <rt >>234</rt> = [>234]
    # <rt></rt> = will not match
    #
    ruby_longhand = r"<rt[^>]*>(?P<kana>.+?)</rt>"

    # Emit the captured kana into square brackets, thus reconstructing the ruby shorthand "X[yz]".
    #
    ruby_shorthand = r"[\g<kana>]"

    # Remove all other html tags. We do not want to forward these to the morphemizer.
    #
    text = anki.utils.strip_html(re.sub(ruby_longhand, ruby_shorthand, text))

    # Remove brackets if user specified not to process them.
    #
    if preprocess_ignore_bracket_contents:
        text = re.sub(r"\[.*?\]", "", text)

    return text


def post_process_learning_status(field_text: str) -> str:
    """If html rubies exist and there are morph-statuses, it's likely they're in the
    wrong place. We need to update the html to move them into a better location.
    If it feels like this is a lot of text gymnastics, that's because it is."""

    # Find ruby tags, with or without attributes where at least one sub element
    # has a morph-status.
    #
    # Samples
    # hi there <ruby><rb>X</rb><rt>yz</rt></ruby> <p>testing tag</p> = will not match (no morph-status prop)
    # hi there <ruby><rb><span morph-status="unknown">X</rb><rt>yz</rt></ruby> <p>testing tag</p> = will match from <ruby> to </ruby>
    # <span morph-status="unknown">X</rb><rt>yz</rt> = will not match, no ruby tags.
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
    """If there is only one learning status across all <rb>'s then consolidate and promote. If
    there are multiple learning statuses for a given ruby, it's not fair to pick one for
    highlighting and we create a new status "multiple"."""

    # Find all morph-statuses in the ruby (excluding in the <rt> translations);
    #
    stripped_text = re.sub("<rt.*?</rt>", "", text)
    morph_status_attr = r'morph-status="(.*?)"'
    matches = list(set(re.findall(morph_status_attr, stripped_text)))

    if len(matches) == 0:
        text = unify_ruby_morph_status(text, "unknown")
    elif len(matches) == 1:
        text = unify_ruby_morph_status(text, matches[0])
    else:
        text = strip_rt_morph_status(text)

    return text


def unify_ruby_morph_status(text: str, morph_status: str) -> str:
    """Move the learning status to the ruby tag for clarity."""

    morph_status_attr = r"\s+morph-status=\"[^\"]*\""

    # Remove all morph statuses in this ruby
    #
    text = re.sub(morph_status_attr, "", text)

    # Add the found morph status to the ruby.
    #
    ruby_tag = r"(?P<ruby_tag><ruby[^>]*)>"
    ruby_replace = r"\g<ruby_tag>" + f' morph-status="{morph_status}">'

    return re.sub(ruby_tag, ruby_replace, text)


def strip_rt_morph_status(text: str) -> str:
    """Remove all morph statuses from translations and replace with unknown."""

    rt_with_status = r"<rt[^>]*>.*?morph-status.*?</rt>"
    rt = re.search(rt_with_status, text)
    if not rt:
        return text

    morph_status = 'morph-status=".*?"'
    morph_status_replacement = 'morph-status="multiple"'

    new_rt = re.sub(morph_status, morph_status_replacement, rt.group())

    return re.sub(rt_with_status, new_rt, text)
