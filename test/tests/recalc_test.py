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
    config_offset_inflection_enabled,
    config_offset_lemma_enabled,
    config_wrong_field_name,
    config_wrong_morph_priority,
    config_wrong_morphemizer_description,
    config_wrong_note_type,
)
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment,
)

import pytest

from ankimorphs import ankimorphs_config
from ankimorphs import ankimorphs_globals as am_globals
from ankimorphs.ankimorphs_config import RawConfigFilterKeys
from ankimorphs.exceptions import (
    AnkiFieldNotFound,
    AnkiNoteTypeNotFound,
    DefaultSettingsException,
    FrequencyFileNotFoundException,
    KnownMorphsFileMalformedException,
    MorphemizerNotFoundException,
)
from ankimorphs.recalc import recalc_main

# these have to be placed here to avoid cyclical imports
from anki.cards import Card  # isort:skip  pylint:disable=wrong-import-order
from anki.models import (  # isort:skip pylint:disable=wrong-import-order
    ModelManager,
    NotetypeDict,
)
from anki.notes import Note  # isort:skip  pylint:disable=wrong-import-order
from test.card_data import CardData  # isort:skip  pylint:disable=wrong-import-order


################################################################
#             CASE: SAME INFLECTION AND LEMMA SCORES
################################################################
# Config contains "lemma priority", therefore we check that all
# the inflections are given the same score as their respective
# lemmas.
# Database choice is arbitrary.
################################################################
case_same_lemma_and_inflection_scores_params = FakeEnvironmentParams(
    collection="lemma_evaluation_lemma_extra_fields_collection",
    config=config_lemma_evaluation_lemma_extra_fields,
)


################################################################
#                 CASE: INFLECTIONS ARE KNOWN
################################################################
# Same as case 1, but at least one card of each lemma has been
# studied. This checks the following:
# 1. all inflections are set to "known"
# 2. the 'am-fresh-morphs' tag are set
# 3. the 'am-study-morph' field has a value while
# Since one card has recently been studied, it will also
# serve as a test for the .
# Database choice is arbitrary.
################################################################
case_inflections_are_known_params = FakeEnvironmentParams(
    collection="some_studied_lemmas_collection",
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
    collection="offset_new_cards_inflection_collection",
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
    collection="offset_new_cards_lemma_collection",
    config=config_offset_lemma_enabled,
)

################################################################
#               CASE: KNOWN MORPHS ENABLED
################################################################
# Config contains "read_known_morphs_folder": true,
################################################################
case_known_morphs_enabled_params = FakeEnvironmentParams(
    collection="known_morphs_collection",
    config=config_known_morphs_enabled,
)

################################################################
#               CASE: KNOWN MORPHS ENABLED
################################################################
# Config contains "preprocess_ignore_names_textfile": true,
################################################################
case_ignore_names_txt_enabled_params = FakeEnvironmentParams(
    collection="ignore_names_txt_collection",
    config=config_ignore_names_txt_enabled,
)

################################################################
#               CASE: BIG JAPANESE COLLECTION
################################################################
# Monolithic collection, used for catching weird and unexpected
# edge cases.
################################################################
case_big_japanese_collection_params = FakeEnvironmentParams(
    collection="big_japanese_collection",
    config=config_big_japanese_collection,
)


