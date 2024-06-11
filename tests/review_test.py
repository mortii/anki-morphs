from functools import partial

import pytest
from aqt.reviewer import Reviewer

from ankimorphs import reviewing_utils
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.reviewing_utils import SkippedCards

from .environment_setup_for_tests import (  # pylint:disable=unused-import
    FakeEnvironment,
    fake_environment,
)
from .fake_configs import config_lemma_priority


@pytest.mark.parametrize(
    "fake_environment",
    [("lemma_priority_collection", config_lemma_priority)],
    indirect=True,
)
def test_custom_review(fake_environment: FakeEnvironment):
    mock_mw = fake_environment.mock_mw
    mock_db = fake_environment.mock_db
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

    first_card = 1715776939301
    second_card = 1717943898444

    # print("cards:")
    # mock_db.print_table("Cards")
    # print("Card_Morph_Map:")
    # mock_db.print_table("Card_Morph_Map")
    # print("Morphs:")
    # mock_db.print_table("Morphs")

    mock_mw.reviewer.nextCard()
    assert mock_mw.reviewer.card.id == first_card

    # directly calling this instead of calling "insert_seen_morphs" from __init__.py
    mock_db.update_seen_morphs_today_single_card(first_card)

    mock_mw.col.sched.answerCard(mock_mw.reviewer.card, ease=3)  # 'good' pressed
    mock_mw.reviewer.nextCard()
    assert mock_mw.reviewer.card.id == second_card

    # check if 'set known and skip' works
    # reviewing_utils._set_card_as_known_and_skip(am_config)
    # assert mock_mw.col.get_card(second_card).queue == CardQueue(-2)  # buried
    # assert mock_mw.reviewer.card.id == third_card
