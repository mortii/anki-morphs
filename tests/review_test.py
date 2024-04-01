import json
import os
import shutil
import sqlite3
from functools import partial
from unittest import mock

import aqt
import pytest
from anki.collection import Collection
from anki.consts import CardQueue
from aqt import setupLangAndBackend
from aqt.reviewer import Reviewer

from ankimorphs import (
    AnkiMorphsConfig,
    AnkiMorphsDB,
    ankimorphs_config,
    ankimorphs_db,
    reviewing_utils,
)
from ankimorphs.skipped_cards import SkippedCards


class MockDB(AnkiMorphsDB):
    # We subclass to use a db with a different file name
    def __init__(self):
        super().__init__()
        tests_path = os.path.join(
            os.path.abspath("tests"), "data", "populated_ankimorphs_copy.db"
        )
        self.con: sqlite3.Connection = sqlite3.connect(tests_path)


@pytest.fixture
def fake_environment():
    tests_path = os.path.join(os.path.abspath("tests"), "data")

    collection_path_original = os.path.join(tests_path, "collection.anki2")
    collection_path_duplicate = os.path.join(tests_path, "duplicate_collection.anki2")
    collection_path_duplicate_media = os.path.join(
        tests_path, "duplicate_collection.media"
    )

    test_db_original_path = os.path.join(tests_path, "populated_ankimorphs.db")
    test_db_copy_path = os.path.join(tests_path, "populated_ankimorphs_copy.db")

    # If the destination already exists, it will be replaced
    shutil.copyfile(collection_path_original, collection_path_duplicate)
    shutil.copyfile(test_db_original_path, test_db_copy_path)

    _config_data = None
    with open("tests/data/meta.json", encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw = mock.Mock(spec=aqt.mw)
    mock_mw.col = Collection(collection_path_duplicate)
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )
    mock_mw.pm.profileFolder.return_value = os.path.join("tests", "data")
    mock_mw.progress.want_cancel.return_value = False
    mock_mw.addonManager.getConfig.return_value = _config_data["config"]
    mock_mw.reviewer = Reviewer(mock_mw)
    mock_mw.reviewer._showQuestion = lambda: None

    # tooltip obviously tries to do gui stuff which breaks tests
    mock_tooltip = mock.Mock(spec=aqt.utils.tooltip)

    patch_am_db_mw = mock.patch.object(ankimorphs_db, "mw", mock_mw)
    patch_config_mw = mock.patch.object(ankimorphs_config, "mw", mock_mw)
    patch_reviewing_mw = mock.patch.object(reviewing_utils, "mw", mock_mw)
    patch_am_db = mock.patch.object(reviewing_utils, "AnkiMorphsDB", MockDB)
    patch_tooltip = mock.patch.object(reviewing_utils, "tooltip", mock_tooltip)

    patch_am_db_mw.start()
    patch_config_mw.start()
    patch_reviewing_mw.start()
    patch_am_db.start()
    patch_tooltip.start()

    yield mock_mw

    mock_mw.col.close()
    patch_am_db_mw.stop()
    patch_config_mw.stop()
    patch_reviewing_mw.stop()
    patch_am_db.stop()
    patch_tooltip.stop()

    os.remove(test_db_copy_path)
    os.remove(collection_path_duplicate)
    shutil.rmtree(collection_path_duplicate_media)


def test_custom_review(fake_environment):
    mock_mw = fake_environment
    am_config = AnkiMorphsConfig()
    skipped_cards = SkippedCards()

    # we have to patch this part later than the others because
    # AnkiMorphsConfig also uses the mocked mw, so it has to be instantiated
    # before we can mock the reviewer functions
    mock_mw.reviewer.nextCard = partial(
        reviewing_utils._get_next_card_background,
        collection=mock_mw.col,
        am_config=am_config,
        skipped_cards=skipped_cards,
    )

    mock_mw.reviewer._shortcutKeys = partial(
        reviewing_utils.am_reviewer_shortcut_keys,
        self=mock_mw.reviewer,
        _old=Reviewer._shortcutKeys,
    )

    patch_reviewing_mw = mock.patch.object(reviewing_utils, "mw", mock_mw)

    # the reviewer uses the 'Demon Slayer' deck because gather order has
    # not been changed in the deck options
    # IMPORTANT: the collection.anki2 file actually stores reviewer info,
    # which means we have to initiate a review (click study now on the deck),
    # and then place the collection.anki2 file in tests/data...
    first_card = 1608533847165
    second_card = 1691325165708
    third_card = 1691325165785

    mock_mw.reviewer.nextCard()
    assert mock_mw.reviewer.card.id == first_card

    mock_mw.col.sched.answerCard(mock_mw.reviewer.card, ease=3)  # 'good' pressed
    mock_mw.reviewer.nextCard()
    assert mock_mw.reviewer.card.id == second_card

    # check if 'set known and skip' works
    reviewing_utils._set_card_as_known_and_skip(am_config)
    assert mock_mw.col.get_card(second_card).queue == CardQueue(-2)  # buried
    assert mock_mw.reviewer.card.id == third_card

    patch_reviewing_mw.stop()