# "Using the indirect=True parameter when parametrizing a test allows to parametrize a
# test with a fixture receiving the values before passing them to a test"
# - https://docs.pytest.org/en/7.1.x/example/parametrize.html#indirect-parametrization
# This means that we run the fixture AND the test function for each parameter.
@pytest.mark.external_morphemizers
@pytest.mark.parametrize(
    "fake_environment",
    [
        case_same_lemma_and_inflection_scores_params,
        case_inflections_are_known_params,
        case_offset_new_cards_inflection_params,
        case_offset_new_cards_lemma_params,
        case_known_morphs_enabled_params,
        case_ignore_names_txt_enabled_params,
        case_big_japanese_collection_params,
    ],
    indirect=True,
)
def test_recalc(  # pylint:disable=too-many-locals
    fake_environment: FakeEnvironment,
) -> None:
    modified_collection = fake_environment.modified_collection
    original_collection = fake_environment.original_collection

    model_manager: ModelManager = ModelManager(modified_collection)
    note_type_dict: NotetypeDict | None = model_manager.by_name(
        fake_environment.config["filters"][0]["note_type"]
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

    card_due_dict: dict[int, CardData] = {}

    original_collection_cards = original_collection.find_cards("")
    card_collection_length = len(original_collection_cards)
    assert card_collection_length > 0

    card: Card
    note: Note

    for card_id in original_collection_cards:
        card = original_collection.get_card(card_id)
        note = card.note()
        card_due_dict[card_id] = CardData(card, note, field_positions)

    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()

    recalc_main._recalc_background_op(
        read_enabled_config_filters=read_enabled_config_filters,
        modify_enabled_config_filters=modify_enabled_config_filters,
    )

    mock_collection_cards: Sequence[int] = modified_collection.find_cards("")
    assert len(mock_collection_cards) == card_collection_length

    for card_id in mock_collection_cards:
        print(f"card_id: {card_id}")

        card = modified_collection.get_card(card_id)
        note = card.note()

        original_card_data = card_due_dict[card_id]
        new_card_data = CardData(card, note, field_positions)

        assert card_id == card.id
        assert original_card_data == new_card_data


################################################################
#                  CASE: WRONG NOTE TYPE
################################################################
# Checks if "AnkiNoteTypeNotFound" exception is raised correctly
# when we supply an invalid note type in the config.
# Collection choice is arbitrary.
# Database choice is arbitrary.
################################################################
case_wrong_note_type_params = FakeEnvironmentParams(
    collection="ignore_names_txt_collection",
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
    collection="ignore_names_txt_collection",
    config=config_wrong_field_name,
)


################################################################
#                CASE: WRONG MORPH PRIORITY
################################################################
# Checks if "FrequencyFileNotFoundException" exception is raised
# correctly when we supply an invalid frequency file in the config.
# Collection choice is arbitrary.
# Database choice is arbitrary.
################################################################
case_wrong_morph_priority_params = FakeEnvironmentParams(
    collection="ignore_names_txt_collection",
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
    collection="ignore_names_txt_collection",
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
    collection="ignore_names_txt_collection",
    config=config_default_note_type,
)

case_default_field_params = FakeEnvironmentParams(
    collection="ignore_names_txt_collection",
    config=config_default_field,
)

case_default_morph_priority_params = FakeEnvironmentParams(
    collection="ignore_names_txt_collection",
    config=config_default_morph_priority,
)

case_default_morphemizer_params = FakeEnvironmentParams(
    collection="ignore_names_txt_collection",
    config=config_default_morphemizer,
)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment, expected_exception",
    [
        (case_default_note_type_params, DefaultSettingsException),
        (case_default_field_params, DefaultSettingsException),
        (case_default_morph_priority_params, DefaultSettingsException),
        (case_default_morphemizer_params, DefaultSettingsException),
        (case_wrong_morphemizer_description_params, MorphemizerNotFoundException),
        (case_wrong_morph_priority_params, FrequencyFileNotFoundException),
        (case_wrong_field_name_params, AnkiFieldNotFound),
        (case_wrong_note_type_params, AnkiNoteTypeNotFound),
    ],
    indirect=["fake_environment"],
)
def test_recalc_with_default_settings(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment, expected_exception: type[Exception]
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
    collection="ignore_names_txt_collection",
    config=config_known_morphs_enabled,
    known_morphs_dir="known-morphs-invalid",
)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment",
    [case_invalid_known_morphs_file_params],
    indirect=["fake_environment"],
)
def test_recalc_with_invalid_known_morphs_file(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
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
