import pprint
from collections.abc import Sequence
from functools import partial
from typing import Optional, Union

from anki.collection import Collection
from anki.notes import Note
from anki.utils import split_fields, strip_html
from aqt import mw
from aqt.operations import QueryOp
from aqt.utils import showCritical, tooltip

from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.config import AnkiMorphsConfig, AnkiMorphsConfigFilter, get_read_filters
from ankimorphs.exceptions import NoteFilterFieldsException
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemes import get_morphemes
from ankimorphs.morphemizer import (
    get_all_morphemizers,
    get_morphemizer_by_name,
    morphemizers_by_name,
)


def main() -> None:
    assert mw
    operation = QueryOp(
        parent=mw,
        op=main_background_op,
        success=lambda t: tooltip("Finished Recalc"),  # t = return value of the op
    )
    operation.with_progress().run_in_background()
    operation.failure(on_failure)


def main_background_op(collection: Collection) -> None:
    assert mw
    assert mw.progress
    am_config = AnkiMorphsConfig()
    print("running main")

    # mw.taskman.run_on_main(
    #     partial(mw.progress.start, label="Recalculating...", immediate=True)
    # )

    # mw.taskman.run_on_main(
    #     lambda: mw.progress.start(label="Recalculating...", immediate=True)
    # )

    mw.taskman.run_on_main(
        lambda: mw.progress.update(  # type: ignore
            label=f"Recalculating...",
        )
    )

    cache_card_morphemes(am_config)
    # recalc2()

    mw.taskman.run_on_main(mw.progress.finish)

    #
    # print("running main4")
    #
    # # update stats and refresh display
    # stats.update_stats()
    #
    # print("running main5")
    #
    # mw.taskman.run_on_main(mw.toolbar.draw)
    #
    # print("running main6")


def cache_card_morphemes(am_config: AnkiMorphsConfig) -> None:
    # TODO create a separate tools menu option "Delete Cache".
    # TODO reset cache after preferences changed
    # TODO check make_all_db for any missing pieces (preference settings, etc)
    # TODO check for added or removed cards

    """
    Extracting morphs from cards is expensive so caching them yields a significant
    performance gain.

    When preferences are changed then we need a full rebuild.

    Re-cache cards that have changed type (learning, suspended, etc.) or interval (ivl).

    required variables:
        note:
            id: used to extract desired cards (nid)
            fields: where we extract the desired text

        card:
            card_id: needed for caching
            card.type: needed for caching
            card.ivl: needed for color-coding morphs

        morphs:
            morph.norm
            morph.base
            morph.inflected
            morph.read
            morph.pos
            morph.sub_pos
            is_base

        expression = strip_html(note.fields[field_index])
        _morphs = get_morphemes(morphemizer, expression)
    """

    assert mw
    am_db = AnkiMorphsDB()
    config_filters_read: list[AnkiMorphsConfigFilter] = get_read_filters()

    # card_table_data: Optional[list[dict]] = []
    # morph_table_data: Optional[list[dict]] = []
    # card_morph_map_table_data: Optional[list[dict]] = []

    for config_filter_read in config_filters_read:
        # I need nid and expression field
        notes = get_notes_to_update(am_db, config_filter_read)
        cards = get_cards_to_update(am_db, config_filter_read, note_ids)

        # note.fields[field_index] # this is the expression field
        # expression
        expression = strip_html(note.fields[field_index])
        _morphs = get_morphemes(config_filter_read.morphemizer_name, expression)

        card_amount = len(card_ids)
        for counter, card_id in enumerate(card_ids):
            if counter % 1000 == 0:
                mw.taskman.run_on_main(
                    partial(
                        mw.progress.update,
                        label=f"Caching morphs on card {counter} of {card_amount}",
                        value=counter,
                        max=card_amount,
                    )
                )

            card = mw.col.get_card(card_id)  # TODO bulk get instead

            card_dict = {"id": card_id, "type": card.type, "interval": card.ivl}
            card_table_data.append(card_dict)

            note = card.note()  # TODO bulk get instead
            morphemes = get_card_morphs(note, note_filter, field_index)

            for morph in morphemes:
                morph_dict = {
                    "norm": morph.norm,
                    "base": morph.base,
                    "inflected": morph.inflected,
                    "read": morph.read,
                    "pos": morph.pos,
                    "sub_pos": morph.sub_pos,
                    "is_base": True if morph.norm == morph.inflected else False,
                }
                morph_table_data.append(morph_dict)

                card_morph_map = {
                    "card_id": card_id,
                    "morph_norm": morph.norm,
                    "morph_inflected": morph.inflected,
                }
                card_morph_map_table_data.append(card_morph_map)

    mw.taskman.run_on_main(partial(mw.progress.update, label="Saving to ankimorphs.db"))

    # am_db.insert_many_into_morph_table(morph_table_data)
    # am_db.insert_many_into_card_table(card_table_data)
    # am_db.insert_many_into_card_morph_map_table(card_morph_map_table_data)
    # # am_db.print_table({})
    # am_db.con.close()


