from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    fake_environment_fixture,
)
from test.recalc_helpers import dump_collection, recalc
from unittest import mock

import ankimorphs
from ankimorphs.ankimorphs_db import AnkiMorphsDB


def test_reset_database_clears_cache_without_changing_collection(
    fake_environment_fixture: FakeEnvironment,
) -> None:
    recalc()
    collection = fake_environment_fixture.mock_mw.col
    before = dump_collection(collection)
    with AnkiMorphsDB() as am_db:
        assert am_db.get_expression_hashes()
        assert am_db.get_extraction_signature() is not None

    ankimorphs._reset_database_background()

    with AnkiMorphsDB() as am_db:
        for table in ("Cards", "Morphs", "Card_Morph_Map", "Seen_Morphs"):
            assert am_db.con.execute(f"SELECT * FROM {table}").fetchall() == []
        assert am_db.get_extraction_signature() is None
    assert dump_collection(collection) == before
    recalc()
    with AnkiMorphsDB() as am_db:
        assert am_db.get_expression_hashes()
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
