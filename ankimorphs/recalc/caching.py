from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
from typing import Any

import anki.utils
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
from .extraction_sources import NoteSourceKey, get_expression_hash, make_source_key


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
        am_db, extraction_signature
    )

    if not cached_morphs_are_reusable:
        am_db.drop_all_tables()

    am_db.create_all_tables()

    # cleared before the first write, written again after the last one, so an
    # interrupted recalc leaves no signature and the next one rebuilds
    am_db.set_extraction_signature(None)

    cached_source_hashes: dict[NoteSourceKey, int] = am_db.get_source_hashes()
    card_table_data, source_work, source_assignments = _collect_source_work(
        am_config, read_enabled_config_filters
    )

    current_source_hashes = {
        key: get_expression_hash(key[1], expression)
        for key, (_config_filter, expression) in source_work.items()
    }
    changed_source_keys = {
        key
        for key, expression_hash in current_source_hashes.items()
        if cached_source_hashes.get(key) != expression_hash
    }
    orphaned_source_keys = set(cached_source_hashes) - set(current_source_hashes)
    source_morph_rows = _extract_source_morphs(
        am_config, source_work, changed_source_keys
    )

    progress_utils.background_update_progress(label="Saving to ankimorphs.db")
    am_db.replace_card_table(list(card_table_data.values()))
    am_db.delete_note_source_morphs(orphaned_source_keys | changed_source_keys)
    am_db.replace_note_sources(
        [
            {
                "note_id": note_id,
                "source_key": source_key,
                "expression_hash": expression_hash,
            }
            for (note_id, source_key), expression_hash in current_source_hashes.items()
        ]
    )
    am_db.insert_note_source_morphs(source_morph_rows)
    am_db.materialize_card_morph_map(
        [
            {"card_id": card_id, "note_id": note_id, "source_key": source_key}
            for card_id, note_id, source_key in source_assignments
        ]
    )

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

    # Card_Morph_Map may have changed, so refresh today's seen morphs from it.
    AnkiMorphsDB.rebuild_seen_morphs_today_background()


def _collect_source_work(
    am_config: AnkiMorphsConfig,
    config_filters: list[AnkiMorphsConfigFilter],
) -> tuple[
    dict[int, dict[str, Any]],
    dict[NoteSourceKey, tuple[AnkiMorphsConfigFilter, str]],
    set[tuple[int, int, str]],
]:
    card_table_data: dict[int, dict[str, Any]] = {}
    source_work: dict[NoteSourceKey, tuple[AnkiMorphsConfigFilter, str]] = {}
    assignments: set[tuple[int, int, str]] = set()
    anki_data_cache: dict[
        tuple[int, tuple[str, ...], tuple[str, ...]],
        dict[int, anki_data_utils.AnkiDBRowData],
    ] = {}

    for config_filter in config_filters:
        anki_data = _get_filter_anki_data(am_config, config_filter, anki_data_cache)
        cards = anki_data_utils.create_card_data_dict(
            am_config, config_filter, anki_data
        )
        source_key = make_source_key(config_filter)
        for card_id, card_data in cards.items():
            note_source_key = (card_data.note_id, source_key)
            previous = source_work.get(note_source_key)
            if previous is not None:
                assert previous[1] == card_data.expression_field
            else:
                source_work[note_source_key] = (
                    config_filter,
                    card_data.expression_field,
                )

            assignments.add((card_id, card_data.note_id, source_key))
            card_table_data.setdefault(
                card_id,
                {
                    "card_id": card_id,
                    "note_id": card_data.note_id,
                    "note_type_id": card_data.note_type_id,
                    "card_type": card_data.type,
                    "tags": card_data.tags,
                    "memory_strength": _get_card_memory_strength(am_config, card_data),
                },
            )

    return card_table_data, source_work, assignments


def _get_filter_anki_data(
    am_config: AnkiMorphsConfig,
    config_filter: AnkiMorphsConfigFilter,
    cache: dict[
        tuple[int, tuple[str, ...], tuple[str, ...]],
        dict[int, anki_data_utils.AnkiDBRowData],
    ],
) -> dict[int, anki_data_utils.AnkiDBRowData]:
    assert mw is not None
    note_type_id = mw.col.models.id_for_name(config_filter.note_type)
    assert note_type_id is not None
    key = (
        int(note_type_id),
        tuple(config_filter.tags["include"]),
        tuple(config_filter.tags["exclude"]),
    )
    if key not in cache:
        cache[key] = anki_data_utils._get_anki_data(  # pylint:disable=protected-access
            am_config, note_type_id, config_filter.tags
        )
    return cache[key]


def _cached_morphs_are_reusable(
    am_db: AnkiMorphsDB,
    extraction_signature: str,
) -> bool:
    if not am_db.has_current_extraction_schema():
        return False

    if am_db.get_extraction_signature() != extraction_signature:
        return False

    return True


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


def _extract_source_morphs(
    am_config: AnkiMorphsConfig,
    source_work: dict[NoteSourceKey, tuple[AnkiMorphsConfigFilter, str]],
    changed_source_keys: set[NoteSourceKey],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, list[NoteSourceKey]]] = {}
    for source_key in changed_source_keys:
        config_filter, expression_field = source_work[source_key]
        expression = anki.utils.strip_html(expression_field.replace("<br>", "\n"))
        processed_text = get_processed_text(am_config, expression.lower())
        if not processed_text.strip():
            continue
        grouped.setdefault(config_filter.morphemizer_description, {}).setdefault(
            processed_text, []
        ).append(source_key)

    rows: list[dict[str, Any]] = []
    for morphemizer_description, text_sources in grouped.items():
        rows.extend(
            _extract_morphemizer_group(am_config, morphemizer_description, text_sources)
        )
    return rows


def _extract_morphemizer_group(
    am_config: AnkiMorphsConfig,
    morphemizer_description: str,
    text_sources: dict[str, list[NoteSourceKey]],
) -> list[dict[str, Any]]:
    morphemizer = morphemizer_utils.get_morphemizer_by_description(
        morphemizer_description
    )
    assert morphemizer is not None
    texts = list(text_sources)
    items = [(text, index) for index, text in enumerate(texts)]
    rows: list[dict[str, Any]] = []

    for counter, (processed_morphs, index) in enumerate(
        morphemizer.get_processed_morphs(am_config, items)
    ):
        progress_utils.background_update_progress_potentially_cancel(
            label=f"Extracting morphs with<br>{morphemizer_description}<br>text: {counter} of {len(items)}",
            counter=counter,
            max_value=len(items),
        )
        for note_id, extraction_source_key in text_sources[texts[index]]:
            rows.extend(
                {
                    "note_id": note_id,
                    "source_key": extraction_source_key,
                    "morph_lemma": morph.lemma,
                    "morph_inflection": morph.inflection,
                }
                for morph in processed_morphs
            )
    return rows


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
