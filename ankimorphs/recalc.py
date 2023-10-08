from collections.abc import Sequence
from functools import partial
from typing import Any, Optional, Union

from anki.cards import Card
from anki.collection import Collection
from anki.utils import split_fields, strip_html
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QMessageBox  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.config import (
    AnkiMorphsConfig,
    AnkiMorphsConfigFilter,
    get_read_enabled_filters,
)
from ankimorphs.exceptions import DefaultSettingsException
from ankimorphs.morph_utils import get_morphemes
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizer import get_morphemizer_by_name


def recalc() -> None:
    assert mw
    operation = QueryOp(
        parent=mw,
        op=recalc_background_op,
        success=lambda t: tooltip("Finished Recalc"),  # t = return value of the op
    )
    operation.with_progress().run_in_background()
    operation.failure(on_failure)


def recalc_background_op(collection: Collection) -> None:
    assert mw
    assert mw.progress
    am_config = AnkiMorphsConfig()
    print("running main")

    # mw.taskman.run_on_main(
    #     partial(mw.progress.start, label="Recalculating...", immediate=True)
    # )

    mw.taskman.run_on_main(
        lambda: mw.progress.update(  # type: ignore
            label="Recalculating...",
        )
    )

    cache_card_morphemes(am_config)
    update_cards()

    # # update stats and refresh display
    # stats.update_stats()

    mw.taskman.run_on_main(mw.toolbar.draw)
    mw.taskman.run_on_main(mw.progress.finish)


def update_cards() -> None:
    """
    get config filters that have 'modify' enabled
    """


def cache_card_morphemes(am_config: AnkiMorphsConfig) -> None:
    """
    Extracting morphs from cards is expensive so caching them yields a significant
    performance gain.

    Rebuilding the entire ankimorphs db every time is faster and much simpler than updating it since
    we can bulk queries to the anki db.
    """

    assert mw
    am_db = AnkiMorphsDB()
    am_db.drop_all_tables()
    am_db.create_all_tables()

    read_config_filters: list[AnkiMorphsConfigFilter] = get_read_enabled_filters()

    card_table_data: list[dict[str, Any]] = []
    morph_table_data: list[dict[str, Any]] = []
    card_morph_map_table_data: list[dict[str, Any]] = []

    for config_filter in read_config_filters:
        if config_filter.note_type == "":
            raise DefaultSettingsException  # handled in on_failure()

        note_ids, expressions = get_notes_to_update(config_filter)
        cards: list[Card] = get_cards_to_update(am_config, note_ids)
        card_amount = len(cards)

        for counter, card in enumerate(cards):
            if counter % 1000 == 0:
                mw.taskman.run_on_main(
                    partial(
                        mw.progress.update,
                        label=f"Caching {config_filter.note_type} cards\n card: {counter} of {card_amount}",
                        value=counter,
                        max=card_amount,
                    )
                )

            card_table_data.append(create_card_dict(card, config_filter))
            morphs = get_card_morphs(expressions[card.nid], am_config, config_filter)
            if morphs is None:
                continue

            for morph in morphs:
                morph_table_data.append(create_morph_dict(morph, card))
                card_morph_map_table_data.append(
                    create_card_morph_map_dict(card, morph)
                )

    mw.taskman.run_on_main(partial(mw.progress.update, label="Saving to ankimorphs.db"))

    am_db.insert_many_into_morph_table(morph_table_data)
    am_db.insert_many_into_card_table(card_table_data)
    am_db.insert_many_into_card_morph_map_table(card_morph_map_table_data)
    # am_db.print_table("Card")
    am_db.con.close()


def create_card_dict(
    card: Card, config_filter: AnkiMorphsConfigFilter
) -> dict[str, int]:
    assert config_filter.note_type_id
    return {
        "id": card.id,
        "learning_status": card.type,
        "queue_status": card.queue,
        "learning_interval": card.ivl,
        "note_type_id": config_filter.note_type_id,
    }


