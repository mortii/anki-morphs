import json
import os
import shutil
from collections.abc import Sequence
from typing import Optional
from unittest import mock

import aqt
import pytest
from anki.cards import Card
from anki.collection import Collection
from anki.models import ModelManager, NotetypeDict, NotetypeId
from anki.notes import Note
from aqt import setupLangAndBackend

from ankimorphs import (
    ankimorphs_db,
    ankimorphs_globals,
    config,
    name_file_utils,
    recalc,
)


class CardData:
    __slots__ = (
        "due",
        "extra_field_unknowns",
        "extra_field_unknowns_count",
        "extra_field_highlighted",
        "extra_field_difficulty",
        "tags",
    )

    def __init__(  # pylint:disable=too-many-arguments
        self,
        due: int,
        extra_field_unknowns: str,
        extra_field_unknowns_count: str,
        extra_field_highlighted: str,
        extra_field_difficulty: str,
        tags: list[str],
    ):
        self.due = due
        self.extra_field_unknowns = extra_field_unknowns
        self.extra_field_unknowns_count = extra_field_unknowns_count
        self.extra_field_highlighted = extra_field_highlighted
        self.extra_field_difficulty = extra_field_difficulty
        self.tags = tags

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, CardData)
        return all(
            [
                self.due == other.due,
                self.extra_field_unknowns == other.extra_field_unknowns,
                self.extra_field_unknowns_count == other.extra_field_unknowns_count,
                self.extra_field_highlighted == other.extra_field_highlighted,
                self.extra_field_difficulty == other.extra_field_difficulty,
                self.tags == other.tags,
            ]
        )


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment():
    # deck used is found here: https://github.com/mortii/anki-decks
    # "Japanese Sentences_v5.apkg"
    # the collection.ank2 file only stores the collection data, not media.

    tests_path = os.path.join(os.path.abspath("tests"), "data")
    collection_path_original = os.path.join(tests_path, "collection.anki2")
    collection_path_duplicate = os.path.join(tests_path, "duplicate_collection.anki2")
    collection_path_duplicate_media = os.path.join(
        tests_path, "duplicate_collection.media"
    )

    print(f"current dir: {os.getcwd()}")

    _config_data = None
    with open(os.path.join(tests_path, "meta.json"), encoding="utf-8") as file:
        _config_data = json.load(file)

    # If the destination already exists, it will be replaced
    shutil.copyfile(collection_path_original, collection_path_duplicate)

    mock_mw = mock.Mock(spec=aqt.mw)
    mock_mw.col = Collection(collection_path_duplicate)
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )
    mock_mw.pm.profileFolder.return_value = os.path.join("tests", "data")
    mock_mw.progress.want_cancel.return_value = False
    mock_mw.addonManager.getConfig.return_value = _config_data["config"]

    patch_recalc_mw = mock.patch.object(recalc, "mw", mock_mw)
    morph_db_mw = mock.patch.object(ankimorphs_db, "mw", mock_mw)
    patch_config_mw = mock.patch.object(config, "mw", mock_mw)
    patch_name_file_utils_mw = mock.patch.object(name_file_utils, "mw", mock_mw)

    patch_recalc_mw.start()
    morph_db_mw.start()
    patch_config_mw.start()
    patch_name_file_utils_mw.start()

    yield mock_mw.col, Collection(collection_path_original)

    mock_mw.col.close()

    patch_recalc_mw.stop()
    morph_db_mw.stop()
    patch_config_mw.stop()
    patch_name_file_utils_mw.stop()

    os.remove(collection_path_duplicate)
    shutil.rmtree(collection_path_duplicate_media)


def test_recalc(fake_environment):  # pylint:disable=too-many-locals
    mock_collection, original_collection = fake_environment

    note_type_id: NotetypeId = NotetypeId(
        1691076536776  # found in tests/data/meta.json
    )
    model_manager: ModelManager = ModelManager(mock_collection)
    note_type_dict: Optional[NotetypeDict] = model_manager.get(note_type_id)
    assert note_type_dict is not None
    note_type_field_name_dict = model_manager.field_map(note_type_dict)

    extra_field_unknowns: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_UNKNOWNS
    ][0]

    extra_field_unknowns_count: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT
    ][0]

    extra_field_highlighted: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
    ][0]

    extra_field_difficulty: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_DIFFICULTY
    ][0]

    card_due_dict: dict[int, CardData] = {}

    original_collection_cards = original_collection.find_cards("")
    card_collection_length = 37323
    assert len(original_collection_cards) == card_collection_length

    for card_id in original_collection_cards:
        card: Card = original_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        difficulty_field = note.fields[extra_field_difficulty]

        card_due_dict[card_id] = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_difficulty=difficulty_field,
            tags=note.tags,
        )

    recalc._recalc_background_op(mock_collection)

    mock_collection_cards: Sequence[int] = mock_collection.find_cards("")
    assert len(mock_collection_cards) == card_collection_length

    for card_id in mock_collection_cards:
        card: Card = mock_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        difficulty_field = note.fields[extra_field_difficulty]

        new_card_data = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_difficulty=difficulty_field,
            tags=note.tags,
        )

        assert card_due_dict[card_id] == new_card_data


@pytest.mark.xfail
def test_names_txt_file():
    # there isn't really a great way to test name.txt since removing
    # morphs will cause a cascade of due changes...
    assert False
