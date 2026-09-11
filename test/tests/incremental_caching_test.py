from __future__ import annotations

import copy
from collections.abc import Callable
from test.fake_configs import config_known_morphs_enabled, default_config_dict
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)
from test.recalc_helpers import (
    dump_collection,
    recalc,
    recalc_until_the_collection_stops_changing,
)
from typing import Any
from unittest import mock

import pytest

from ankimorphs import ankimorphs_globals as am_globals
from ankimorphs import name_file_utils, text_preprocessing
from ankimorphs.ankimorphs_config import RawConfigFilterKeys, RawConfigKeys
from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.morphemizers import morphemizer_utils

from anki.collection import Collection  # isort:skip  pylint:disable=wrong-import-order
from anki.notes import NoteId  # isort:skip  pylint:disable=wrong-import-order
from anki.consts import (  # isort:skip  pylint:disable=wrong-import-order
    CARD_TYPE_NEW,
    CARD_TYPE_REV,
    QUEUE_TYPE_NEW,
    QUEUE_TYPE_REV,
    QUEUE_TYPE_SUSPENDED,
)

_SPACE_MORPHEMIZER = "AnkiMorphs: Simple Space Splitter"
_JAPANESE_MORPHEMIZER = "AnkiMorphs: Japanese"

_COLLECTION = FakeEnvironmentParams(
    initial_col="card_handling_collection",
    config=copy.deepcopy(default_config_dict),
)

_JAPANESE_COLLECTION = FakeEnvironmentParams(
    initial_col="some_studied_japanese_collection",
    config=copy.deepcopy(default_config_dict),
)

_KNOWN_MORPHS_COLLECTION = FakeEnvironmentParams(
    initial_col="known_morphs_collection",
    config=copy.deepcopy(config_known_morphs_enabled),
)

Mutation = Callable[[Collection, dict[str, Any], FakeEnvironment], None]


def _start_with_a_config_no_other_test_shares(
    fixture: FakeEnvironment, base_config: dict[str, Any] = default_config_dict
) -> tuple[Collection, dict[str, Any]]:
    config = copy.deepcopy(base_config)
    fixture.config = config
    fixture.mock_mw.addonManager.getConfig.return_value = config
    text_preprocessing.update_translation_table()
    return fixture.mock_mw.col, config


def _discard_the_cached_morphs() -> None:
    am_db = AnkiMorphsDB()
    am_db.drop_all_tables()
    am_db.con.close()


def _dump_am_db() -> dict[str, list[Any]]:
    am_db = AnkiMorphsDB()
    dump = {
        table: sorted(am_db.con.execute(f"SELECT * FROM {table}").fetchall())
        for table in ("Cards", "Morphs", "Card_Morph_Map")
    }
    am_db.con.close()
    return dump


def _assert_reusing_the_cache_matches_a_full_rebuild(collection: Collection) -> None:
    reused_collection = recalc_until_the_collection_stops_changing(collection)
    reused_db = _dump_am_db()

    _discard_the_cached_morphs()
    recalc()
    rebuilt_collection = dump_collection(collection)
    _discard_the_cached_morphs()
    recalc()
    rebuilt_db = _dump_am_db()

    assert reused_collection == rebuilt_collection

    for table, rows in reused_db.items():
        assert rows == rebuilt_db[table], table


def _first_note_id(collection: Collection) -> NoteId:
    return sorted(collection.find_notes(""))[0]


def _nothing_changed(
    _collection: Collection, _config: dict[str, Any], _fixture: FakeEnvironment
) -> None:
    pass


def _the_expression_changed(
    collection: Collection, _config: dict[str, Any], _fixture: FakeEnvironment
) -> None:
    note = collection.get_note(_first_note_id(collection))
    note.fields[0] = "a completely different sentence"
    collection.update_note(note)


def _a_note_was_added(
    collection: Collection, _config: dict[str, Any], _fixture: FakeEnvironment
) -> None:
    note_type = collection.models.by_name("Basic")
    assert note_type is not None
    note = collection.new_note(note_type)
    note["Front"] = "a brand new sentence"
    note["Back"] = "back"
    collection.add_note(note, collection.decks.all()[0]["id"])


