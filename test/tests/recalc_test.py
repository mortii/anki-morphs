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
    config_lemma_evaluation_lemma_extra_fields,
    config_max_morph_priority,
    config_offset_inflection_enabled,
    config_offset_lemma_enabled,
    config_suspend_known,
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
from anki.cards import Card  # isort:skip  pylint:disable=wrong-import-order
from anki.models import (  # isort:skip pylint:disable=wrong-import-order
    ModelManager,
    NotetypeDict,
)
from anki.notes import Note  # isort:skip  pylint:disable=wrong-import-order


################################################################
#             CASE: SAME INFLECTION AND LEMMA SCORES
################################################################
# Config contains "lemma priority", therefore we check that all
# the inflections are given the same score as their respective
# lemmas.
# Database choice is arbitrary.
################################################################
case_same_lemma_and_inflection_scores_params = FakeEnvironmentParams(
    actual_col="lemma_evaluation_lemma_extra_fields_collection",
    expected_col="lemma_evaluation_lemma_extra_fields_collection",
    config=config_lemma_evaluation_lemma_extra_fields,
)


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
case_inflections_are_known_params = FakeEnvironmentParams(
    actual_col="some_studied_lemmas_collection",
    expected_col="some_studied_lemmas_collection",
    config=config_lemma_evaluation_lemma_extra_fields,
)

################################################################
#               CASE: OFFSET NEW CARDS INFLECTIONS
################################################################
# Config contains ["recalc_offset_new_cards"] = True, checks
# if new cards that are not the first in the queue with that
# particular unknown morph is offset, i.e. moved back in
# the queue.
################################################################
case_offset_new_cards_inflection_params = FakeEnvironmentParams(
    actual_col="offset_new_cards_inflection_collection",
    expected_col="offset_new_cards_inflection_collection",
    config=config_offset_inflection_enabled,
)

################################################################
#               CASE: OFFSET NEW CARDS LEMMAS
################################################################
# Same as `CASE: OFFSET NEW CARDS INFLECTIONS` but evaluates
# morphs by lemmas instead, and has the `lemma_priority_collection`
# as the basis.
################################################################
case_offset_new_cards_lemma_params = FakeEnvironmentParams(
    actual_col="offset_new_cards_lemma_collection",
    expected_col="offset_new_cards_lemma_collection",
    config=config_offset_lemma_enabled,
)

################################################################
#               CASE: KNOWN MORPHS ENABLED
################################################################
# Config contains "read_known_morphs_folder": true,
################################################################
case_known_morphs_enabled_params = FakeEnvironmentParams(
    actual_col="known_morphs_collection",
    expected_col="known_morphs_collection",
    config=config_known_morphs_enabled,
)

################################################################
#               CASE: KNOWN MORPHS ENABLED
################################################################
# Config contains "preprocess_ignore_names_textfile": true,
################################################################
case_ignore_names_txt_enabled_params = FakeEnvironmentParams(
    actual_col="ignore_names_txt_collection",
    expected_col="ignore_names_txt_collection",
    config=config_ignore_names_txt_enabled,
)

################################################################
#               CASE: BIG JAPANESE COLLECTION
################################################################
# Monolithic collection, used for catching weird and unexpected
# edge cases.
################################################################
case_big_japanese_collection_params = FakeEnvironmentParams(
    actual_col="big_japanese_collection",
    expected_col="big_japanese_collection",
    config=config_big_japanese_collection,
)

################################################################
#               CASE: MAX MORPH PRIORITY
################################################################
# This collection uses the `ja_core_news_sm_freq_inflection_min_occurrence.csv`
# priority file, and checks if morphs not contained in that file
# are given the max morph priority.
################################################################
case_max_morph_priority_params = FakeEnvironmentParams(
    actual_col="max_morph_priority_collection",
    expected_col="max_morph_priority_collection",
    config=config_max_morph_priority,
)

################################################################
#                   CASE: SUSPEND KNOWN
################################################################
# Config contains [ConfigKeys.RECALC_SUSPEND_KNOWN_NEW_CARDS] = True
################################################################
config_suspend_known_params = FakeEnvironmentParams(
    actual_col="suspend_pre_col",
    expected_col="suspend_post_col",
    config=config_suspend_known,
)


