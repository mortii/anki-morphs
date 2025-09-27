from __future__ import annotations

from collections.abc import Sequence
from test.fake_configs import (
    config_big_japanese_collection,
    config_default_field,
    config_default_morph_priority,
    config_default_morphemizer,
    config_default_note_type,
    config_ignore_names_txt_enabled,
    config_known_morphs_enabled,
    config_use_stability_for_known_threshold,
    config_lemma_evaluation_lemma_extra_fields,
    config_max_morph_priority,
    config_move_to_end_morphs_known,
    config_move_to_end_morphs_known_or_fresh,
    config_offset_inflection_enabled,
    config_offset_lemma_enabled,
    config_suspend_morphs_known,
    config_suspend_morphs_known_or_fresh,
    config_wrong_field_name,
    config_wrong_morph_priority,
    config_wrong_morphemizer_description,
    config_wrong_note_type,
)
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)

import pytest

from ankimorphs import ankimorphs_config
from ankimorphs import ankimorphs_globals as am_globals
from ankimorphs import text_preprocessing
from ankimorphs.ankimorphs_config import RawConfigFilterKeys
from ankimorphs.exceptions import (
    AnkiFieldNotFound,
    AnkiNoteTypeNotFound,
    DefaultSettingsException,
    KnownMorphsFileMalformedException,
    MorphemizerNotFoundException,
    PriorityFileNotFoundException,
)
from ankimorphs.recalc import recalc_main

# these have to be placed here to avoid cyclical imports
from anki.cards import Card, CardId  # isort:skip  pylint:disable=wrong-import-order
from anki.models import (  # isort:skip pylint:disable=wrong-import-order
    ModelManager,
    NotetypeDict,
)
from anki.notes import Note  # isort:skip  pylint:disable=wrong-import-order


