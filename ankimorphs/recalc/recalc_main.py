from __future__ import annotations

import time
from pathlib import Path

from anki.cards import Card
from anki.consts import CARD_TYPE_NEW
from anki.models import FieldDict, ModelManager, NotetypeDict
from anki.notes import Note
from aqt import mw
from aqt.operations import QueryOp
from aqt.utils import tooltip

from .. import (
    ankimorphs_config,
    ankimorphs_globals,
    message_box_utils,
    progress_utils,
    tags_and_queue_utils,
)
from ..ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from ..ankimorphs_db import AnkiMorphsDB
from ..exceptions import (
    AnkiFieldNotFound,
    AnkiNoteTypeNotFound,
    CancelledOperationException,
    DefaultSettingsException,
    KnownMorphsFileMalformedException,
    MorphemizerNotFoundException,
    PriorityFileMalformedException,
    PriorityFileNotFoundException,
)
from ..morph_priority_utils import get_morph_priority
from ..morpheme import Morpheme
from ..morphemizers import morphemizer as morphemizer_module
from . import caching, extra_field_utils
from .anki_data_utils import AnkiMorphsCardData
from .card_morphs_metrics import CardMorphsMetrics
from .card_score import _DEFAULT_SCORE, CardScore


def recalc() -> None:
    ################################################################
    #                          FREEZING
    ################################################################
    # Recalc can take a long time if there are many cards, so to
    # prevent Anki from freezing we need to run this on a background
    # thread by using QueryOp.
    #
    # QueryOp docs:
    # https://addon-docs.ankiweb.net/background-ops.html
    ################################################################
    assert mw is not None

    read_enabled_config_filters: list[AnkiMorphsConfigFilter] = (
        ankimorphs_config.get_read_enabled_filters()
    )
    modify_enabled_config_filters: list[AnkiMorphsConfigFilter] = (
        ankimorphs_config.get_modify_enabled_filters()
    )

    # Note: we check for potential errors before running the QueryOp because
    # these processes and confirmations can require gui elements being displayed,
    # which is less of a headache to do on the main thread.
    settings_error: Exception | None = _check_selected_settings_for_errors(
        read_enabled_config_filters, modify_enabled_config_filters
    )

    if settings_error is not None:
        _on_failure(error=settings_error, before_query_op=True)
        return

    if extra_field_utils.new_extra_fields_are_selected():
        confirmed = message_box_utils.confirm_new_extra_fields_selection(parent=mw)
        if not confirmed:
            return

    mw.progress.start(label="Recalculating")
    _start_time: float = time.time()

    # lambda is used to ignore the irrelevant arguments given by QueryOp
    operation = QueryOp(
        parent=mw,
        op=lambda _: _recalc_background_op(
            read_enabled_config_filters, modify_enabled_config_filters
        ),
        success=lambda _: _on_success(_start_time),
    )
    operation.failure(_on_failure)
    operation.with_progress().run_in_background()


def _check_selected_settings_for_errors(
    read_enabled_config_filters: list[AnkiMorphsConfigFilter],
    modify_enabled_config_filters: list[AnkiMorphsConfigFilter],
) -> Exception | None:
    assert mw is not None

    # ideally we would combine the read and modify filters into a set since they
    # usually have significant overlap, but they contain dicts, which makes
    # comparing them impractical, so we just combine them into a list.
    config_filters = read_enabled_config_filters + modify_enabled_config_filters

    model_manager: ModelManager = mw.col.models

    for config_filter in config_filters:
        options_possibly_containing_none: set[str] = {
            config_filter.note_type,
            config_filter.field,
            config_filter.morphemizer_description,
            config_filter.morph_priority_selection,
        }

        if ankimorphs_globals.NONE_OPTION in options_possibly_containing_none:
            return DefaultSettingsException()

        note_type_dict: NotetypeDict | None = mw.col.models.by_name(
            config_filter.note_type
        )
        if note_type_dict is None:
            return AnkiNoteTypeNotFound()

        note_type_field_name_dict: dict[str, tuple[int, FieldDict]] = (
            model_manager.field_map(note_type_dict)
        )

        if config_filter.field not in note_type_field_name_dict:
            return AnkiFieldNotFound()

        morphemizer_found = morphemizer_module.get_morphemizer_by_description(
            config_filter.morphemizer_description
        )
        if morphemizer_found is None:
            return MorphemizerNotFoundException(config_filter.morphemizer_description)

        if (
            config_filter.morph_priority_selection
            != ankimorphs_globals.COLLECTION_FREQUENCY_OPTION
        ):
            priority_file_path = Path(
                mw.pm.profileFolder(),
                ankimorphs_globals.PRIORITY_FILES_DIR_NAME,
                config_filter.morph_priority_selection,
            )
            if not priority_file_path.is_file():
                return PriorityFileNotFoundException(path=str(priority_file_path))

    return None


