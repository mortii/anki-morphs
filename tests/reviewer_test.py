import json
import os
import shutil
from unittest import mock

import pytest
from aqt import setupLangAndBackend
from aqt.reviewer import Reviewer

# A bug in the anki module leads to cyclic imports if these are placed higher
from ankimorphs import (  # isort:skip pylint:disable=wrong-import-order
    config,
    reviewing_utils,
)

from anki import hooks  # isort:skip pylint:disable=wrong-import-order
from anki.collection import Collection  # isort:skip pylint:disable=wrong-import-order


@pytest.fixture
def fake_environment():
    tests_path = os.path.join(os.path.abspath("tests"), "data")
    collection_path_original = os.path.join(tests_path, "collection.anki2")
    collection_path_duplicate = os.path.join(tests_path, "duplicate_collection.anki2")
    collection_path_duplicate_media = os.path.join(
        tests_path, "duplicate_collection.media"
    )

    # If dst already exists, it will be replaced
    shutil.copyfile(collection_path_original, collection_path_duplicate)

    mock_mw = mock.Mock(spec=preferences.mw)  # can use any mw to spec
    mock_mw.col = Collection(collection_path_duplicate)
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )

    _config_data = None
    with open("ankimorphs/config.json", encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw.addonManager.getConfig.return_value = _config_data

    mock_mw.reviewer = Reviewer(mock_mw)
    mock_mw.reviewer._showQuestion = lambda: None

    Reviewer.nextCard = hooks.wrap(
        Reviewer.nextCard, reviewing_utils.am_next_card, "around"
    )
    Reviewer._shortcutKeys = hooks.wrap(
        Reviewer._shortcutKeys, reviewing_utils.am_reviewer_shortcut_keys, "around"
    )

    mock_show_skipped_cards = mock.Mock(name="show_skipped_cards")

    patch_preferences_mw = mock.patch.object(preferences, "mw", mock_mw)

    patch_show_skipped_cards = mock.patch(
        "ankimorphs.reviewing_utils.SkippedCards.show_tooltip_of_skipped_cards",
        mock_show_skipped_cards,
    )

    patch_preferences_mw.start()
    patch_show_skipped_cards.start()

    yield mock_mw

    mock_mw.col.close()
    patch_preferences_mw.stop()
    patch_show_skipped_cards.stop()

    os.remove(collection_path_duplicate)
    shutil.rmtree(collection_path_duplicate_media)


def test_next_card(fake_environment):
    mock_mw = fake_environment

    mock_mw.reviewer.nextCard()

    # search in browser with 'cid:{id}', e.g 'cid:1691325167978'
    print(f"mock_mw.reviewer.card.id: {mock_mw.reviewer.card.id}")

    mock_mw.col.sched.answerCard(mock_mw.reviewer.card, ease=3)

    mock_mw.reviewer.nextCard()

    # search in browser with 'cid:{id}', e.g 'cid:1691325167978'
    print(f"mock_mw.reviewer.card.id: {mock_mw.reviewer.card.id}")

    # assert mock_mw.reviewer.card.id == 1691326511011
    assert True


@pytest.mark.xfail
def test_set_known_and_skip(fake_environment):
    mock_mw = fake_environment

    mock_mw.reviewer.nextCard()

    # search in browser with 'cid:{id}', e.g 'cid:1691325167978'

    # card = mock_mw.col.get_card(1695148982363)
    #
    # pprint.pprint(vars(card))

    print(f"mock_mw.reviewer.card.id: {mock_mw.reviewer.card.id}")

    reviewing_utils._set_card_as_known_and_skip(mock_mw.reviewer)

    # mock_mw.col.sched.answerCard(mock_mw.reviewer.card, ease=3)

    # mock_mw.reviewer.nextCard()

    # search in browser with 'cid:{id}', e.g 'cid:1691325167978'
    print(f"mock_mw.reviewer.card.id: {mock_mw.reviewer.card.id}")

    assert mock_mw.reviewer.card.id == 1691325816182


@pytest.mark.xfail
def test_focus_morph():
    assert False