# "Using the indirect=True parameter when parametrizing a test allows to parametrize a
# test with a fixture receiving the values before passing them to a test"
# - https://docs.pytest.org/en/7.1.x/example/parametrize.html#indirect-parametrization
# This means that we run the fixture AND the test function for each parameter.
@pytest.mark.external_morphemizers
@pytest.mark.parametrize(
    "fake_environment_fixture",
    [
        case_same_lemma_and_inflection_scores_params,
        case_inflections_are_known_params,
        case_offset_new_cards_inflection_params,
        case_offset_new_cards_lemma_params,
        case_known_morphs_enabled_params,
        case_ignore_names_txt_enabled_params,
        case_big_japanese_collection_params,
        case_max_morph_priority_params,
        config_suspend_known_params,
    ],
    indirect=True,
)
def test_recalc(  # pylint:disable=too-many-locals
    fake_environment_fixture: FakeEnvironment | None,
) -> None:
    if fake_environment_fixture is None:
        pytest.xfail()

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

        actual_card: Card = actual_collection.get_card(card_id)
        actual_note: Note = actual_card.note()

        expected_card: Card = expected_collection.get_card(card_id)
        expected_note: Note = expected_card.note()

        # for field, pos in field_positions.items():
        #     print()
        #     print(f"field: {field}")
        #     print(f"actual_note: {actual_note.fields[pos]}")
        #     print(f"expected_note: {expected_note.fields[pos]}")
        #
        # print(f"actual_card.due: {actual_card.due}")
        # print(f"expected_card.due: {expected_card.due}")
        #
        # print(f"actual_note.tags: {actual_note.tags}")
        # print(f"expected_note.tags: {expected_note.tags}")

        assert card_id == actual_card.id
        assert actual_card.due == expected_card.due
        assert actual_note.tags == expected_note.tags

        for pos in field_positions.values():
            # note.fields[pos]: the content of the field
            assert actual_note.fields[pos] == expected_note.fields[pos]


################################################################
#                  CASE: WRONG NOTE TYPE
################################################################
# Checks if "AnkiNoteTypeNotFound" exception is raised correctly
# when we supply an invalid note type in the config.
# Collection choice is arbitrary.
# Database choice is arbitrary.
################################################################
case_wrong_note_type_params = FakeEnvironmentParams(
    config=config_wrong_note_type,
)


################################################################
#                  CASE: WRONG FIELD NAME
################################################################
# Checks if "AnkiFieldNotFound" exception is raised correctly
# when we supply an invalid field name in the config.
# Collection choice is arbitrary.
# Database choice is arbitrary.
################################################################
case_wrong_field_name_params = FakeEnvironmentParams(
    config=config_wrong_field_name,
)


################################################################
#                CASE: WRONG MORPH PRIORITY
################################################################
# Checks if "PriorityFileNotFoundException" exception is raised
# correctly when we supply an invalid priority file in the config.
# Collection choice is arbitrary.
# Database choice is arbitrary.
################################################################
case_wrong_morph_priority_params = FakeEnvironmentParams(
    config=config_wrong_morph_priority,
)


################################################################
#            CASE: WRONG MORPHEMIZER DESCRIPTION
################################################################
# Checks if "MorphemizerNotFoundException" exception is raised
# correctly when we supply an invalid morphemizer description
# in the config.
# Collection choice is arbitrary.
# Database choice is arbitrary.
################################################################
case_wrong_morphemizer_description_params = FakeEnvironmentParams(
    config=config_wrong_morphemizer_description,
)


################################################################
#            CASES: DEFAULT NOTE FILTER SETTINGS
################################################################
# Checks if "DefaultSettingsException" exception is raised
# when any note filters contain the default `(none)` selection.
# Collection choice is arbitrary.
# Database choice is arbitrary.
################################################################
case_default_note_type_params = FakeEnvironmentParams(
    config=config_default_note_type,
)

case_default_field_params = FakeEnvironmentParams(
    config=config_default_field,
)

case_default_morph_priority_params = FakeEnvironmentParams(
    config=config_default_morph_priority,
)

case_default_morphemizer_params = FakeEnvironmentParams(
    config=config_default_morphemizer,
)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment_fixture, expected_exception",
    [
        (case_default_note_type_params, DefaultSettingsException),
        (case_default_field_params, DefaultSettingsException),
        (case_default_morph_priority_params, DefaultSettingsException),
        (case_default_morphemizer_params, DefaultSettingsException),
        (case_wrong_morphemizer_description_params, MorphemizerNotFoundException),
        (case_wrong_morph_priority_params, PriorityFileNotFoundException),
        (case_wrong_field_name_params, AnkiFieldNotFound),
        (case_wrong_note_type_params, AnkiNoteTypeNotFound),
    ],
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


################################################################
#        CASES: INVALID/MALFORMED KNOWN MORPHS FILE
################################################################
# Checks if "KnownMorphsFileMalformedException" exception is raised
# when a file is malformed.
# Collection choice is arbitrary.
# Database choice is arbitrary.
################################################################
case_invalid_known_morphs_file_params = FakeEnvironmentParams(
    config=config_known_morphs_enabled,
    known_morphs_dir="known-morphs-invalid",
)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment_fixture",
    [case_invalid_known_morphs_file_params],
    indirect=["fake_environment_fixture"],
)
def test_recalc_with_invalid_known_morphs_file(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
) -> None:
    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()

    try:
        recalc_main._recalc_background_op(
            read_enabled_config_filters=read_enabled_config_filters,
            modify_enabled_config_filters=modify_enabled_config_filters,
        )
    except KnownMorphsFileMalformedException:
        pass
    else:
        assert False