def _recalc_background_op(
    read_enabled_config_filters: list[AnkiMorphsConfigFilter],
    modify_enabled_config_filters: list[AnkiMorphsConfigFilter],
) -> None:
    am_config = AnkiMorphsConfig()
    caching.cache_anki_data(am_config, read_enabled_config_filters)
    _update_cards_and_notes(am_config, modify_enabled_config_filters)


def _update_cards_and_notes(  # pylint:disable=too-many-locals, too-many-statements, too-many-branches
    am_config: AnkiMorphsConfig,
    modify_enabled_config_filters: list[AnkiMorphsConfigFilter],
) -> None:
    assert mw is not None
    assert mw.col.db is not None
    assert mw.progress is not None

    am_db = AnkiMorphsDB()
    model_manager: ModelManager = mw.col.models
    card_morph_map_cache: dict[int, list[Morpheme]] = am_db.get_card_morph_map_cache()
    handled_cards: dict[int, None] = {}  # we only care about the key lookup, not values
    modified_cards: dict[int, Card] = {}  # a dict makes the offsetting process easier
    modified_notes: list[Note] = []

    # clear relevant caches between recalcs
    am_db.get_morph_priorities_from_collection.cache_clear()
    Morpheme.get_learning_status.cache_clear()

    for config_filter in modify_enabled_config_filters:
        note_type_dict: NotetypeDict = extra_field_utils.add_extra_fields_to_note_type(
            model_manager, config_filter
        )
        field_name_dict: dict[str, tuple[int, FieldDict]] = model_manager.field_map(
            note_type_dict
        )
        morph_priorities: dict[tuple[str, str], int] = get_morph_priority(
            am_db=am_db,
            only_lemma_priorities=am_config.evaluate_morph_lemma,
            morph_priority_selection=config_filter.morph_priority_selection,
        )
        cards_data_dict: dict[int, AnkiMorphsCardData] = am_db.get_am_cards_data_dict(
            note_type_id=model_manager.id_for_name(config_filter.note_type)
        )
        card_amount = len(cards_data_dict)

        for counter, card_id in enumerate(cards_data_dict):
            progress_utils.background_update_progress_potentially_cancel(
                label=f"Updating {config_filter.note_type} cards<br>card: {counter} of {card_amount}",
                counter=counter,
                max_value=card_amount,
            )

            # check if the card has already been handled in a previous note filter
            if card_id in handled_cards:
                continue

            card: Card = mw.col.get_card(card_id)
            note: Note = card.note()

            # make sure to get the values and not references
            original_due: int = int(card.due)
            original_queue: int = int(card.queue)  # queue: suspended, buried, etc.
            original_fields: list[str] = note.fields.copy()
            original_tags: list[str] = note.tags.copy()

            cards_morph_metrics = CardMorphsMetrics(
                am_config,
                card_id,
                card_morph_map_cache,
                morph_priorities,
            )

            if card.type == CARD_TYPE_NEW:
                score_values = CardScore(am_config, cards_morph_metrics)
                card.due = score_values.score

                tags_and_queue_utils.update_tags_and_queue_of_new_cards(
                    am_config=am_config,
                    note=note,
                    card=card,
                    unknowns=len(cards_morph_metrics.unknown_morphs),
                    has_learning_morphs=cards_morph_metrics.has_learning_morphs,
                )

                if config_filter.extra_study_morphs:
                    extra_field_utils.update_study_morphs_field(
                        am_config=am_config,
                        field_name_dict=field_name_dict,
                        note=note,
                        unknowns=cards_morph_metrics.unknown_morphs,
                    )

                if config_filter.extra_all_morphs:
                    extra_field_utils.update_all_morphs_field(
                        am_config=am_config,
                        field_name_dict=field_name_dict,
                        note=note,
                        all_morphs=cards_morph_metrics.all_morphs,
                    )
                if config_filter.extra_all_morphs_count:
                    extra_field_utils.update_all_morphs_count_field(
                        field_name_dict=field_name_dict,
                        note=note,
                        all_morphs=cards_morph_metrics.all_morphs,
                    )

                if config_filter.extra_score:
                    extra_field_utils.update_score_field(
                        field_name_dict=field_name_dict,
                        note=note,
                        score=score_values.score,
                    )
                if config_filter.extra_score_terms:
                    extra_field_utils.update_score_terms_field(
                        field_name_dict=field_name_dict,
                        note=note,
                        score_terms=score_values.terms,
                    )
            else:
                # not new cards
                tags_and_queue_utils.update_tags_of_review_cards(
                    am_config=am_config,
                    note=note,
                    has_learning_morphs=cards_morph_metrics.has_learning_morphs,
                )

            # always update these regardless of the state of the card
            if config_filter.extra_unknown_morphs:
                extra_field_utils.update_unknown_morphs_field(
                    am_config=am_config,
                    field_name_dict=field_name_dict,
                    note=note,
                    unknown_morphs=cards_morph_metrics.unknown_morphs,
                )
            if config_filter.extra_unknown_morphs_count:
                extra_field_utils.update_unknown_morphs_count_field(
                    field_name_dict=field_name_dict,
                    note=note,
                    unknown_morphs=cards_morph_metrics.unknown_morphs,
                )

            if config_filter.extra_highlighted:
                extra_field_utils.update_highlighted_field(
                    am_config=am_config,
                    config_filter=config_filter,
                    field_name_dict=field_name_dict,
                    note=note,
                    card_morphs=cards_morph_metrics.all_morphs,
                )

            # we only want anki to update the cards and notes that have actually changed
            if card.due != original_due or card.queue != original_queue:
                modified_cards[card_id] = card

            if original_fields != note.fields or original_tags != note.tags:
                modified_notes.append(note)

            handled_cards[card_id] = None  # this marks the card as handled

    am_db.con.close()

    if am_config.recalc_offset_new_cards:
        modified_cards = _add_offsets_to_new_cards(
            am_config=am_config,
            card_morph_map_cache=card_morph_map_cache,
            already_modified_cards=modified_cards,
            handled_cards=handled_cards,
        )

    progress_utils.background_update_progress(label="Inserting into Anki collection")
    mw.col.update_cards(list(modified_cards.values()))
    mw.col.update_notes(modified_notes)


