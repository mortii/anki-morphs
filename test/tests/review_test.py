from functools import partial
from test.fake_configs import (
    config_inflection_evaluation,
    config_lemma_evaluation_lemma_extra_fields,
)
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)

import pytest
from anki.consts import CardQueue
from aqt.reviewer import Reviewer

from ankimorphs import reviewing_utils
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.reviewing_utils import SkippedCards

################################################################
#                  CASE: SKIP INFLECTIONS
################################################################
# Config contains "lemma evaluation", i.e. we want to skip subsequent
# cards that have the same lemmas as those studied before
################################################################
case_skip_inflections_params = FakeEnvironmentParams(
    collection="lemma_evaluation_lemma_extra_fields_collection",
    config=config_lemma_evaluation_lemma_extra_fields,
    am_db="lemma_evaluation.db",
)
case_skip_inflections_expected = [1715776939301, 1718190526053, 1717943898444]


################################################################
#               CASE: DON'T SKIP INFLECTIONS
################################################################
# Config contains "inflection evaluation", i.e. we DON'T want to
# skip any subsequent cards that have the same lemmas as those
# studied before
################################################################
case_dont_skip_inflections_params = FakeEnvironmentParams(
    collection="lemma_evaluation_lemma_extra_fields_collection",
    config=config_inflection_evaluation,
    am_db="lemma_evaluation.db",
)
case_dont_skip_inflections_expected = [1715776939301, 1715776946917, 1715776953867]


@pytest.mark.parametrize(
    "fake_environment_fixture, expected_results",
    [
        (case_skip_inflections_params, case_skip_inflections_expected),
        (case_dont_skip_inflections_params, case_dont_skip_inflections_expected),
    ],
    indirect=["fake_environment_fixture"],
)
def test_custom_review(
    fake_environment_fixture: FakeEnvironment, expected_results: list[int]
) -> None:
    mock_mw = fake_environment_fixture.mock_mw
    mock_db = fake_environment_fixture.mock_db
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
