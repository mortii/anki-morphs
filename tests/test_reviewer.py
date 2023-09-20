import os
import pprint
from unittest import mock

import pytest

from aqt.reviewer import Reviewer

from ankimorphs import preferences, reviewing_utils
from tests.fake_config import FakeConfig
from aqt import setupLangAndBackend
from anki.collection import Collection

from anki import hooks
import shutil


@pytest.fixture
def fake_environment():
    collection_path_original = os.path.join(
        os.getcwd(), "tests", "data", "collection.anki2"
    )
    collection_path_duplicate = os.path.join(
        os.getcwd(), "tests", "data", "duplicate_collection.anki2"
    )

    # If dst already exists, it will be replaced
    shutil.copyfile(collection_path_original, collection_path_duplicate)

    mock_mw = mock.Mock(spec=preferences.mw)  # can use any mw to spec
    mock_mw.col = Collection(collection_path_duplicate)
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )
    mock_mw.reviewer = Reviewer(mock_mw)
    mock_mw.reviewer._showQuestion = lambda: None

    Reviewer.nextCard = hooks.wrap(
        Reviewer.nextCard, reviewing_utils.my_next_card, "around"
    )
    # hooks.field_filter.append(reviewing_utils.highlight)
    Reviewer._shortcutKeys = hooks.wrap(
        Reviewer._shortcutKeys, reviewing_utils.my_reviewer_shortcut_keys, "around"
    )

    mock_config_py = FakeConfig()

    mock_show_skipped_cards = mock.Mock(name="show_skipped_cards")

    patch_preferences_mw = mock.patch.object(preferences, "mw", mock_mw)
    patch_preferences_config_py = mock.patch.object(
        preferences, "config_py", mock_config_py
    )
    patch_show_skipped_cards = mock.patch(
        "ankimorphs.reviewing_utils.SkippedCards.show_tooltip_of_skipped_cards",
        mock_show_skipped_cards,
    )

    patch_preferences_mw.start()
    patch_preferences_config_py.start()
    patch_show_skipped_cards.start()

    yield mock_mw

    mock_mw.col.close()
    patch_preferences_mw.stop()
    patch_preferences_config_py.stop()
    patch_show_skipped_cards.stop()


def mock_get_config_py_preference(key):
    return FakeConfig().default[key]


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

    reviewing_utils.set_known_and_skip(mock_mw.reviewer)

    # mock_mw.col.sched.answerCard(mock_mw.reviewer.card, ease=3)

    # mock_mw.reviewer.nextCard()

    # search in browser with 'cid:{id}', e.g 'cid:1691325167978'
    print(f"mock_mw.reviewer.card.id: {mock_mw.reviewer.card.id}")

    assert mock_mw.reviewer.card.id == 1691325816182


@pytest.mark.xfail
def test_focus_morph():
    assert False