def _add_offsets_to_new_cards(
    am_config: AnkiMorphsConfig,
    card_morph_map_cache: dict[int, list[Morpheme]],
    already_modified_cards: dict[int, Card],
    handled_cards: dict[int, None],
) -> dict[int, Card]:
    # This essentially replaces the need for the "skip" options, which in turn
    # makes reviewing cards on mobile a viable alternative.
    assert mw is not None

    earliest_due_card_for_unknown_morph: dict[str, Card] = {}
    cards_with_morph: dict[str, set[int]] = {}  # a set has faster lookup than a list

    card_amount = len(handled_cards)
    for counter, card_id in enumerate(handled_cards):
        progress_utils.background_update_progress_potentially_cancel(
            label=f"Potentially offsetting cards<br>card: {counter} of {card_amount}",
            counter=counter,
            max_value=card_amount,
        )

        if am_config.evaluate_morph_inflection:
            card_unknown_morphs = CardMorphsMetrics.get_unknown_inflections(
                card_morph_map_cache=card_morph_map_cache,
                card_id=card_id,
            )
        else:
            card_unknown_morphs = CardMorphsMetrics.get_unknown_lemmas(
                card_morph_map_cache=card_morph_map_cache,
                card_id=card_id,
            )

        # we don't want to do anything to cards that have multiple unknown morphs
        if len(card_unknown_morphs) == 1:
            unknown_morph = card_unknown_morphs.pop()
            card = mw.col.get_card(card_id)

            if unknown_morph not in earliest_due_card_for_unknown_morph:
                earliest_due_card_for_unknown_morph[unknown_morph] = card
            elif earliest_due_card_for_unknown_morph[unknown_morph].due > card.due:
                earliest_due_card_for_unknown_morph[unknown_morph] = card

            if unknown_morph not in cards_with_morph:
                cards_with_morph[unknown_morph] = {card_id}
            else:
                cards_with_morph[unknown_morph].add(card_id)

    progress_utils.background_update_progress(label="Applying offsets")

    # sort so we can limit to the top x unknown morphs
    earliest_due_card_for_unknown_morph = dict(
        sorted(
            earliest_due_card_for_unknown_morph.items(), key=lambda item: item[1].due
        )
    )
    modified_offset_cards: dict[int, Card] = _apply_offsets(
        am_config=am_config,
        already_modified_cards=already_modified_cards,
        earliest_due_card_for_unknown_morph=earliest_due_card_for_unknown_morph,
        cards_with_morph=cards_with_morph,
    )

    # combine the "lists" of cards we want to modify
    already_modified_cards.update(modified_offset_cards)
    return already_modified_cards


