from __future__ import annotations

import pprint
from collections.abc import Sequence

import pytest

from ankimorphs import ankimorphs_config, ankimorphs_globals, recalc
from ankimorphs.exceptions import (
    AnkiFieldNotFound,
    AnkiNoteTypeNotFound,
    DefaultSettingsException,
    FrequencyFileNotFoundException,
    MorphemizerNotFoundException,
)

from .environment_setup_for_tests import (  # pylint:disable=unused-import
    FakeEnvironment,
    config_big_japanese_collection,
    config_default_field,
    config_default_morph_priority,
    config_default_morphemizer,
    config_default_note_type,
    config_ignore_names_txt_enabled,
    config_known_morphs_enabled,
    config_offset_enabled,
    config_wrong_field_name,
    config_wrong_morph_priority,
    config_wrong_morphemizer_description,
    config_wrong_note_type,
    fake_environment,
)

# these have to be lower than the others to prevent circular imports
from anki.cards import Card  # isort: skip  # pylint:disable=wrong-import-order
from anki.models import (  # isort: skip  # pylint:disable=wrong-import-order
    ModelManager,
    NotetypeDict,
)
from anki.notes import Note  # isort: skip  # pylint:disable=wrong-import-order


class CardData:

    def __init__(  # pylint:disable=too-many-arguments
        self,
        due: int,
        extra_field_unknowns: str,
        extra_field_unknowns_count: str,
        extra_field_highlighted: str,
        extra_field_score: str,
        tags: list[str],
    ):
        self.due = due
        self.extra_field_unknowns = extra_field_unknowns
        self.extra_field_unknowns_count = extra_field_unknowns_count
        self.extra_field_highlighted = extra_field_highlighted
        self.extra_field_score = extra_field_score
        self.tags = tags

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, CardData)
        is_equal = True

        # use "if" for everything to get more feedback
        if self.due != other.due:
            print("Due mismatch!")
            is_equal = False

        if self.extra_field_unknowns != other.extra_field_unknowns:
            print("extra_field_unknowns mismatch!")
            is_equal = False

        if self.extra_field_unknowns_count != other.extra_field_unknowns_count:
            print("extra_field_unknowns_count mismatch!")
            is_equal = False

        if self.extra_field_highlighted != other.extra_field_highlighted:
            print("extra_field_highlighted mismatch!")
            is_equal = False

        if self.extra_field_score != other.extra_field_score:
            print("extra_field_score mismatch!")
            is_equal = False

        if self.tags != other.tags:
            print("tags mismatch!")
            is_equal = False

        if is_equal is False:
            print("self:")
            pprint.pp(vars(self))
            print("other:")
            pprint.pp(vars(other))

        return is_equal


# "Using the indirect=True parameter when parametrizing a test allows to parametrize a test with a fixture
# receiving the values before passing them to a test"
# - https://docs.pytest.org/en/7.1.x/example/parametrize.html#indirect-parametrization
# This means that we run the fixture AND the test function for each parameter.
@pytest.mark.external_morphemizers
@pytest.mark.parametrize(
    "fake_environment",
    [
        ("big-japanese-collection", config_big_japanese_collection),
        ("offset_new_cards_test_collection", config_offset_enabled),
        ("known-morphs-test-collection", config_known_morphs_enabled),
        ("ignore_names_txt_collection", config_ignore_names_txt_enabled),
    ],
    indirect=True,
)
def test_recalc(  # pylint:disable=too-many-locals
    fake_environment: FakeEnvironment,
):
    modified_collection = fake_environment.modified_collection
    original_collection = fake_environment.original_collection

    # pprint.pp(fake_environment.config)

    model_manager: ModelManager = ModelManager(modified_collection)

    note_type_dict: NotetypeDict | None = model_manager.by_name(
        fake_environment.config["filters"][0]["note_type"]
    )

    assert note_type_dict is not None
    note_type_field_name_dict = model_manager.field_map(note_type_dict)

    extra_field_unknowns: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_UNKNOWNS
    ][0]

    extra_field_unknowns_count: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT
    ][0]

    extra_field_highlighted: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
    ][0]

    extra_field_score: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_SCORE
    ][0]

    card_due_dict: dict[int, CardData] = {}

    original_collection_cards = original_collection.find_cards("")
    card_collection_length = len(original_collection_cards)
    assert card_collection_length > 0  # sanity check

    for card_id in original_collection_cards:
        card: Card = original_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        score_field = note.fields[extra_field_score]

        card_due_dict[card_id] = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_score=score_field,
            tags=note.tags,
        )

    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()

    recalc._recalc_background_op(
        read_enabled_config_filters=read_enabled_config_filters,
        modify_enabled_config_filters=modify_enabled_config_filters,
    )

    mock_collection_cards: Sequence[int] = modified_collection.find_cards("")
    assert len(mock_collection_cards) == card_collection_length

    for card_id in mock_collection_cards:
        print(f"card_id: {card_id}")

        card: Card = modified_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        score_field = note.fields[extra_field_score]

        original_card_data = card_due_dict[card_id]
        new_card_data = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_score=score_field,
            tags=note.tags,
        )

        assert card_id == card.id
        assert original_card_data == new_card_data


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment",
    [
        ("ignore_names_txt_collection", config_wrong_note_type),
    ],
    indirect=True,
)
def test_recalc_with_wrong_note_type(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
):
    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()
    settings_error: Exception | None = recalc._check_selected_settings_for_errors(
        read_enabled_config_filters, modify_enabled_config_filters
    )
    assert isinstance(settings_error, AnkiNoteTypeNotFound)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment",
    [
        ("ignore_names_txt_collection", config_wrong_field_name),
    ],
    indirect=True,
)
def test_recalc_with_wrong_field(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
):
    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()
    settings_error: Exception | None = recalc._check_selected_settings_for_errors(
        read_enabled_config_filters, modify_enabled_config_filters
    )
    assert isinstance(settings_error, AnkiFieldNotFound)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment",
    [
        ("ignore_names_txt_collection", config_wrong_morph_priority),
    ],
    indirect=True,
)
def test_recalc_with_wrong_frequency_file(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
):
    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()
    settings_error: Exception | None = recalc._check_selected_settings_for_errors(
        read_enabled_config_filters, modify_enabled_config_filters
    )
    assert isinstance(settings_error, FrequencyFileNotFoundException)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment",
    [
        ("ignore_names_txt_collection", config_wrong_morphemizer_description),
    ],
    indirect=True,
)
def test_recalc_with_wrong_morphemizer(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
):
    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()
    settings_error: Exception | None = recalc._check_selected_settings_for_errors(
        read_enabled_config_filters, modify_enabled_config_filters
    )
    assert isinstance(settings_error, MorphemizerNotFoundException)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment",
    [
        ("ignore_names_txt_collection", config_default_note_type),
        ("ignore_names_txt_collection", config_default_field),
        ("ignore_names_txt_collection", config_default_morph_priority),
        ("ignore_names_txt_collection", config_default_morphemizer),
    ],
    indirect=True,
)
def test_recalc_with_default_settings(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
):
    read_enabled_config_filters = ankimorphs_config.get_read_enabled_filters()
    modify_enabled_config_filters = ankimorphs_config.get_modify_enabled_filters()
    settings_error: Exception | None = recalc._check_selected_settings_for_errors(
        read_enabled_config_filters, modify_enabled_config_filters
    )
    assert isinstance(settings_error, DefaultSettingsException)


@pytest.mark.xfail
def test_recalc_using_spacy_morphemizer():
    # todo: add this at some point
    assert False
