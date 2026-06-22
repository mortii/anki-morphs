import copy
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
from unittest.mock import Mock

import pytest
from anki.consts import CardQueue
from aqt.reviewer import Reviewer

from ankimorphs import insert_seen_morphs, reviewing_utils
from ankimorphs.ankimorphs_config import AnkiMorphsConfig, RawConfigKeys
from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.reviewing_utils import SkippedCards


@pytest.fixture
def mocked_reviewer_and_db(
    fake_environment_fixture: FakeEnvironment,
) -> tuple[Mock, AnkiMorphsDB]:
    """Prepare reviewer with custom background nextCard and shortcut keys."""
    mock_mw = fake_environment_fixture.mock_mw
    mock_db = fake_environment_fixture.mock_db

    am_config = AnkiMorphsConfig()
    skipped_cards = SkippedCards()

    reviewing_utils.init_undo_targets()

    # Patch nextCard to use custom background function
    mock_mw.reviewer.nextCard = partial(
        reviewing_utils._get_next_card_background,
        am_config=am_config,
        skipped_cards=skipped_cards,
    )

    # Patch shortcut keys
    mock_mw.reviewer._shortcutKeys = partial(
        reviewing_utils.am_reviewer_shortcut_keys,
        self=mock_mw.reviewer,
        _old=Reviewer._shortcutKeys,
    )

    return mock_mw, mock_db


test_cases_morph_infection = [
    ################################################################
    #                  CASE: SKIP INFLECTIONS
    ################################################################
    # Config contains "lemma evaluation", i.e. we want to skip subsequent
    # cards that have the same lemmas as those studied before
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            initial_col="lemma_evaluation_lemma_extra_fields_collection",
            config=config_lemma_evaluation_lemma_extra_fields,
            am_db="lemma_evaluation_lemma_extra_fields.db",
        ),
        [1715776939301, 1718190526053, 1717943898444],
        marks=pytest.mark.spacy,
        id="skip_inflections",
    ),
    ################################################################
    #               CASE: DON'T SKIP INFLECTIONS
    ################################################################
    # Config contains "inflection evaluation", i.e. we DON'T want to
    # skip any subsequent cards that have the same lemmas as those
    # studied before
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            initial_col="lemma_evaluation_lemma_extra_fields_collection",
            config=config_inflection_evaluation,
            am_db="lemma_evaluation_lemma_extra_fields.db",
        ),
        [1715776939301, 1715776946917, 1715776953867],
        marks=pytest.mark.spacy,
        id="dont_skip_inflections",
    ),
]


@pytest.mark.parametrize(
    "fake_environment_fixture, expected_results",
    test_cases_morph_infection,
    indirect=["fake_environment_fixture"],
)
def test_custom_review(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    expected_results: list[int],
    mocked_reviewer_and_db: tuple[Mock, AnkiMorphsDB],
) -> None:
    mock_mw, mock_db = mocked_reviewer_and_db
    am_config = AnkiMorphsConfig()

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


