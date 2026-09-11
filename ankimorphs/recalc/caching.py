from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
from typing import Any

from aqt import mw

from .. import ankimorphs_globals as am_globals
from .. import name_file_utils, progress_utils
from ..ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from ..ankimorphs_db import AnkiMorphsDB
from ..exceptions import CancelledOperationException, KnownMorphsFileMalformedException
from ..morphemizers import morphemizer_utils
from ..text_preprocessing import get_processed_text
from . import anki_data_utils
from .anki_data_utils import AnkiCardData


def cache_anki_data(
    am_config: AnkiMorphsConfig,
    read_enabled_config_filters: list[AnkiMorphsConfigFilter],
) -> None:
    """
    Extracting morphs from cards is expensive, so caching them yields a significant
    performance gain. The morphs a previous recalc extracted are reused unless
    something they depend on changed.
    """
    assert mw is not None

    am_db = AnkiMorphsDB()
    am_db.create_extraction_signature_table()

    extraction_signature = _get_morph_extraction_signature(
        am_config, read_enabled_config_filters
    )
    cached_morphs_are_reusable = _cached_morphs_are_reusable(
        am_db, extraction_signature, read_enabled_config_filters
    )

    if not cached_morphs_are_reusable:
        am_db.drop_all_tables()

    am_db.create_all_tables()

    # cleared before the first write, written again after the last one, so an
    # interrupted recalc leaves no signature and the next one rebuilds
    am_db.set_extraction_signature(None)

    # recalc has always started the "morphs seen today" over
    am_db.drop_seen_morphs_table()
    am_db.create_seen_morph_table()

    cached_expression_hashes: dict[int, int] = am_db.get_expression_hashes()

    card_table_data: list[dict[str, Any]] = []
    card_morph_map_table_data: list[dict[str, Any]] = []
    orphaned_card_ids: set[int] = set(cached_expression_hashes)
    reextracted_card_ids: set[int] = set()

    # We only want to cache the morphs on the note-filters that have 'read' enabled
    for config_filter in read_enabled_config_filters:
        cards_data_dict = anki_data_utils.create_card_data_dict(
            am_config, config_filter
        )
        orphaned_card_ids.difference_update(cards_data_dict)
        reextracted_card_ids.update(
            _extract_and_assign_morphs(
                am_config, config_filter, cards_data_dict, cached_expression_hashes
            )
        )
        _append_card_and_morph_data(
            am_config,
            config_filter,
            cards_data_dict,
            card_table_data,
            card_morph_map_table_data,
        )

    progress_utils.background_update_progress(label="Saving to ankimorphs.db")
    am_db.replace_card_table(card_table_data)

    # these still hold the morphs of the previous recalc
    if cached_morphs_are_reusable:
        am_db.delete_card_morphs(orphaned_card_ids | reextracted_card_ids)

    am_db.insert_many_into_card_morph_map_table(card_morph_map_table_data)

    morph_table_data: list[dict[str, Any]] = am_db.get_morphs_with_highest_intervals()

    if am_config.read_known_morphs_folder:
        progress_utils.background_update_progress(label="Importing known morphs")
        morph_table_data += _get_morphs_from_files(am_config)

    morph_table_data = _deduplicate_morphs(morph_table_data)

    progress_utils.background_update_progress(label="Updating learning intervals")
    _update_learning_intervals(am_config, morph_table_data)

    am_db.replace_morph_table(morph_table_data)
    am_db.set_extraction_signature(extraction_signature)
    am_db.con.close()


def _cached_morphs_are_reusable(
    am_db: AnkiMorphsDB,
    extraction_signature: str,
    read_enabled_config_filters: list[AnkiMorphsConfigFilter],
) -> bool:
    if am_db.get_extraction_signature() != extraction_signature:
        return False

    return _every_card_has_one_source_of_morphs(read_enabled_config_filters)