test_cases_with_success = [
    ################################################################
    #             CASE: SAME INFLECTION AND LEMMA SCORES
    ################################################################
    # Config contains "lemma priority", therefore we check that all
    # the inflections are given the same score as their respective
    # lemmas.
    # Database choice is arbitrary.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="lemma_evaluation_lemma_extra_fields_collection",
            expected_col="lemma_evaluation_lemma_extra_fields_collection",
            config=config_lemma_evaluation_lemma_extra_fields,
        ),
        id="same_lemma_and_inflection_scores",
    ),
    ################################################################
    #                 CASE: INFLECTIONS ARE KNOWN
    ################################################################
    # Same as case 1, but at least one card of each lemma has been
    # studied. This checks the following:
    # 1. all inflections are set to "known"
    # 2. the 'am-fresh-morphs' tag are set
    # 3. the 'am-study-morph' field has a value
    # Database choice is arbitrary.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="some_studied_lemmas_collection",
            expected_col="some_studied_lemmas_collection",
            config=config_lemma_evaluation_lemma_extra_fields,
        ),
        id="inflections_are_known",
    ),
    ################################################################
    #               CASE: OFFSET NEW CARDS INFLECTIONS
    ################################################################
    # Config contains ["recalc_offset_new_cards"] = True, checks
    # if new cards that are not the first in the queue with that
    # particular unknown morph is offset, i.e. moved back in
    # the queue.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="offset_new_cards_inflection_collection",
            expected_col="offset_new_cards_inflection_collection",
            config=config_offset_inflection_enabled,
        ),
        id="offset_new_cards_inflection",
    ),
    ################################################################
    #               CASE: OFFSET NEW CARDS LEMMAS
    ################################################################
    # Same as `CASE: OFFSET NEW CARDS INFLECTIONS` but evaluates
    # morphs by lemmas instead, and has the `lemma_priority_collection`
    # as the basis.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="offset_new_cards_lemma_collection",
            expected_col="offset_new_cards_lemma_collection",
            config=config_offset_lemma_enabled,
        ),
        id="offset_new_cards_lemma",
    ),
    ################################################################
    #               CASE: KNOWN MORPHS ENABLED
    ################################################################
    # Config contains "read_known_morphs_folder": true,
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="known_morphs_collection",
            expected_col="known_morphs_collection",
            config=config_known_morphs_enabled,
        ),
        id="known_morphs_enabled",
    ),
    ################################################################
    #               CASE: USE_STABILITY_FOR_KNOWN_THRESHOLD ENABLED
    ################################################################
    # Config contains "use_stability_for_known_threshold": true,
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="stability_post_treatment",
            expected_col="stability_post_treatment",
            config=config_use_stability_for_known_threshold
        ),
        id="use_stability_for_known_threshold",
    ),
    ################################################################
    #               CASE: IGNORE NAMES ENABLED
    ################################################################
    # Config contains "preprocess_ignore_names_textfile": true,
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="ignore_names_txt_collection",
            expected_col="ignore_names_txt_collection",
            config=config_ignore_names_txt_enabled,
        ),
        id="ignore_names_txt_enabled",
    ),
    ################################################################
    #               CASE: BIG JAPANESE COLLECTION
    ################################################################
    # Monolithic collection, used for catching weird and unexpected
    # edge cases.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="big_japanese_collection",
            expected_col="big_japanese_collection",
            config=config_big_japanese_collection,
        ),
        id="big_japanese_collection",
    ),
    ################################################################
    #               CASE: MAX MORPH PRIORITY
    ################################################################
    # This collection uses the `ja_core_news_sm_freq_inflection_min_occurrence.csv`
    # priority file, and checks if morphs not contained in that file
    # are given the max morph priority.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="max_morph_priority_collection",
            expected_col="max_morph_priority_collection",
            config=config_max_morph_priority,
        ),
        id="max_morph_priority",
    ),
    ################################################################
    #               CASE: SUSPEND ALL MORPHS KNOWN
    ################################################################
    # Checks if cards are correctly suspended if all their morphs
    # are known, except if they also have fresh morphs
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="card_handling_collection",
            expected_col="suspend_all_morphs_known",
            config=config_suspend_morphs_known,
        ),
        id="suspend_all_morphs_known",
    ),
    ################################################################
    #              CASE: SUSPEND ALL MORPHS KNOWN OR FRESH
    ################################################################
    # Checks if cards are correctly suspended if all their morphs
    # are known or fresh
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="card_handling_collection",
            expected_col="suspend_morphs_known_or_fresh",
            config=config_suspend_morphs_known_or_fresh,
        ),
        id="suspend_all_morphs_known_or_fresh",
    ),
    ################################################################
    #                CASE: MOVE TO END MORPHS KNOWN
    ################################################################
    # Checks if cards are correctly moved to the end of the due
    # queue if all their morphs are known, except if they have fresh
    # morphs
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="card_handling_collection",
            expected_col="move_to_end_morphs_known",
            config=config_move_to_end_morphs_known,
        ),
        id="move_to_end_morphs_known",
    ),
    ################################################################
    #          CASE: MOVE TO END MORPHS KNOWN OR FRESH
    ################################################################
    # Checks if cards are correctly moved to the end of the due
    # queue if all their morphs are known and/or fresh
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            actual_col="card_handling_collection",
            expected_col="move_to_end_morphs_known_or_fresh",
            config=config_move_to_end_morphs_known_or_fresh,
        ),
        id="move_to_end_morphs_known_or_fresh",
    ),
]


