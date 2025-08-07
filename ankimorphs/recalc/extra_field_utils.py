from __future__ import annotations

from anki.models import FieldDict, ModelManager, NotetypeDict
from anki.notes import Note
from aqt import mw

from .. import ankimorphs_config
from .. import ankimorphs_globals as am_globals
from ..ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from ..highlighting.text_highlighter import TextHighlighter
from ..morpheme import Morpheme


def new_extra_fields_are_selected() -> bool:
    assert mw is not None

    model_manager: ModelManager = mw.col.models
    modify_enabled_config_filters: list[AnkiMorphsConfigFilter] = (
        ankimorphs_config.get_modify_enabled_filters()
    )

    for config_filter in modify_enabled_config_filters:
        note_type_dict: NotetypeDict | None = mw.col.models.by_name(
            config_filter.note_type
        )
        assert note_type_dict is not None

        existing_field_names = model_manager.field_names(note_type_dict)
        extra_fields_states = _get_states_of_extra_fields(config_filter)

        if any(
            field
            for enabled, field in extra_fields_states
            if enabled and field not in existing_field_names
        ):
            return True

    return False


def _get_states_of_extra_fields(
    config_filter: AnkiMorphsConfigFilter,
) -> list[tuple[bool, str]]:
    # fmt: off
    return [
        (config_filter.extra_all_morphs, am_globals.EXTRA_FIELD_ALL_MORPHS),
        (config_filter.extra_all_morphs_count, am_globals.EXTRA_FIELD_ALL_MORPHS_COUNT),
        (config_filter.extra_unknown_morphs, am_globals.EXTRA_FIELD_UNKNOWN_MORPHS),
        (config_filter.extra_unknown_morphs_count, am_globals.EXTRA_FIELD_UNKNOWN_MORPHS_COUNT),
        (config_filter.extra_highlighted, am_globals.EXTRA_FIELD_HIGHLIGHTED),
        (config_filter.extra_score, am_globals.EXTRA_FIELD_SCORE),
        (config_filter.extra_score_terms, am_globals.EXTRA_FIELD_SCORE_TERMS),
        (config_filter.extra_study_morphs, am_globals.EXTRA_FIELD_STUDY_MORPHS),
    ]
    # fmt: on


def potentially_add_extra_fields_to_note_type(
    model_manager: ModelManager,
    config_filter: AnkiMorphsConfigFilter,
) -> NotetypeDict:
    note_type_dict: NotetypeDict | None = model_manager.by_name(config_filter.note_type)
    assert note_type_dict is not None

    existing_field_names = model_manager.field_names(note_type_dict)
    extra_fields_states = _get_states_of_extra_fields(config_filter)

    for enabled, field in extra_fields_states:
        if enabled and field not in existing_field_names:
            new_field = model_manager.new_field(field)
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)

    # Refresh the note_type_dict to ensure it's updated
    note_type_dict = model_manager.by_name(config_filter.note_type)
    assert note_type_dict is not None
    return note_type_dict


def update_all_morphs_field(
    am_config: AnkiMorphsConfig,
    field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    all_morphs: list[Morpheme],
) -> None:
    all_morphs_string: str = _get_string_of_morphs(am_config, all_morphs)
    index: int = field_name_dict[am_globals.EXTRA_FIELD_ALL_MORPHS][0]
    note.fields[index] = all_morphs_string


def update_all_morphs_count_field(
    field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    all_morphs: list[Morpheme],
) -> None:
    index: int = field_name_dict[am_globals.EXTRA_FIELD_ALL_MORPHS_COUNT][0]
    note.fields[index] = str(len(all_morphs))


def update_unknown_morphs_field(
    am_config: AnkiMorphsConfig,
    field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    unknown_morphs: list[Morpheme],
) -> None:
    unknowns_string: str = _get_string_of_morphs(am_config, unknown_morphs)
    index: int = field_name_dict[am_globals.EXTRA_FIELD_UNKNOWN_MORPHS][0]
    note.fields[index] = unknowns_string


def _get_string_of_morphs(
    am_config: AnkiMorphsConfig,
    morphs: list[Morpheme],
) -> str:
    morphs_string: str

    if am_config.extra_fields_display_inflections:
        morphs_string = "".join(f"{morph.inflection}, " for morph in morphs)
    else:
        morphs_string = "".join(f"{unknown.lemma}, " for unknown in morphs)

    morphs_string = morphs_string[:-2]  # removes last comma and whitespace
    return morphs_string


def update_unknown_morphs_count_field(
    field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    unknown_morphs: list[Morpheme],
) -> None:
    index: int = field_name_dict[am_globals.EXTRA_FIELD_UNKNOWN_MORPHS_COUNT][0]
    note.fields[index] = str(len(unknown_morphs))


def update_score_field(
    field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    score: int,
) -> None:
    index: int = field_name_dict[am_globals.EXTRA_FIELD_SCORE][0]
    note.fields[index] = str(score)


def update_study_morphs_field(
    am_config: AnkiMorphsConfig,
    field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    unknowns: list[Morpheme],
) -> None:
    unknowns_string: str = _get_string_of_morphs(am_config, unknowns)
    index: int = field_name_dict[am_globals.EXTRA_FIELD_STUDY_MORPHS][0]
    note.fields[index] = unknowns_string


def update_score_terms_field(
    field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    score_terms: str,
) -> None:
    index: int = field_name_dict[am_globals.EXTRA_FIELD_SCORE_TERMS][0]
    note.fields[index] = score_terms


def update_highlighted_field(
    am_config: AnkiMorphsConfig,
    config_filter: AnkiMorphsConfigFilter,
    field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    card_morphs: list[Morpheme],
) -> None:
    expression_field_index: int = field_name_dict[config_filter.field][0]
    text_to_highlight = note.fields[expression_field_index]

    highlighted_text = TextHighlighter(
        am_config=am_config, expression=text_to_highlight, morphemes=card_morphs
    ).highlighted()

    extra_field_index: int = field_name_dict[am_globals.EXTRA_FIELD_HIGHLIGHTED][0]
    note.fields[extra_field_index] = highlighted_text
