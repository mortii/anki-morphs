from functools import partial

import pytest
from anki.consts import CardQueue
from aqt.reviewer import Reviewer

from ankimorphs import reviewing_utils
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.reviewing_utils import SkippedCards

from .environment_setup_for_tests import (  # pylint:disable=unused-import
    FakeEnvironment,
    fake_environment,
)
from .fake_configs import config_inflection_priority, config_lemma_priority

expected_lemma_priority_cards = [1715776939301, 1718190526053, 1717943898444]
expected_inflection_priority_cards = [1715776939301, 1715776946917, 1715776953867]


@pytest.mark.parametrize(
    "fake_environment, expected_results",
    [
        (
            ("lemma_priority_collection", config_lemma_priority),
            expected_lemma_priority_cards,
        ),
        (
            ("lemma_priority_collection", config_inflection_priority),
            expected_inflection_priority_cards,
        ),
    ],
    indirect=["fake_environment"],
)
def test_custom_review(fake_environment: FakeEnvironment, expected_results: list[int]):
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

    first_card = expected_results[0]
    second_card = expected_results[1]
    third_card = expected_results[2]

    mock_mw.reviewer.nextCard()
    assert mock_mw.reviewer.card.id == first_card

    # directly calling this instead of calling "insert_seen_morphs" from __init__.py
    mock_db.update_seen_morphs_today_single_card(first_card)

    mock_mw.col.sched.answerCard(mock_mw.reviewer.card, ease=3)  # 'good' pressed
    mock_mw.reviewer.nextCard()
    assert mock_mw.reviewer.card.id == second_card

    # check if 'set known and skip' works
    reviewing_utils._set_card_as_known_and_skip(am_config)
    assert mock_mw.col.get_card(second_card).queue == CardQueue(-2)  # buried
    assert mock_mw.reviewer.card.id == third_card
