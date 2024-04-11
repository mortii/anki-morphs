from functools import partial

import pytest
from anki.consts import CardQueue
from aqt.reviewer import Reviewer

from ankimorphs import reviewing_utils
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.reviewing_utils import SkippedCards

from .environment_setup_for_tests import (  # pylint:disable=unused-import
    FakeEnvironment,
    config_big_japanese_collection,
    fake_environment,
)


@pytest.mark.parametrize(
    "fake_environment",
    [("big-japanese-collection", config_big_japanese_collection)],
    indirect=True,
)
def test_custom_review(fake_environment: FakeEnvironment):
    mock_mw = fake_environment.mock_mw
    am_config = AnkiMorphsConfig()
    skipped_cards = SkippedCards()

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

    # the reviewer uses the 'Demon Slayer' deck because gather order has
    # not been changed in the deck options
    # IMPORTANT: the collection.anki2 file actually stores reviewer info,
    # which means we have to initiate a review (click study now on the deck),
    # and then place the collection.anki2 file in test/data...
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