test_cases_morph_status = [
    ################################################################
    #               CASE: SKIP ONLY KNOWN OR FRESH
    ################################################################
    # Test if cards with only known or fresh morphs are skipped,
    # which is the default settings
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            initial_col="card_handling_collection",
            config=config_lemma_evaluation_lemma_extra_fields,
            am_db="card_handling_collection.db",
        ),
        [1736763249205],
        marks=pytest.mark.spacy,
        id="skip_known_and_fresh",
    ),
    ################################################################
    #               CASE: DISABLE SKIP NO UNKNOWN MORPHS
    ################################################################
    # Test if cards are skipped when we disable:
    #   "ConfigKeys.SKIP_ONLY_KNOWN_MORPHS_CARDS"
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            initial_col="card_handling_collection",
            config=copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
            | {
                RawConfigKeys.SKIP_NO_UNKNOWN_MORPHS: False,
            },
            am_db="card_handling_collection.db",
        ),
        [1736763242955, 1736763365474, 1736763249205],
        marks=pytest.mark.spacy,
        id="dont_skip_known",
    ),
    ################################################################
    #               CASE: DON'T SKIP FRESH MORPHS
    ################################################################
    # Test if cards with fresh morphs are skipped if we activate
    # "ConfigKeys.SKIP_DONT_WHEN_CONTAINS_FRESH_MORPHS"
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            initial_col="card_handling_collection",
            config=copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
            | {
                RawConfigKeys.SKIP_DONT_WHEN_CONTAINS_FRESH_MORPHS: True,
                RawConfigKeys.SKIP_WHEN_ALL_FRESH_MORPHS_SEEN_TODAY: False,
                RawConfigKeys.SKIP_WHEN_CONTAINS_FRESH_MORPHS: False,
            },
            am_db="card_handling_collection.db",
        ),
        [1736763242955, 1736763249205],
        marks=pytest.mark.spacy,
        id="dont_skip_known_or_fresh",
    ),
    ###############################################################
    #               CASE: SKIP FRESH MORPHS SEEN TODAY
    ################################################################
    # Test if cards with fresh morphs are skipped already seen today
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            initial_col="fresh_skip_collection",
            config=copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
            | {
                RawConfigKeys.SKIP_DONT_WHEN_CONTAINS_FRESH_MORPHS: False,
                RawConfigKeys.SKIP_WHEN_ALL_FRESH_MORPHS_SEEN_TODAY: True,
                RawConfigKeys.SKIP_WHEN_CONTAINS_FRESH_MORPHS: False,
            },
            am_db="fresh_skip_collection.db",
        ),
        [1784810971407, 1784810794920],
        marks=pytest.mark.spacy,
        id="skip_when_fresh_already_seen_today",
    ),
    ###############################################################
    #               CASE: DON'T SKIP FRESH MORPHS V2
    ################################################################
    # Test if cards with fresh morphs are NOT skipped
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            initial_col="fresh_skip_collection",
            config=copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
            | {
                RawConfigKeys.SKIP_DONT_WHEN_CONTAINS_FRESH_MORPHS: True,
                RawConfigKeys.SKIP_WHEN_ALL_FRESH_MORPHS_SEEN_TODAY: False,
                RawConfigKeys.SKIP_WHEN_CONTAINS_FRESH_MORPHS: False,
            },
            am_db="fresh_skip_collection.db",
        ),
        [1784810971407, 1784812132312],
        marks=pytest.mark.spacy,
        id="dont_skip_fresh_morphs_v2",
    ),
    ###############################################################
    #               CASE: SKIP FRESH MORPHS V2
    ################################################################
    # Test if cards with fresh morphs are skipped
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            initial_col="fresh_skip_collection",
            config=copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
            | {
                RawConfigKeys.SKIP_DONT_WHEN_CONTAINS_FRESH_MORPHS: False,
                RawConfigKeys.SKIP_WHEN_ALL_FRESH_MORPHS_SEEN_TODAY: False,
                RawConfigKeys.SKIP_WHEN_CONTAINS_FRESH_MORPHS: True,
            },
            am_db="fresh_skip_collection.db",
        ),
        [1784810794920],
        marks=pytest.mark.spacy,
        id="skip_fresh_morphs_v2",
    ),
]


@pytest.mark.parametrize(
    "fake_environment_fixture, expected_results",
    test_cases_morph_status,
    indirect=["fake_environment_fixture"],
)
def test_morph_status_skip(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    expected_results: list[int],
    mocked_reviewer_and_db: tuple[Mock, AnkiMorphsDB],
) -> None:
    mock_mw, _ = mocked_reviewer_and_db

    # print("fake env config")
    # pprint.pprint(fake_environment_fixture.config)

    for expected_card_id in expected_results:
        mock_mw.reviewer.nextCard()
        actual_card_id = mock_mw.reviewer.card.id
        assert (
            actual_card_id == expected_card_id
        ), f"Expected card {expected_card_id}, got {actual_card_id}"

        # Press 'good'
        mock_mw.col.sched.answerCard(mock_mw.reviewer.card, ease=3)
        insert_seen_morphs(mock_mw.reviewer, mock_mw.reviewer.card, 3)