def _get_morph_extraction_signature(
    am_config: AnkiMorphsConfig,
    read_enabled_config_filters: list[AnkiMorphsConfigFilter],
) -> str:
    signature_parts: list[Any] = [
        am_globals.__version__,
        am_config.preprocess_ignore_bracket_contents,
        am_config.preprocess_ignore_round_bracket_contents,
        am_config.preprocess_ignore_slim_round_bracket_contents,
        am_config.preprocess_ignore_numbers,
        am_config.preprocess_ignore_custom_characters,
        am_config.preprocess_custom_characters_to_ignore,
        am_config.preprocess_ignore_names_morphemizer,
        am_config.preprocess_ignore_names_textfile,
        sorted(name_file_utils.get_names_from_file()),
        sorted(
            (
                config_filter.note_type,
                config_filter.field,
                config_filter.morphemizer_description,
            )
            for config_filter in read_enabled_config_filters
        ),
    ]
    return hashlib.blake2b(repr(signature_parts).encode("utf-8")).hexdigest()


def _every_card_has_one_source_of_morphs(
    read_enabled_config_filters: list[AnkiMorphsConfigFilter],
) -> bool:
    """
    Overlapping note filters are fine as long as they read the same field with
    the same morphemizer. When they don't, a card's morphs are the union of
    several sources, which one hash per card cannot describe.
    """
    morph_sources_of_note_type: dict[str, set[tuple[str, str]]] = {}

    for config_filter in read_enabled_config_filters:
        morph_sources_of_note_type.setdefault(config_filter.note_type, set()).add(
            (config_filter.field, config_filter.morphemizer_description)
        )

    return all(
        len(morph_sources) == 1 for morph_sources in morph_sources_of_note_type.values()
    )


def _get_expression_hash(config_filter: AnkiMorphsConfigFilter, expression: str) -> int:
    """
    Covers the filter the text was read through, not only the text: a note can
    move to a filter with a different morphemizer while keeping its text.
    """
    source = (
        f"{config_filter.field}\x1f{config_filter.morphemizer_description}\x1f"
        f"{expression}"
    )
    return int.from_bytes(
        hashlib.blake2b(source.encode("utf-8"), digest_size=8).digest(),
        byteorder="big",
        signed=True,
    )


def _extract_and_assign_morphs(
    am_config: AnkiMorphsConfig,
    config_filter: AnkiMorphsConfigFilter,
    cards_data_dict: dict[int, AnkiCardData],
    cached_expression_hashes: dict[int, int],
) -> list[int]:
    """
    Batches the card expressions for this filter, runs them through the
    configured morphemizer, and writes the resulting morphs back onto
    each card's data. Cards whose expression hash still matches are left out of
    the batch and keep the morphs a previous recalc extracted.

    Returns: the ids of the cards that were extracted again
    """
    # str is first because that is the order spacy receives it
    items_to_extract: list[tuple[str, int]] = []

    for key, card_data in cards_data_dict.items():
        expression_hash = _get_expression_hash(config_filter, card_data.expression)
        card_data.expression_hash = expression_hash

        if cached_expression_hashes.get(key) != expression_hash:
            items_to_extract.append(
                (get_processed_text(am_config, card_data.expression.lower()), key)
            )

    card_amount = len(items_to_extract)

    if card_amount == 0:
        return []

    morphemizer = morphemizer_utils.get_morphemizer_by_description(
        config_filter.morphemizer_description
    )
    assert morphemizer is not None

    for index, (processed_morphs, key) in enumerate(
        morphemizer.get_processed_morphs(am_config, items_to_extract)
    ):
        progress_utils.background_update_progress_potentially_cancel(
            label=f"Extracting morphs from<br>{config_filter.note_type} cards<br>card: {index} of {card_amount}",
            counter=index,
            max_value=card_amount,
        )
        cards_data_dict[key].morphs = set(processed_morphs)

    return [key for _processed_text, key in items_to_extract]


