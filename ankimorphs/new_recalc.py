import pprint
from functools import partial
from typing import Optional, Union

from anki.collection import Collection
from aqt import mw
from aqt.operations import QueryOp
from aqt.utils import showCritical, tooltip

from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.config import get_config, get_configs, get_read_filters
from ankimorphs.exceptions import NoteFilterFieldsException


def main():
    operation = QueryOp(
        parent=mw,
        op=main_background_op,
        success=lambda t: tooltip("Finished Recalc"),  # t = return value of the op
    )
    operation.with_progress().run_in_background()
    operation.failure(on_failure)


def main_background_op(collection: Collection):
    assert mw is not None

    print("running main")

    mw.taskman.run_on_main(
        partial(mw.progress.start, label="recalcing...", immediate=True)
    )

    cache_card_morphemes()
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


def cache_card_morphemes():
    # TODO create a separate tools menu option "Delete Cache".
    # TODO reset cache after preferences changed
    # TODO check make_all_db for any missing pieces (preference settings, etc)
    # TODO check for added or removed cards

    """
    Extracting morphs from cards is expensive so caching them yields a significant
    performance gain.

    When preferences are changed then we need a full rebuild.

    Re-cache cards that have changed type (learning, suspended, etc.) or interval (ivl).
    """

    # included_note_types = get_included_mids()
    # note_type = mw.col.models.get(included_note_types[0])
    # note_filter = get_filter_by_mid_and_tags(note_type["id"], tags=[""])
    # note_types_to_use = get_note_types_to_use(note_filter, note_type)
    # TODO there is probably much superfluous stuff happening in code above

    config_filters_read = get_read_filters()

    # print(f"config_filters read: {pprint.pprint(config_filters_read)}")

    am_db = AnkiMorphsDB()

    card_table_data = []
    morph_table_data = []
    card_morph_map_table_data = []

    for config_filter_read in config_filters_read:
        notes = get_notes_to_update(am_db, config_filter_read)
        card_ids = get_gets_to_update(am_db, config_filter_read)
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

    am_db.insert_many_into_morph_table(morph_table_data)
    am_db.insert_many_into_card_table(card_table_data)
    am_db.insert_many_into_card_morph_map_table(card_morph_map_table_data)
    # am_db.print_table({})
    am_db.con.close()


def get_notes_to_update(am_db: AnkiMorphsDB, config_filter_read, full_rebuild=False):
    # TODO SUSPENDED CARDS CONFIG

    query_one = """
        SELECT *
        FROM notes
        WHERE mid=?
        """

    tags = []
    for tag in config_filter_read["tags"]:
        if tag != "":
            tags.append(tag)

    tags = ["4"]

    print(f"tags: {tags}")

    # query = f"SELECT * FROM notes WHERE mid={config_filter_read['note_type_id']} AND tags in ({','.join(['?']*len(config_filter_read['tags']))})"
    query = f"SELECT * FROM notes WHERE mid={config_filter_read['note_type_id']}"
    # query_tags = f"SELECT * FROM notes WHERE tags LIKE ' demon_slayer '"
    query_tags = f"SELECT * FROM notes where tags like ' demon_slayer '"

    # all_notes_with_note_type = mw.col.db.all(
    #     query_one, config_filter_read["note_type_id"]
    # )

    all_notes_with_note_type = mw.col.db.all(query_tags)

    print(f"all_notes_with_note_type: {all_notes_with_note_type}")

    return all_notes_with_note_type


def get_gets_to_update(am_db: AnkiMorphsDB, config_filter_read, full_rebuild=False):
    """
    cards have notes ->
    notes have note types id (mid) ->
    note types have mid (model id) and name.

    Name is what we set in preferences, so we need to traverse backwards from note types to find cards.
    """

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