def _a_note_was_removed(
    collection: Collection, _config: dict[str, Any], _fixture: FakeEnvironment
) -> None:
    collection.remove_notes([_first_note_id(collection)])


def _a_note_changed_note_type(
    collection: Collection, _config: dict[str, Any], _fixture: FakeEnvironment
) -> None:
    note = collection.get_note(_first_note_id(collection))
    old_note_type = collection.models.get(note.mid)
    new_note_type = collection.models.by_name("Basic (and reversed card)")
    assert old_note_type is not None
    assert new_note_type is not None
    collection.models.change(
        old_note_type, [note.id], new_note_type, {0: 0, 1: 1}, None
    )


def _a_card_was_studied(
    collection: Collection, _config: dict[str, Any], _fixture: FakeEnvironment
) -> None:
    card = collection.get_card(sorted(collection.find_cards(""))[0])
    card.type = CARD_TYPE_REV
    card.queue = QUEUE_TYPE_REV
    card.ivl = 250
    collection.update_card(card)


def _a_card_was_forgotten(
    collection: Collection, _config: dict[str, Any], _fixture: FakeEnvironment
) -> None:
    for card_id in sorted(collection.find_cards("")):
        card = collection.get_card(card_id)
        if card.type != CARD_TYPE_REV:
            continue
        card.type = CARD_TYPE_NEW
        card.queue = QUEUE_TYPE_NEW
        card.ivl = 0
        collection.update_card(card)
        return
    pytest.skip("the collection has no studied card to forget")


def _the_morphemizer_changed(
    _collection: Collection, config: dict[str, Any], fixture: FakeEnvironment
) -> None:
    config[RawConfigKeys.FILTERS][0][
        RawConfigFilterKeys.MORPHEMIZER_DESCRIPTION
    ] = _JAPANESE_MORPHEMIZER
    fixture.mock_mw.addonManager.getConfig.return_value = config


def _the_read_field_changed(
    _collection: Collection, config: dict[str, Any], fixture: FakeEnvironment
) -> None:
    config[RawConfigKeys.FILTERS][0][RawConfigFilterKeys.FIELD] = "Back"
    fixture.mock_mw.addonManager.getConfig.return_value = config


def _the_filter_tags_changed(
    _collection: Collection, config: dict[str, Any], fixture: FakeEnvironment
) -> None:
    config[RawConfigKeys.FILTERS][0][RawConfigFilterKeys.TAGS] = {
        "include": [],
        "exclude": ["am-known-manually"],
    }
    fixture.mock_mw.addonManager.getConfig.return_value = config


def _the_preprocessing_changed(
    _collection: Collection, config: dict[str, Any], fixture: FakeEnvironment
) -> None:
    config[RawConfigKeys.PREPROCESS_IGNORE_CUSTOM_CHARACTERS] = True
    config[RawConfigKeys.PREPROCESS_CUSTOM_CHARACTERS_TO_IGNORE] = "aeiou"
    fixture.mock_mw.addonManager.getConfig.return_value = config
    text_preprocessing.update_translation_table()


def _an_overlapping_filter_was_added(
    _collection: Collection, config: dict[str, Any], fixture: FakeEnvironment
) -> None:
    extra_filter = copy.deepcopy(config[RawConfigKeys.FILTERS][0])
    extra_filter[RawConfigFilterKeys.FIELD] = "Back"
    config[RawConfigKeys.FILTERS].append(extra_filter)
    fixture.mock_mw.addonManager.getConfig.return_value = config


_MUTATIONS: list[Mutation] = [
    _nothing_changed,
    _the_expression_changed,
    _a_note_was_added,
    _a_note_was_removed,
    _a_note_changed_note_type,
    _a_card_was_studied,
    _a_card_was_forgotten,
    _the_morphemizer_changed,
    _the_read_field_changed,
    _the_filter_tags_changed,
    _the_preprocessing_changed,
    _an_overlapping_filter_was_added,
]


