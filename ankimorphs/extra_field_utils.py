from __future__ import annotations

from anki.models import FieldDict, ModelManager, NotetypeDict
from anki.notes import Note
from aqt import mw

from . import ankimorphs_config, ankimorphs_globals, text_highlighting
from .ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from .morpheme import Morpheme


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

        if config_filter.extra_unknowns:
            if ankimorphs_globals.EXTRA_FIELD_UNKNOWNS not in existing_field_names:
                return True

        if config_filter.extra_unknowns_count:
            if (
                ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT
                not in existing_field_names
            ):
                return True

        if config_filter.extra_highlighted:
            if ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED not in existing_field_names:
                return True

        if config_filter.extra_score:
            if ankimorphs_globals.EXTRA_FIELD_SCORE not in existing_field_names:
                return True

    return False


def add_extra_fields_to_note_type(
    config_filter: AnkiMorphsConfigFilter,
    note_type_dict: NotetypeDict,
    model_manager: ModelManager,
) -> bool:
    did_add_fields: bool = False
    existing_field_names = model_manager.field_names(note_type_dict)
    new_field: FieldDict

    if config_filter.extra_unknowns:
        if ankimorphs_globals.EXTRA_FIELD_UNKNOWNS not in existing_field_names:
            new_field = model_manager.new_field(ankimorphs_globals.EXTRA_FIELD_UNKNOWNS)
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)
            did_add_fields = True

    if config_filter.extra_unknowns_count:
        if ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT not in existing_field_names:
            new_field = model_manager.new_field(
                ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT
            )
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)
            did_add_fields = True

    if config_filter.extra_highlighted:
        if ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED not in existing_field_names:
            new_field = model_manager.new_field(
                ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
            )
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)
            did_add_fields = True

    if config_filter.extra_score:
        if ankimorphs_globals.EXTRA_FIELD_SCORE not in existing_field_names:
            new_field = model_manager.new_field(ankimorphs_globals.EXTRA_FIELD_SCORE)
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)
            did_add_fields = True

    return did_add_fields


def update_unknowns_field(
    am_config: AnkiMorphsConfig,
    note_type_field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    unknowns: list[Morpheme],
) -> None:
    focus_morph_string: str

    if am_config.recalc_unknowns_field_shows_inflections:
        focus_morph_string = "".join(f"{unknown.inflection}, " for unknown in unknowns)
    else:
        focus_morph_string = "".join(f"{unknown.lemma}, " for unknown in unknowns)

    focus_morph_string = focus_morph_string[:-2]  # removes last comma and whitespace
    index: int = note_type_field_name_dict[ankimorphs_globals.EXTRA_FIELD_UNKNOWNS][0]
    note.fields[index] = focus_morph_string


def update_unknowns_count_field(
    note_type_field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    unknowns: list[Morpheme],
) -> None:
    index: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT
    ][0]
    note.fields[index] = str(len(unknowns))


def update_score_field(
    note_type_field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    score: int,
) -> None:
    index: int = note_type_field_name_dict[ankimorphs_globals.EXTRA_FIELD_SCORE][0]
    note.fields[index] = str(score)


def update_highlighted_field(  # pylint:disable=too-many-arguments
    am_config: AnkiMorphsConfig,
    config_filter: AnkiMorphsConfigFilter,
    note_type_field_name_dict: dict[str, tuple[int, FieldDict]],
    card_morph_map_cache: dict[int, list[Morpheme]],
    card_id: int,
    note: Note,
) -> None:
    try:
        card_morphs: list[Morpheme] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return

    expression_field_index: int = note_type_field_name_dict[config_filter.field][0]
    text_to_highlight = note.fields[expression_field_index]

    highlighted_text = text_highlighting.get_highlighted_text(
        am_config,
        card_morphs,
        text_to_highlight,
    )

    extra_field_index: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
    ][0]
    note.fields[extra_field_index] = highlighted_text