def get_card_morphs(note: Note, note_filter, field_index) -> set[Morpheme]:
    try:
        morphemizer = get_morphemizer_by_name(note_filter["Morphemizer"])
        expression = strip_html(note.fields[field_index])
        _morphs = get_morphemes(morphemizer, expression)
        # print(f"morphemizer: {morphemizer}")
        # print(f"expression: {expression}")
        # print(f"_morphs: {_morphs}")
        return set(_morphs)
    except KeyError:
        return set()


def get_notes_to_update(
    am_db: AnkiMorphsDB, config_filter_read: AnkiMorphsConfigFilter, full_rebuild=False
) -> set[int]:
    # TODO SUSPENDED CARDS CONFIG
    # I need nid and expression field, cards do not have field data

    assert mw.col.db

    model_id = config_filter_read.note_type_id

    print(f"config_filter_read['tags']: {config_filter_read.tags}")
    print(f"model_id: {model_id}")

    all_notes = set()
    for tag in config_filter_read.tags:
        notes_with_tag = set()
        print(f"ran tag: {tag}")

        if tag == "":
            tag = "%"
        else:
            tag = f"% {tag} %"

        result = mw.col.db.all(
            """
            SELECT id, flds, sfld, data
            FROM notes 
            WHERE mid=? AND tags LIKE ?
            """,
            model_id,
            tag,
        )
        # print(f"result: {result}")

        for item in result:
            print(f"item[0]: {item[0]}")
            print(f"item[1]: {item[1]}")
            print(f"item[3]: {item[3]}")
            notes_with_tag.add(item[0])

        if len(all_notes) == 0:
            all_notes = notes_with_tag
        else:
            all_notes.intersection_update(notes_with_tag)

        print(f"len all_notes : {len(all_notes)}")

        # split_fields(fields)

    # return expression field

    result = mw.col.db.all(
        """
        SELECT *
        FROM cards 
        WHERE nid=1608533845885
        """,
    )
    print(f"card: {result}")

    assert 1 == 2

    return all_notes


def get_cards_to_update(
    am_db: AnkiMorphsDB, config_filter_read, full_rebuild=False
) -> Sequence[int]:
    """
    We get to cards from note_types (models) via notes.
    Notes have mid (model_id/note_type_id) and cards have nid (note_id).
    """
    assert mw.col.db

    card_ids = mw.col.find_cards(f"note:{config_filter_read['note_type']}")

    if full_rebuild:
        return card_ids

    # all_cards = mw.col.db.all(
    #     """
    #     SELECT *
    #     FROM notes
    #     limit 1
    #     """
    # )
    #
    # all_cards = mw.col.db.all("SELECT name FROM sqlite_master WHERE type='table';")
    # print(f"all_notes: {all_cards}")

    # all_cards = mw.col.db.all("PRAGMA table_info('notes')")
    # print(f"PRAGMA notes: {all_cards}")

    all_cards = mw.col.db.all("PRAGMA table_info('cards')")
    # print(f"PRAGMA cards: {all_cards}")

    all_notes_with_note_type = mw.col.db.all(
        """
        SELECT *
        FROM notes
        WHERE mid=?
        """,
        config_filter_read["note_type_id"],
    )

    # print(
    #     f"all_cards with {config_filter_read['note_type_id']} : {all_notes_with_note_type}"
    # )

    all_card_ids = []
    for row in all_cards:
        all_card_ids.append(row[0])

    # print(f"all_cards: {all_card_ids}")

    # cards_to_update = am_db.con.executemany(
    #     """
    #     SELECT id
    #     FROM Card
    #     WHERE NOT EXISTS (SELECT *
    #               FROM positions
    #               WHERE positions.position_id = employees.position_id);
    #     """,
    #     all_cards,
    # )

    # print(f"result1: {cards_to_update}")

    return card_ids


def on_failure(_exception: Union[Exception, NoteFilterFieldsException]):
    if isinstance(_exception, NoteFilterFieldsException):
        showCritical(
            f'Did not find a field called "{_exception.field_name}" in the Note Type "{_exception.note_type}"\n\n'
            f"Field names are case-sensitive!\n\n"
            f"Read the guide for more info:\n"
            f"https://mortii.github.io/MorphMan/user_guide/setup/preferences/note-filter.html "
        )
    else:
        raise _exception