def _apply_offsets(
    am_config: AnkiMorphsConfig,
    already_modified_cards: dict[int, Card],
    earliest_due_card_for_unknown_morph: dict[str, Card],
    cards_with_morph: dict[str, set[int]],
) -> dict[int, Card]:
    assert mw is not None

    modified_offset_cards: dict[int, Card] = {}

    for counter, _unknown_morph in enumerate(earliest_due_card_for_unknown_morph):
        if counter > am_config.recalc_number_of_morphs_to_offset:
            break

        earliest_due_card = earliest_due_card_for_unknown_morph[_unknown_morph]
        all_new_cards_with_morph = cards_with_morph[_unknown_morph]
        all_new_cards_with_morph.remove(earliest_due_card.id)

        for card_id in all_new_cards_with_morph:
            _card = mw.col.get_card(card_id)
            score_and_offset: int | None = None

            # we don't want to offset the card due if it has already been offset previously
            if card_id in already_modified_cards:
                # limit to _DEFAULT_SCORE to prevent integer overflow
                score_and_offset = min(
                    already_modified_cards[card_id].due + am_config.recalc_due_offset,
                    _DEFAULT_SCORE,
                )
                if _card.due == score_and_offset:
                    del already_modified_cards[card_id]
                    continue

            if score_and_offset is None:
                score_and_offset = min(
                    _card.due + am_config.recalc_due_offset,
                    _DEFAULT_SCORE,
                )

            _card.due = score_and_offset
            modified_offset_cards[card_id] = _card

    return modified_offset_cards


def _on_success(_start_time: float) -> None:
    # This function runs on the main thread.
    assert mw is not None
    assert mw.progress is not None

    mw.toolbar.draw()  # updates stats
    mw.progress.finish()

    tooltip("Finished Recalc", parent=mw)
    end_time: float = time.time()
    print(f"Recalc duration: {round(end_time - _start_time, 3)} seconds")


def _on_failure(  # pylint:disable=too-many-branches
    error: (
        Exception
        | DefaultSettingsException
        | MorphemizerNotFoundException
        | CancelledOperationException
        | PriorityFileNotFoundException
        | PriorityFileMalformedException
        | KnownMorphsFileMalformedException
        | AnkiNoteTypeNotFound
        | AnkiFieldNotFound
    ),
    before_query_op: bool = False,
) -> None:
    # This function runs on the main thread.
    assert mw is not None
    assert mw.progress is not None

    if not before_query_op:
        mw.progress.finish()

    if isinstance(error, CancelledOperationException):
        tooltip("Cancelled Recalc")
        return

    title = "AnkiMorphs Error"

    if isinstance(error, DefaultSettingsException):
        text = (
            f'Found a note filter containing a "{ankimorphs_globals.NONE_OPTION}" option. Please select something else.\n\n'
            f"Note filter guide: https://mortii.github.io/anki-morphs/user_guide/setup/settings/note-filter.html"
        )
    elif isinstance(error, AnkiNoteTypeNotFound):
        text = "The AnkiMorphs settings uses one or more note types that no longer exists. Please redo your settings."
    elif isinstance(error, AnkiFieldNotFound):
        text = "The AnkiMorphs settings uses one or more fields that no longer exist. Please redo your settings."
    elif isinstance(error, MorphemizerNotFoundException):
        if error.morphemizer_name == "MecabMorphemizer":
            text = (
                'Morphemizer "AnkiMorphs: Japanese" was not found.\n\n'
                "The Japanese morphemizer can be added by installing a separate companion add-on:\n\n"
                "Link: https://ankiweb.net/shared/info/1974309724 \n\n"
                "Installation code: 1974309724 \n\n"
                "The morphemizer should be automatically found after the add-on is installed and Anki has restarted."
            )
        elif error.morphemizer_name == "JiebaMorphemizer":
            text = (
                'Morphemizer "AnkiMorphs: Chinese" was not found.\n\n'
                "The Chinese morphemizer can be added by installing a separate companion add-on:\n\n"
                "Link: https://ankiweb.net/shared/info/1857311956 \n\n"
                "Installation code: 1857311956 \n\n"
                "The morphemizer should be automatically found after the add-on is installed and Anki has restarted."
            )
        else:
            text = f'Morphemizer "{error.morphemizer_name}" was not found.'

    elif isinstance(error, PriorityFileNotFoundException):
        text = f"Priority file: {error.path} not found!"
    elif isinstance(error, PriorityFileMalformedException):
        text = (
            f"Priority file: {error.path} is malformed (possibly outdated).\n\n"
            f"{error.reason}\n\n"
            f"Please generate a new one."
        )
    elif isinstance(error, KnownMorphsFileMalformedException):
        text = (
            f"Known morphs file: {error.path} is malformed.\n\n"
            f"Please generate a new one."
        )
    else:
        raise error

    message_box_utils.show_error_box(title=title, body=text, parent=mw)