# "Using the indirect=True parameter when parametrizing a test allows to parametrize a
# test with a fixture receiving the values before passing them to a test"
# - https://docs.pytest.org/en/7.1.x/example/parametrize.html#indirect-parametrization
# This means that we run the fixture AND the test function for each parameter.
@pytest.mark.external_morphemizers
@pytest.mark.parametrize(
    "fake_environment_fixture",
    test_cases_with_success,
    indirect=True,
)
def test_recalc(  # pylint:disable=too-many-locals
    fake_environment_fixture: FakeEnvironment | None,
) -> None:
    if fake_environment_fixture is None:
        pytest.xfail()

    text_preprocessing.update_translation_table()  # updates custom characters to ignore

    actual_collection = fake_environment_fixture.mock_mw.col
    expected_collection = fake_environment_fixture.expected_collection

    model_manager: ModelManager = ModelManager(actual_collection)
    note_type_dict: NotetypeDict | None = model_manager.by_name(
        fake_environment_fixture.config["filters"][0]["note_type"]
    )
    assert note_type_dict is not None
    field_name_dict = model_manager.field_map(note_type_dict)

    field_indices = {
        RawConfigFilterKeys.EXTRA_ALL_MORPHS: am_globals.EXTRA_FIELD_ALL_MORPHS,
        RawConfigFilterKeys.EXTRA_ALL_MORPHS_COUNT: am_globals.EXTRA_FIELD_ALL_MORPHS_COUNT,
        RawConfigFilterKeys.EXTRA_UNKNOWN_MORPHS: am_globals.EXTRA_FIELD_UNKNOWN_MORPHS,
        RawConfigFilterKeys.EXTRA_UNKNOWN_MORPHS_COUNT: am_globals.EXTRA_FIELD_UNKNOWN_MORPHS_COUNT,
        RawConfigFilterKeys.EXTRA_HIGHLIGHTED: am_globals.EXTRA_FIELD_HIGHLIGHTED,
        RawConfigFilterKeys.EXTRA_SCORE: am_globals.EXTRA_FIELD_SCORE,
        RawConfigFilterKeys.EXTRA_SCORE_TERMS: am_globals.EXTRA_FIELD_SCORE_TERMS,
        RawConfigFilterKeys.EXTRA_STUDY_MORPHS: am_globals.EXTRA_FIELD_STUDY_MORPHS,
    }
    field_positions = {
        key: field_name_dict[value][0] for key, value in field_indices.items()
    }

    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()

    recalc_main._recalc_background_op(
        read_enabled_config_filters=read_enabled_config_filters,
        modify_enabled_config_filters=modify_enabled_config_filters,
    )

    # print("config:")
    # pprint(fake_environment_fixture.config)
    # print()

    expected_collection_cards: Sequence[int] = expected_collection.find_cards("")
    actual_collection_cards: Sequence[int] = actual_collection.find_cards("")
    assert len(expected_collection_cards) > 0
    assert len(expected_collection_cards) == len(actual_collection_cards)

    for card_id in expected_collection_cards:
        # print(f"card_id: {card_id}")
        card_id = CardId(card_id)

        actual_card: Card = actual_collection.get_card(card_id)
        actual_note: Note = actual_card.note()

        expected_card: Card = expected_collection.get_card(card_id)
        expected_note: Note = expected_card.note()

        # for field, pos in field_positions.items():
        #     print()
        #     print(f"field: {field}")
        #     print(f"actual_note: {actual_note.fields[pos]}")
        #     print(f"expected_note: {expected_note.fields[pos]}")

        # print(f"actual_card.due: {actual_card.due}")
        # print(f"expected_card.due: {expected_card.due}")
        # print(f"actual_note.tags: {actual_note.tags}")
        # print(f"expected_note.tags: {expected_note.tags}")

        assert card_id == actual_card.id
        assert actual_card.due == expected_card.due
        assert actual_note.tags == expected_note.tags

        for pos in field_positions.values():
            # note.fields[pos]: the content of the field
            assert actual_note.fields[pos] == expected_note.fields[pos]