def create_morph_dict(morph: Morpheme, card: Card) -> dict[str, Union[bool, str, int]]:
    return {
        "norm": morph.norm,
        "base": morph.base,
        "inflected": morph.inflected,
        "is_base": morph.norm == morph.inflected,  # gives a bool
        "highest_learning_interval": card.ivl,  # this is updated later in update_morphs()
    }


def create_card_morph_map_dict(
    card: Card, morph: Morpheme
) -> dict[str, Union[int, str]]:
    return {
        "card_id": card.id,
        "morph_norm": morph.norm,
        "morph_inflected": morph.inflected,
    }


def get_card_morphs(
    expression: str, am_config: AnkiMorphsConfig, am_filter: AnkiMorphsConfigFilter
) -> Optional[set[Morpheme]]:
    try:
        morphemizer = get_morphemizer_by_name(am_filter.morphemizer_name)
        assert morphemizer
        morphs = get_morphemes(morphemizer, expression, am_config)
        return set(morphs)
    except KeyError:
        return None


def get_notes_to_update(
    config_filter_read: AnkiMorphsConfigFilter,
) -> tuple[set[int], dict[int, str]]:
    assert mw
    assert mw.col.db

    model_id: Optional[int] = config_filter_read.note_type_id
    expressions: dict[int, str] = {}
    note_ids: set[int] = set()

    for tag in config_filter_read.tags:
        notes_with_tag = set()

        for id_and_fields in get_notes_with_tags(model_id, tag):
            note_id = id_and_fields[0]
            fields = id_and_fields[1]

            notes_with_tag.add(note_id)
            fields_split = split_fields(fields)

            assert config_filter_read.field_index is not None
            field = fields_split[config_filter_read.field_index]

            # store the field now, that way we don't have to re-query
            expressions[note_id] = strip_html(field)

        # only get the notes that intersect all the specified tags
        # i.e. only get the subset of notes that have all the tags
        if len(note_ids) == 0:
            note_ids = notes_with_tag
        else:
            note_ids.intersection_update(notes_with_tag)

    # if the notes have not been reduced, simply return everything stored
    if len(note_ids) == len(expressions):
        return note_ids, expressions

    # only return the expressions of the new subset of notes
    filtered_expressions = {}
    for note_id in note_ids:
        filtered_expressions[note_id] = expressions[note_id]

    return note_ids, filtered_expressions


def get_notes_with_tags(model_id: Optional[int], tag: str) -> list[Sequence[Any]]:
    assert mw
    assert mw.col.db

    if tag == "":
        tag = "%"
    else:
        tag = f"% {tag} %"

    # This is a list of two item lists, [[id: int, flds: str]]
    id_and_fields: list[Sequence[Any]] = mw.col.db.all(
        """
        SELECT id, flds
        FROM notes 
        WHERE mid=? AND tags LIKE ?
        """,
        model_id,
        tag,
    )
    return id_and_fields


def get_cards_to_update(
    am_config: AnkiMorphsConfig,
    note_ids: set[int],
) -> list[Card]:
    """
    note_type -> note -> card
    Notes have mid (model_id/note_type_id) and cards have nid (note_id).
    """
    assert mw
    assert mw.col.db

    cards: list[Card] = []

    for note_id in note_ids:
        for card_id in mw.col.find_cards(f"nid:{note_id}"):
            card = mw.col.get_card(card_id)
            if am_config.parse_ignore_suspended_cards_content:
                if card.queue == -1:  # card is suspended
                    continue
            cards.append(card)
    return cards


def on_failure(error: Union[Exception, DefaultSettingsException]) -> None:
    if isinstance(error, DefaultSettingsException):
        title = "AnkiMorphs Error"
        text = "Save settings before using Recalc!"
        critical_box = QMessageBox(mw)
        critical_box.setWindowTitle(title)
        critical_box.setIcon(QMessageBox.Icon.Critical)
        critical_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        critical_box.setText(text)
        critical_box.exec()
    else:
        raise error
