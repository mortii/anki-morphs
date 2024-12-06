from __future__ import annotations

import re

import anki
from anki.template import TemplateRenderContext

from ankimorphs.morpheme_highlight_meta import MorphemeHighlightMeta

from . import ankimorphs_config, ankimorphs_globals, text_preprocessing
from .ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from .ankimorphs_db import AnkiMorphsDB
from .morpheme import Morpheme
from .morphemizers import morphemizer as morphemizer_module
from .morphemizers import spacy_wrapper
from .morphemizers.morphemizer import Morphemizer, SpacyMorphemizer


def get_highlighted_text(
    am_config: AnkiMorphsConfig,
    morphemes: list[Morpheme],
    text: str,
) -> str:
    """Use morph learning progress to decorate the morphemes in the supplied text.
    Internal method that takes some already processed data, so is simpler than highlight_morphs_jit.
    """
    return _rubify_with_status(_make_highlight_morph_meta(morphemes, am_config), text)


def highlight_morphs_jit(
    field_text: str,
    field_name: str,
    filter_name: str,
    context: TemplateRenderContext,
) -> str:
    """Use morph learning progress to decorate the morphemes in the supplied text.
    Registered as a template filter in anki. Adds css classes to the output that
    can be styled in the card."""

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

    morph_metas: list[MorphemeHighlightMeta] = _get_morph_meta_for_text(
        morphemizer, field_text, am_config
    )

    if not morph_metas:
        return field_text

    return _rubify_with_status(morph_metas, _dehtml(field_text))


def _get_morph_meta_for_text(
    morphemizer: Morphemizer,
    field_text: str,
    am_config: AnkiMorphsConfig,
) -> list[MorphemeHighlightMeta]:
    """Take in a string and gather the morphemes from it."""

    # If we were piped in after the `furigana` built-in filter, or if there is html in the source
    # data, we need to do some cleansing before we present to the morphemizers.
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

    return _make_highlight_morph_meta(morphs, am_config, True)


def _make_highlight_morph_meta(
    morphs: list[Morpheme], am_config: AnkiMorphsConfig, get_intervals: bool = False
) -> list[MorphemeHighlightMeta]:
    """Create MorphemeHighlightMeta objects to store some data relevant to highlighting."""

    morphs = list(set(morphs))

    if not morphs:
        return []

    if get_intervals:
        with AnkiMorphsDB() as am_db:
            morph_metas = [
                (
                    MorphemeHighlightMeta(
                        morph.inflection,
                        am_db.get_highest_inflection_learning_interval(morph) or 0,
                        am_config,
                    )
                    if am_config.evaluate_morph_inflection
                    else MorphemeHighlightMeta(
                        morph.lemma,
                        am_db.get_highest_lemma_learning_interval(morph) or 0,
                        am_config,
                    )
                )
                for morph in morphs
            ]
    else:
        morph_metas = [
            MorphemeHighlightMeta(
                (
                    morph.inflection
                    if am_config.evaluate_morph_inflection
                    else morph.lemma
                ),
                (
                    (morph.highest_inflection_learning_interval or 0)
                    if am_config.evaluate_morph_inflection
                    else (morph.highest_lemma_learning_interval or 0)
                ),
                am_config,
            )
            for morph in morphs
        ]

    return morph_metas


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
    ruby_longhand = r"(?:<ruby[^<]*>)(?:<rb>|.{0})(?P<kanji>.*?)(?:</rb>|.{0})<rt[^>]*>(?P<kana>.+?)</rt>(?P<after>.*?)(?:</ruby>)"

    # Emit the captured kana into square brackets, thus reconstructing the ruby shorthand "X[yz]".
    # Pad with a space so that we can retain the kanji/kana relationship
    #
    ruby_shorthand = r" \g<kanji>[\g<kana>]\g<after>"

    text = re.sub(ruby_longhand, ruby_shorthand, text, flags=re.IGNORECASE)

    # Remove all other html tags. We do not want to forward these to the morphemizer.
    #
    if clean_html:
        text = anki.utils.strip_html(text)

    return text_preprocessing.get_processed_text(am_config, text) if am_config else text


def _rubify_with_status(morph_metas: list[MorphemeHighlightMeta], text: str) -> str:
    """Split the incoming string into parts to be processed.
    After processing, join them back together with newlines.
    Each split part will become an html ruby.
    This allows the interaction between furigana notation and morpheme detection to work in harmony.
    Present each of the found parts to the function that will do the formatting of the part.
    """

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

    # furigana is a regex used to deal with text rubies inside the target string.
    # 1 `(?![^\[]*\])`: A negative lookahead that ensures the pattern does not match inside square
    # brackets, preventing accidental matches inside rubies.
    # 2 `\[(?P<kana>.*?)\]`: a capture group named <kana> that captures all characters inside
    # square brackets
    #
    furigana = r"(?![^\[]*\])\[(?P<kana>.*?)\]"
    ruby = rf'<rt morph-status="{status}">\g<kana></rt>'
    status_span_open = f'<span morph-status="{status}">'
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
    # Trim off cases where there is an empty span tag in case we ended up doing that.
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


def _rubify_part_with_status(
    text: str, morph_metas: list[MorphemeHighlightMeta]
) -> str:
    """Take in a part for processing, find all morphemes in this part and format them. Wrap the
    entire part in a ruby. Post-process to tag all pieces that do not have a morpheme.
    """

    for morph_meta in morph_metas:
        full_match = False

        # Reverse sort the matches so we can replace safely.
        #
        # Make a specially crafted regex for this morpheme and test for it.
        #
        for match in reversed(
            list(re.finditer(morph_meta.regex, text, flags=re.IGNORECASE))
        ):
            matched = match.group(1)

            if matched:
                # Optimization, do not check any more morphs if we consumed the whole line already.
                #
                if len(matched) == len(text):
                    full_match = True

                # If found, format it, and splice it back into the source string.
                #
                text = (
                    text[: match.start()]
                    + _make_morph_ruby(match.group(1), morph_meta.status)
                    + text[match.end() :]
                )

        if full_match:
            break

    # Find all "bare" text left in the part.
    #
    # Excludes all content between <span>s and <rt>s. also excludes html tags.
    #
    unprocessed_regex = r"<span.*?</span>|<rt.*?</rt>|<[^<]*>|([^<]*)"

    # Final pass, find all unprocessed pieces in the part, and tag them, in case our user wants
    # to style them. This typically includes punctuation and proper nouns.
    #
    for match in reversed(
        list(re.finditer(unprocessed_regex, text, flags=re.IGNORECASE))
    ):
        if match.group(1):
            text = (
                text[: match.start()]
                + _make_morph_ruby(match.group(1), "unprocessed")
                + text[match.end() :]
            )

    # Wrap the whole part in a ruby tag. This is the magic that lets rubies and morphemes play
    # nice.
    #
    text = "<ruby>" + text + "</ruby>"

    return text
