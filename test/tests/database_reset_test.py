from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    fake_environment_fixture,
)
from test.recalc_helpers import dump_collection, recalc
from unittest import mock

import ankimorphs
from ankimorphs.ankimorphs_db import AnkiMorphsDB


def _column_names(am_db: AnkiMorphsDB, table: str) -> list[str]:
    return [row[1] for row in am_db.con.execute(f"PRAGMA table_info({table})")]


def test_extraction_cache_schema_is_source_aware(
    fake_environment_fixture: FakeEnvironment,  # pylint:disable=unused-argument
) -> None:
    with AnkiMorphsDB() as am_db:
        am_db.drop_all_tables()
        am_db.create_all_tables()

        assert _column_names(am_db, "Cards") == [
            "card_id",
            "note_id",
            "note_type_id",
            "card_type",
            "tags",
            "memory_strength",
        ]
        assert _column_names(am_db, "Note_Sources") == [
            "note_id",
            "source_key",
            "expression_hash",
        ]
        assert _column_names(am_db, "Note_Source_Morph_Map") == [
            "note_id",
            "source_key",
            "morph_lemma",
            "morph_inflection",
        ]


def test_reset_database_clears_cache_without_changing_collection(
    fake_environment_fixture: FakeEnvironment,
) -> None:
    recalc()
    collection = fake_environment_fixture.mock_mw.col
    before = dump_collection(collection)
    with AnkiMorphsDB() as am_db:
        assert am_db.get_source_hashes()
        assert am_db.get_extraction_signature() is not None

    ankimorphs._reset_database_background()

    with AnkiMorphsDB() as am_db:
        for table in (
            "Cards",
            "Morphs",
            "Card_Morph_Map",
            "Seen_Morphs",
            "Note_Sources",
            "Note_Source_Morph_Map",
        ):
            assert am_db.con.execute(f"SELECT * FROM {table}").fetchall() == []
        assert am_db.get_extraction_signature() is None
    assert dump_collection(collection) == before
    recalc()
    with AnkiMorphsDB() as am_db:
        assert am_db.get_source_hashes()
        assert am_db.get_extraction_signature() is not None


def test_declining_reset_preserves_database(
    fake_environment_fixture: FakeEnvironment,
) -> None:
    recalc()
    with AnkiMorphsDB() as am_db:
        before = list(am_db.con.iterdump())
    with (
        mock.patch.object(ankimorphs, "mw", fake_environment_fixture.mock_mw),
        mock.patch.object(
            ankimorphs.message_box_utils, "show_warning_box", return_value=False
        ),
    ):
        ankimorphs.reset_database()
    with AnkiMorphsDB() as am_db:
        assert list(am_db.con.iterdump()) == before