def _append_card_and_morph_data(
    am_config: AnkiMorphsConfig,
    config_filter: AnkiMorphsConfigFilter,
    cards_data_dict: dict[int, AnkiCardData],
    card_table_data: list[dict[str, Any]],
    card_morph_map_table_data: list[dict[str, Any]],
) -> None:
    """
    Builds the row dicts for the card table and the morph/card-morph-map
    tables from the (now morph-annotated) cards_data_dict.
    """
    card_amount = len(cards_data_dict)

    for counter, (card_id, card_data) in enumerate(cards_data_dict.items()):
        progress_utils.background_update_progress_potentially_cancel(
            label=f"Caching {config_filter.note_type} cards<br>card: {counter} of {card_amount}",
            counter=counter,
            max_value=card_amount,
        )

        card_table_data.append(
            {
                "card_id": card_id,
                "note_id": card_data.note_id,
                "note_type_id": card_data.note_type_id,
                "card_type": card_data.type,
                "tags": card_data.tags,
                "expression_hash": card_data.expression_hash,
                "memory_strength": _get_card_memory_strength(am_config, card_data),
            }
        )

        if card_data.morphs is None:
            continue

        for morph in card_data.morphs:
            card_morph_map_table_data.append(
                {
                    "card_id": card_id,
                    "morph_lemma": morph.lemma,
                    "morph_inflection": morph.inflection,
                }
            )