test_cases_with_immediate_exceptions = [
    ################################################################
    #                  CASE: WRONG NOTE TYPE
    ################################################################
    # Checks if "AnkiNoteTypeNotFound" exception is raised correctly
    # when we supply an invalid note type in the config.
    # Collection choice is arbitrary.
    # Database choice is arbitrary.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            config=config_wrong_note_type,
        ),
        AnkiNoteTypeNotFound,
        id="wrong_note_type",
    ),
    ################################################################
    #                  CASE: WRONG FIELD NAME
    ################################################################
    # Checks if "AnkiFieldNotFound" exception is raised correctly
    # when we supply an invalid field name in the config.
    # Collection choice is arbitrary.
    # Database choice is arbitrary.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            config=config_wrong_field_name,
        ),
        AnkiFieldNotFound,
        id="wrong_field_name",
    ),
    ################################################################
    #                CASE: WRONG MORPH PRIORITY
    ################################################################
    # Checks if "PriorityFileNotFoundException" exception is raised
    # correctly when we supply an invalid priority file in the config.
    # Collection choice is arbitrary.
    # Database choice is arbitrary.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            config=config_wrong_morph_priority,
        ),
        PriorityFileNotFoundException,
        id="wrong_morph_priority",
    ),
    ################################################################
    #            CASE: WRONG MORPHEMIZER DESCRIPTION
    ################################################################
    # Checks if "MorphemizerNotFoundException" exception is raised
    # correctly when we supply an invalid morphemizer description
    # in the config.
    # Collection choice is arbitrary.
    # Database choice is arbitrary.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            config=config_wrong_morphemizer_description,
        ),
        MorphemizerNotFoundException,
        id="wrong_morphemizer_description",
    ),
    ################################################################
    #            CASES: DEFAULT NOTE FILTER SETTINGS
    ################################################################
    # Checks if "DefaultSettingsException" exception is raised
    # when any note filters contain the default `(none)` selection.
    # Collection choice is arbitrary.
    # Database choice is arbitrary.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            config=config_default_note_type,
        ),
        DefaultSettingsException,
        id="default_note_type",
    ),
    pytest.param(
        FakeEnvironmentParams(
            config=config_default_field,
        ),
        DefaultSettingsException,
        id="default_field",
    ),
    pytest.param(
        FakeEnvironmentParams(
            config=config_default_morph_priority,
        ),
        DefaultSettingsException,
        id="default_morph_priority",
    ),
    pytest.param(
        FakeEnvironmentParams(
            config=config_default_morphemizer,
        ),
        DefaultSettingsException,
        id="default_morphemizer",
    ),
]


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment_fixture, expected_exception",
    test_cases_with_immediate_exceptions,
    indirect=["fake_environment_fixture"],
)
def test_recalc_with_default_settings(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment, expected_exception: type[Exception]
) -> None:
    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()

    settings_error: Exception | None = recalc_main._check_selected_settings_for_errors(
        read_enabled_config_filters, modify_enabled_config_filters
    )
    assert isinstance(settings_error, expected_exception)


test_cases_with_delayed_exceptions = [
    ################################################################
    #        CASES: INVALID/MALFORMED KNOWN MORPHS FILE
    ################################################################
    # Checks if "KnownMorphsFileMalformedException" exception is raised
    # when a file is malformed.
    # Collection choice is arbitrary.
    # Database choice is arbitrary.
    ################################################################
    pytest.param(
        FakeEnvironmentParams(
            config=config_known_morphs_enabled,
            known_morphs_dir="known-morphs-invalid",
        ),
        KnownMorphsFileMalformedException,
        id="invalid_known_morphs_file",
    ),
]


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment_fixture, expected_exception",
    test_cases_with_delayed_exceptions,
    indirect=["fake_environment_fixture"],
)
def test_recalc_with_invalid_known_morphs_file(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment, expected_exception: type[Exception]
) -> None:
    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()

    with pytest.raises(expected_exception):
        recalc_main._recalc_background_op(
            read_enabled_config_filters=read_enabled_config_filters,
            modify_enabled_config_filters=modify_enabled_config_filters,
        )
