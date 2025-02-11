from __future__ import annotations

import re

import anki
from anki.template import TemplateRenderContext

from .. import ankimorphs_config, ankimorphs_globals, text_preprocessing
from ..ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from ..ankimorphs_db import AnkiMorphsDB
from ..highlighting.ruby_classes import (
    FuriganaRuby,
    KanaRuby,
    KanjiRuby,
    Ruby,
    TextRuby,
)
from ..highlighting.text_highlighter import TextHighlighter
from ..morpheme import Morpheme
from ..morphemizers import morphemizer_utils
from ..morphemizers.morphemizer import (
    Morphemizer,
)


def highlight_morphs_jit(
    field_text: str,
    field_name: str,
    filter_name: str,
    context: TemplateRenderContext,
) -> str:
    """
    Use morph learning progress to decorate the morphemes in the supplied text.
    Adds css classes to the output that can be styled in the card.
    """

    # Perf: Bail early if the user attempts to use this template filter on the already
    # formatted data.
    if (
        filter_name
        not in [
            "am-highlight",
            "am-highlight-furigana",
            "am-highlight-kanji",
            "am-highlight-kana",
        ]
        or field_name == ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
    ):
        return field_text

    am_config_filter: AnkiMorphsConfigFilter | None = (
        ankimorphs_config.get_matching_filter(context.note())
    )

    if am_config_filter is None:
        return field_text

    morphemizer: Morphemizer | None = morphemizer_utils.get_morphemizer_by_description(
        am_config_filter.morphemizer_description
    )

    if not morphemizer:
        return field_text

    am_config = AnkiMorphsConfig()

    card_morphs: list[Morpheme] = _get_morph_meta_for_text(
        morphemizer, field_text, am_config
    )

    ruby_type: type[Ruby] = _get_ruby_type(filter_name)

    highlighted_jit_text = TextHighlighter(
        am_config=am_config,
        morphemes=card_morphs,
        expression=_dehtml(field_text),
        ruby_type=ruby_type,
    ).highlighted()

    return highlighted_jit_text


def _get_morph_meta_for_text(
    morphemizer: Morphemizer,
    field_text: str,
    am_config: AnkiMorphsConfig,
) -> list[Morpheme]:
    """Take in a string and gather the morphemes from it."""

    # If we were piped in after the `furigana` built-in filter, or if there is html in the source
    # data, we need to do some cleansing.
    clean_text = _dehtml(field_text, am_config, True)

    # we only need to first item of the iterator since we only have one sentence,
    morphs: list[Morpheme] = next(
        morphemizer.get_processed_morphs(am_config, sentences=[clean_text])
    )

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
    """
    Prepare a string to be passed to a morphemizer. Specially process <ruby><rt> tags to extract
    ruby to reconstruct base/ruby ruby shorthand. Remove all html from the input string.
    """

    # Capture html ruby ruby. The built in furigana filter will turn X[yz] into
    # <ruby><rb>X</rb><rt>yz</rt></ruby>, and if we blindly strip out all html we will loose
    # information on the ruby. Find <rt> tags and capture all text between them in a capture
    # group called ruby, allow for any attributes or other decorations on the <rt> tag by
    # non-eagerly capturing all chars up to '>', so that the whole element can just be dropped.
    # non-eagerly capture one or more characters into the capture group named ruby.
    # Samples:
    # <ruby><rb>X</rb><rt>yz</rt></ruby> = ` X[yz]`
    # <ruby>X<rt>yz</rt></ruby> = ` X[yz]`
    # <ruby>X<rt class='foo'>234</rt>sdf</ruby> = ` X[234]sdf`
    # <ruby>X<rt >>234</rt>sdf</ruby> = ` X[>234]sdf`
    # <ruby>X<rt></rt></ruby> = Will not match
    ruby_longhand = r"(?:<ruby[^<]*>)(?:<rb[^>]*>|.{0})(?P<base>.*?)(?:</rb>|.{0})<rt[^>]*>(?P<ruby>.+?)</rt>(?P<after>.*?)(?:</ruby>)"

    # Emit the captured ruby into square brackets, thus reconstructing the ruby shorthand "X[yz]".
    # Pad with a leading space so that we can retain the base/ruby relationship
    ruby_shorthand = r" \g<base>[\g<ruby>]\g<after>"

    text = re.sub(ruby_longhand, ruby_shorthand, text, flags=re.IGNORECASE).strip()

    if clean_html:
        text = anki.utils.strip_html(text)

    return text_preprocessing.get_processed_text(am_config, text) if am_config else text


def _get_ruby_type(filter_name: str) -> type[Ruby]:
    """Get local styles for this run, based on the filter name."""

    if filter_name == "am-highlight-furigana":
        return FuriganaRuby
    if filter_name == "am-highlight-kanji":
        return KanjiRuby
    if filter_name == "am-highlight-kana":
        return KanaRuby
    return TextRuby