@pytest.mark.parametrize("mutation", _MUTATIONS, ids=lambda m: m.__name__.strip("_"))
@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_reusing_the_cached_morphs_matches_a_full_rebuild(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment, mutation: Mutation
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )

    recalc_until_the_collection_stops_changing(collection)
    mutation(collection, config, fake_environment_fixture)
    _assert_reusing_the_cache_matches_a_full_rebuild(collection)


@pytest.mark.parametrize(
    "fake_environment_fixture", [_JAPANESE_COLLECTION], indirect=True
)
def test_reusing_the_cached_morphs_matches_a_full_rebuild_with_mecab(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    config[RawConfigKeys.FILTERS][0][
        RawConfigFilterKeys.MORPHEMIZER_DESCRIPTION
    ] = _JAPANESE_MORPHEMIZER
    fake_environment_fixture.mock_mw.addonManager.getConfig.return_value = config

    recalc_until_the_collection_stops_changing(collection)
    _the_expression_changed(collection, config, fake_environment_fixture)
    _assert_reusing_the_cache_matches_a_full_rebuild(collection)


def _spy_on_the_morphemizer(description: str = _SPACE_MORPHEMIZER) -> Any:
    morphemizer = morphemizer_utils.get_morphemizer_by_description(description)
    assert morphemizer is not None
    return mock.patch.object(
        type(morphemizer),
        "get_processed_morphs",
        side_effect=morphemizer.get_processed_morphs,
    )


def _extracted_expressions(spy: mock.Mock) -> list[str]:
    expressions: list[str] = []
    for call in spy.call_args_list:
        expressions += [text for text, _key in call.args[1]]
    return expressions


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_only_cards_whose_text_changed_are_sent_to_the_morphemizer(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    recalc()

    with _spy_on_the_morphemizer() as spy:
        recalc()
        assert not _extracted_expressions(spy)

        _the_expression_changed(collection, config, fake_environment_fixture)
        recalc()
        assert _extracted_expressions(spy) == ["a completely different sentence"]


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_a_new_addon_version_invalidates_the_cached_morphs(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    _start_with_a_config_no_other_test_shares(fake_environment_fixture)
    recalc()

    with mock.patch.object(am_globals, "__version__", "999.0.0"):
        with _spy_on_the_morphemizer() as spy:
            recalc()
            assert _extracted_expressions(spy)


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_changing_the_names_file_reextracts_every_card(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    _start_with_a_config_no_other_test_shares(fake_environment_fixture)
    recalc()

    with mock.patch.object(name_file_utils, "get_names_from_file", lambda: {"hello"}):
        with _spy_on_the_morphemizer() as spy:
            recalc()
            assert _extracted_expressions(spy)


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_a_database_from_an_older_ankimorphs_version_is_rebuilt(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, _config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    recalc()
    expected = dump_collection(collection)

    am_db = AnkiMorphsDB()
    with am_db.con:
        am_db.con.execute("DROP TABLE IF EXISTS Extraction_Signature")
        am_db.con.execute("DROP TABLE IF EXISTS Cards")
        am_db.con.execute("""
            CREATE TABLE Cards
            (
                card_id INTEGER PRIMARY KEY ASC,
                note_id INTEGER,
                note_type_id INTEGER,
                card_type INTEGER,
                fields TEXT,
                tags TEXT
            )
            """)
    am_db.con.close()

    recalc()
    assert dump_collection(collection) == expected


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_a_card_that_moves_to_a_filter_with_another_morphemizer_is_reextracted(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )

    reversed_filter = copy.deepcopy(config[RawConfigKeys.FILTERS][0])
    reversed_filter[RawConfigFilterKeys.NOTE_TYPE] = "Basic (and reversed card)"
    reversed_filter[RawConfigFilterKeys.MORPHEMIZER_DESCRIPTION] = _JAPANESE_MORPHEMIZER
    config[RawConfigKeys.FILTERS].append(reversed_filter)
    fake_environment_fixture.mock_mw.addonManager.getConfig.return_value = config

    recalc_until_the_collection_stops_changing(collection)
    _a_note_changed_note_type(collection, config, fake_environment_fixture)
    _assert_reusing_the_cache_matches_a_full_rebuild(collection)


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_a_card_that_moves_to_a_filter_reading_another_field_is_reextracted(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )

    reversed_filter = copy.deepcopy(config[RawConfigKeys.FILTERS][0])
    reversed_filter[RawConfigFilterKeys.NOTE_TYPE] = "Basic (and reversed card)"
    reversed_filter[RawConfigFilterKeys.FIELD] = "Back"
    config[RawConfigKeys.FILTERS].append(reversed_filter)
    fake_environment_fixture.mock_mw.addonManager.getConfig.return_value = config

    recalc_until_the_collection_stops_changing(collection)
    _a_note_changed_note_type(collection, config, fake_environment_fixture)
    _assert_reusing_the_cache_matches_a_full_rebuild(collection)


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_highest_learning_intervals_go_down_when_a_card_is_forgotten(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, _config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )

    card = collection.get_card(sorted(collection.find_cards(""))[0])
    card.type = CARD_TYPE_REV
    card.queue = QUEUE_TYPE_REV
    card.ivl = 365
    collection.update_card(card)
    recalc()

    am_db = AnkiMorphsDB()
    intervals = am_db.get_all_highest_inflection_learning_intervals()
    am_db.con.close()
    assert max(intervals.values()) == 365

    card = collection.get_card(card.id)
    card.type = CARD_TYPE_NEW
    card.queue = QUEUE_TYPE_NEW
    card.ivl = 0
    collection.update_card(card)
    recalc()

    am_db = AnkiMorphsDB()
    intervals_after = am_db.get_all_highest_inflection_learning_intervals()
    am_db.con.close()
    assert max(intervals_after.values()) < 365


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_removing_a_note_leaves_no_morphs_behind(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, _config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    recalc()

    note_id = _first_note_id(collection)
    removed_card_ids = set(collection.find_cards(f"nid:{note_id}"))
    assert removed_card_ids

    collection.remove_notes([note_id])
    recalc()

    am_db = AnkiMorphsDB()
    remaining = {
        row[0]
        for row in am_db.con.execute("SELECT card_id FROM Card_Morph_Map").fetchall()
    }
    am_db.con.close()
    assert not remaining & removed_card_ids


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_a_card_leaving_its_note_filter_leaves_no_morphs_behind(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    recalc()

    note = collection.get_note(_first_note_id(collection))
    note.tags.append("excluded-tag")
    collection.update_note(note)
    excluded_card_ids = set(collection.find_cards(f"nid:{note.id}"))

    config[RawConfigKeys.FILTERS][0][RawConfigFilterKeys.TAGS] = {
        "include": [],
        "exclude": ["excluded-tag"],
    }
    fake_environment_fixture.mock_mw.addonManager.getConfig.return_value = config
    recalc()

    am_db = AnkiMorphsDB()
    remaining = {
        row[0]
        for row in am_db.con.execute("SELECT card_id FROM Card_Morph_Map").fetchall()
    }
    am_db.con.close()
    assert not remaining & excluded_card_ids


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_overlapping_filters_on_one_note_type_disable_the_cache(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    _collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    recalc()

    _an_overlapping_filter_was_added(
        fake_environment_fixture.mock_mw.col, config, fake_environment_fixture
    )

    with _spy_on_the_morphemizer() as spy:
        recalc()
        assert _extracted_expressions(spy)
        recalc()
        assert _extracted_expressions(spy)


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_two_filters_reading_different_fields_keep_the_morphs_of_both(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )

    _an_overlapping_filter_was_added(collection, config, fake_environment_fixture)
    recalc_until_the_collection_stops_changing(collection)
    _the_expression_changed(collection, config, fake_environment_fixture)
    _assert_reusing_the_cache_matches_a_full_rebuild(collection)


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_morphs_seen_today_are_cleared_by_every_recalc(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    _start_with_a_config_no_other_test_shares(fake_environment_fixture)
    recalc()

    am_db = AnkiMorphsDB()
    with am_db.con:
        am_db.con.execute("INSERT OR IGNORE INTO Seen_Morphs VALUES ('a', 'a')")
    am_db.con.close()

    recalc()

    am_db = AnkiMorphsDB()
    seen = am_db.con.execute("SELECT * FROM Seen_Morphs").fetchall()
    am_db.con.close()
    assert not seen


@pytest.mark.parametrize(
    "fake_environment_fixture", [_KNOWN_MORPHS_COLLECTION], indirect=True
)
def test_known_morphs_files_are_reimported_on_every_recalc(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    _start_with_a_config_no_other_test_shares(
        fake_environment_fixture, config_known_morphs_enabled
    )
    recalc()
    with_files = _dump_am_db()["Morphs"]
    assert with_files

    am_db = AnkiMorphsDB()
    with am_db.con:
        am_db.con.execute("DELETE FROM Morphs")
    am_db.con.close()

    recalc()
    assert _dump_am_db()["Morphs"] == with_files


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_the_card_morph_map_is_identical_to_a_full_rebuild(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    recalc_until_the_collection_stops_changing(collection)

    _a_note_was_added(collection, config, fake_environment_fixture)
    recalc_until_the_collection_stops_changing(collection)
    reused = _dump_am_db()["Card_Morph_Map"]

    _discard_the_cached_morphs()
    recalc()
    assert _dump_am_db()["Card_Morph_Map"] == reused


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_an_interrupted_recalc_does_not_leave_a_cache_that_is_believed_valid(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    recalc_until_the_collection_stops_changing(collection)
    expected = _dump_am_db()

    _the_expression_changed(collection, config, fake_environment_fixture)

    with mock.patch.object(
        AnkiMorphsDB, "replace_morph_table", side_effect=RuntimeError("interrupted")
    ):
        with pytest.raises(RuntimeError):
            recalc()

    am_db = AnkiMorphsDB()
    signature = am_db.get_extraction_signature()
    am_db.con.close()
    assert signature is None

    recalc_until_the_collection_stops_changing(collection)
    reused = _dump_am_db()

    _discard_the_cached_morphs()
    recalc()
    rebuilt = _dump_am_db()

    assert reused != expected
    for table, rows in reused.items():
        assert rows == rebuilt[table], table


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_an_interrupted_recalc_reextracts_the_morphs_of_every_card(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    _start_with_a_config_no_other_test_shares(fake_environment_fixture)
    recalc()

    with mock.patch.object(
        AnkiMorphsDB, "replace_morph_table", side_effect=RuntimeError("interrupted")
    ):
        with pytest.raises(RuntimeError):
            recalc()

    with _spy_on_the_morphemizer() as spy:
        recalc()
        assert _extracted_expressions(spy)


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_the_extraction_signature_survives_an_unrelated_settings_change(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    _collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    recalc()

    config[RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_ALL_MORPHS_WEIGHT] = 42
    fake_environment_fixture.mock_mw.addonManager.getConfig.return_value = config

    with _spy_on_the_morphemizer() as spy:
        recalc()
        assert not _extracted_expressions(spy)


@pytest.mark.parametrize("fake_environment_fixture", [_COLLECTION], indirect=True)
def test_ignoring_suspended_cards_is_not_part_of_the_extraction_signature(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    # This setting decides which cards are read, not how the text of a card is
    # tokenized, so it is deliberately left out of the extraction signature. A
    # card it excludes is handled as an orphan and a card it lets back in is
    # handled as a new one. The cache surviving the change therefore has to
    # still produce what a full rebuild produces -- in both directions.
    collection, config = _start_with_a_config_no_other_test_shares(
        fake_environment_fixture
    )
    card = collection.get_card(sorted(collection.find_cards(""))[0])
    card.queue = QUEUE_TYPE_SUSPENDED
    collection.update_card(card)

    config[RawConfigKeys.PREPROCESS_IGNORE_SUSPENDED_CARDS_CONTENT] = False
    recalc()

    config[RawConfigKeys.PREPROCESS_IGNORE_SUSPENDED_CARDS_CONTENT] = True
    _assert_reusing_the_cache_matches_a_full_rebuild(collection)

    config[RawConfigKeys.PREPROCESS_IGNORE_SUSPENDED_CARDS_CONTENT] = False
    _assert_reusing_the_cache_matches_a_full_rebuild(collection)