def _deduplicate_morphs(
    morph_table_data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    # the Morphs table only keeps one row per (lemma, inflection) with the
    # highest interval anyway, so collapsing here just saves sqlite the upserts
    deduplicated_morphs: dict[tuple[str, str], dict[str, Any]] = {}

    for morph_data_dict in morph_table_data:
        key = (morph_data_dict["lemma"], morph_data_dict["inflection"])
        existing = deduplicated_morphs.get(key)

        if (
            existing is None
            or morph_data_dict["highest_inflection_learning_interval"]
            > existing["highest_inflection_learning_interval"]
        ):
            deduplicated_morphs[key] = morph_data_dict

    return list(deduplicated_morphs.values())


def _get_card_memory_strength(
    am_config: AnkiMorphsConfig, card_data: AnkiCardData
) -> int:
    if card_data.automatically_known_tag or card_data.manually_known_tag:
        return am_config.interval_for_known_morphs

    if card_data.type == 0:  # 0: new
        # force a zero value as an early exit and to prevent edge cases.
        return 0

    if card_data.type == 1:  # 1: learning
        # cards in the 'learning' state have an interval of zero, but we don't
        # want to treat them as 'unknown', so we change the value manually.
        return 1

    if am_config.use_stability_for_known_threshold:
        # Stability being a float, we floor it to get an integer value of "secured" interval, and we
        # give a minimum stability of 1 since the card is not new
        return max(1, math.floor(card_data.stability))

    return card_data.interval


def _get_morphs_from_files(am_config: AnkiMorphsConfig) -> list[dict[str, Any]]:
    assert mw is not None

    morphs_from_files: list[dict[str, Any]] = []
    input_files: list[Path] = _get_known_morphs_files()

    for input_file in input_files:
        if mw.progress.want_cancel():  # user clicked 'x'
            raise CancelledOperationException

        progress_utils.background_update_progress(
            label=f"Importing known morphs from file:<br>{input_file.name}",
        )

        with open(input_file, encoding="utf-8") as csvfile:
            morph_reader = csv.reader(csvfile, delimiter=",")
            headers: list[str] | None = next(morph_reader, None)

            lemma_column_index, inflection_column_index = (
                _get_lemma_and_inflection_columns(
                    input_file_path=input_file, headers=headers
                )
            )

            if inflection_column_index == -1:
                morphs_from_files += _get_morphs_from_minimum_format(
                    am_config, morph_reader, lemma_column_index
                )
            else:
                morphs_from_files += _get_morphs_from_full_format(
                    am_config, morph_reader, lemma_column_index, inflection_column_index
                )

    return morphs_from_files


def _get_known_morphs_files() -> list[Path]:
    assert mw is not None
    input_files: list[Path] = []
    known_morphs_dir_path: Path = Path(
        mw.pm.profileFolder(), am_globals.KNOWN_MORPHS_DIR_NAME
    )
    for path in known_morphs_dir_path.rglob("*.csv"):
        input_files.append(path)
    return input_files


def _get_lemma_and_inflection_columns(
    input_file_path: Path, headers: list[str] | None
) -> tuple[int, int]:
    if headers is None:
        raise KnownMorphsFileMalformedException(input_file_path)

    # we lower case the headers to make it backwards
    # compatible with 'known morphs' files from AnkiMorphs v2
    headers_lower = [header.lower() for header in headers]

    if am_globals.LEMMA_HEADER.lower() not in headers_lower:
        raise KnownMorphsFileMalformedException(input_file_path)

    lemma_column_index: int = headers_lower.index(am_globals.LEMMA_HEADER.lower())
    inflection_column_index: int = -1

    try:
        inflection_column_index = headers_lower.index(
            am_globals.INFLECTION_HEADER.lower()
        )
    except ValueError:
        # ValueError just means it's not a full format file, which
        # we handle later, so this can safely be ignored.
        pass

    return lemma_column_index, inflection_column_index


def _get_morphs_from_minimum_format(
    am_config: AnkiMorphsConfig, morph_reader: Any, lemma_column: int
) -> list[dict[str, Any]]:
    morphs_from_files: list[dict[str, Any]] = []

    for row in morph_reader:
        lemma: str = row[lemma_column]
        morphs_from_files.append(
            {
                "lemma": lemma,
                "inflection": lemma,
                "highest_lemma_learning_interval": am_config.interval_for_known_morphs,
                "highest_inflection_learning_interval": am_config.interval_for_known_morphs,
            }
        )
    return morphs_from_files


def _get_morphs_from_full_format(
    am_config: AnkiMorphsConfig,
    morph_reader: Any,
    lemma_column: int,
    inflection_column: int,
) -> list[dict[str, Any]]:
    morphs_from_files: list[dict[str, Any]] = []

    for row in morph_reader:
        lemma: str = row[lemma_column]
        inflection: str = row[inflection_column]
        morphs_from_files.append(
            {
                "lemma": lemma,
                "inflection": inflection,
                "highest_lemma_learning_interval": am_config.interval_for_known_morphs,
                "highest_inflection_learning_interval": am_config.interval_for_known_morphs,
            }
        )
    return morphs_from_files


def _update_learning_intervals(
    am_config: AnkiMorphsConfig, morph_table_data: list[dict[str, Any]]
) -> None:
    learning_intervals_of_lemmas: dict[str, int] = _get_learning_intervals_of_lemmas(
        morph_table_data
    )

    if am_config.evaluate_morph_lemma:
        # update both the lemma and inflection intervals
        for morph_data_dict in morph_table_data:
            lemma = morph_data_dict["lemma"]
            morph_data_dict["highest_lemma_learning_interval"] = (
                learning_intervals_of_lemmas[lemma]
            )
            morph_data_dict["highest_inflection_learning_interval"] = (
                learning_intervals_of_lemmas[lemma]
            )
    else:
        # only update lemma intervals
        for morph_data_dict in morph_table_data:
            lemma = morph_data_dict["lemma"]
            morph_data_dict["highest_lemma_learning_interval"] = (
                learning_intervals_of_lemmas[lemma]
            )


def _get_learning_intervals_of_lemmas(
    morph_table_data: list[dict[str, Any]],
) -> dict[str, int]:
    learning_intervals_of_lemmas: dict[str, int] = {}

    for morph_data_dict in morph_table_data:
        lemma = morph_data_dict["lemma"]
        inflection_interval = morph_data_dict["highest_inflection_learning_interval"]

        if lemma in learning_intervals_of_lemmas:
            if inflection_interval > learning_intervals_of_lemmas[lemma]:
                learning_intervals_of_lemmas[lemma] = inflection_interval
        else:
            learning_intervals_of_lemmas[lemma] = inflection_interval

    return learning_intervals_of_lemmas
