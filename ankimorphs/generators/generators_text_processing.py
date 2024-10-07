# Much of the logic in this file is very similar/identical to that found in
# the "text_preprocessing.py" file, and it's very tempting to make further
# abstractions to combine the two, but this would be a classic mistake of
# over-abstraction--the uses cases are sufficiently different that they
# should be kept separate.
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from .. import text_preprocessing
from ..exceptions import UnicodeException
from ..morpheme import Morpheme, MorphOccurrence
from ..morphemizers.morphemizer import Morphemizer
from ..text_preprocessing import (
    remove_names_textfile,
    round_brackets_regex,
    slim_round_brackets_regexp,
    square_brackets_regex,
)
from ..ui.generators_window_ui import Ui_GeneratorsWindow
from .text_extractors import (
    extract_ass_text,
    extract_basic_text,
    extract_epub_text,
    extract_html_text,
    extract_srt_text,
    extract_vtt_text,
)


class PreprocessOptions:
    def __init__(self, ui: Ui_GeneratorsWindow):
        self.filter_square_brackets: bool = ui.squareBracketsCheckBox.isChecked()
        self.filter_round_brackets: bool = ui.roundBracketsCheckBox.isChecked()
        self.filter_slim_round_brackets: bool = ui.slimRoundBracketsCheckBox.isChecked()
        self.filter_numbers: bool = ui.numbersCheckBox.isChecked()
        self.filter_morphemizer_names: bool = ui.namesMorphemizerCheckBox.isChecked()
        self.filter_names_from_file: bool = ui.namesFileCheckBox.isChecked()


extractors: dict[str, Callable[[Path], list[str]]] = {
    ".ass": extract_ass_text,
    ".epub": extract_epub_text,
    ".html": extract_html_text,
    ".srt": extract_srt_text,
    ".vtt": extract_vtt_text,
    ".md": extract_basic_text,
    ".txt": extract_basic_text,
}


def create_file_morph_occurrences(
    preprocess_options: PreprocessOptions,
    file_path: Path,
    morphemizer: Morphemizer,
    nlp: Any,  # nlp: spacy.Language
) -> dict[str, MorphOccurrence]:

    morph_occurrences: dict[str, MorphOccurrence]
    raw_lines: list[str]
    filtered_lines: list[str] = []
    extension = file_path.suffix

    if extension in extractors:
        raw_lines = extractors[extension](file_path)
    else:
        raise ValueError(f"Unsupported file format: {extension}")

    try:
        for line in raw_lines:
            # lower-case to avoid proper noun false-positives
            filtered_line = filter_line(preprocess_options, line=line.strip().lower())
            if filtered_line:
                filtered_lines.append(filtered_line)

    except UnicodeDecodeError as exc:
        raise UnicodeException(path=file_path) from exc

    if nlp is not None:
        morph_occurrences = get_morph_occurrences_by_spacy(
            preprocess_options, nlp, filtered_lines
        )
    else:
        morph_occurrences = get_morph_occurrences_by_morphemizer(
            preprocess_options, morphemizer, filtered_lines
        )

    return morph_occurrences


def filter_line(preprocess: PreprocessOptions, line: str) -> str:
    if preprocess.filter_square_brackets:
        if square_brackets_regex.search(line):
            line = square_brackets_regex.sub("", line)

    if preprocess.filter_round_brackets:
        if round_brackets_regex.search(line):
            line = round_brackets_regex.sub("", line)

    if preprocess.filter_slim_round_brackets:
        if slim_round_brackets_regexp.search(line):
            line = slim_round_brackets_regexp.sub("", line)

    if preprocess.filter_numbers:
        line = re.sub(r"\d", "", line)

    return line


def get_morph_occurrences_by_spacy(
    preprocess_options: PreprocessOptions, nlp: Any, all_lines: list[str]
) -> dict[str, MorphOccurrence]:
    morph_occurrences: dict[str, MorphOccurrence] = {}

    for doc in nlp.pipe(all_lines):
        morphs: list[Morpheme] = get_morphs_from_line_spacy(preprocess_options, doc=doc)
        for morph in morphs:
            key = morph.lemma + morph.inflection
            if key in morph_occurrences:
                morph_occurrences[key].occurrence += 1
            else:
                morph_occurrences[key] = MorphOccurrence(morph)

    return morph_occurrences


def get_morphs_from_line_spacy(
    preprocess: PreprocessOptions, doc: Any
) -> list[Morpheme]:
    # doc: spacy.tokens.Doc

    morphs: list[Morpheme] = []

    for w in doc:
        if not w.is_alpha:
            continue

        if preprocess.filter_morphemizer_names:
            if w.pos == 96:  # PROPN
                continue

        morphs.append(
            Morpheme(
                lemma=w.lemma_,
                inflection=w.text,
            )
        )

    if preprocess.filter_names_from_file:
        morphs = remove_names_textfile(morphs)

    return morphs


def get_morph_occurrences_by_morphemizer(
    preprocess_options: PreprocessOptions,
    morphemizer: Morphemizer,
    all_lines: list[str],
) -> dict[str, MorphOccurrence]:
    morph_occurrences: dict[str, MorphOccurrence] = {}

    for line in all_lines:
        morphs: list[Morpheme] = get_morphs_from_line_morphemizer(
            preprocess_options=preprocess_options,
            morphemizer=morphemizer,
            line=line,
        )
        for morph in morphs:
            key = morph.lemma + morph.inflection
            if key in morph_occurrences:
                morph_occurrences[key].occurrence += 1
            else:
                morph_occurrences[key] = MorphOccurrence(morph)

    return morph_occurrences


def get_morphs_from_line_morphemizer(
    preprocess_options: PreprocessOptions, morphemizer: Morphemizer, line: str
) -> list[Morpheme]:
    morphs: list[Morpheme] = morphemizer.get_morphemes_from_expr(line)
    if preprocess_options.filter_morphemizer_names:
        morphs = text_preprocessing.remove_names_morphemizer(morphs)
    if preprocess_options.filter_names_from_file:
        morphs = text_preprocessing.remove_names_textfile(morphs)
    return morphs
