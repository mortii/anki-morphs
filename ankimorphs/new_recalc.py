import pprint
from collections.abc import Sequence
from functools import partial
from typing import Optional, Union

from anki.cards import Card
from anki.collection import Collection
from anki.notes import Note
from anki.utils import split_fields, strip_html
from aqt import mw
from aqt.operations import QueryOp
from aqt.utils import showCritical, tooltip

from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.config import AnkiMorphsConfig, AnkiMorphsConfigFilter, get_read_filters
from ankimorphs.exceptions import NoteFilterFieldsException
from ankimorphs.morph_utils import get_morphemes
from ankimorphs.morpheme import Morpheme
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
            fields: where we extract the desired text (cards don't have this data)

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

        _morphs = get_morphemes(morphemizer, expression)
    """

    assert mw
    am_db = AnkiMorphsDB()
    am_db.drop_all_tables()
    am_db.create_all_tables()

    config_filters_read: list[AnkiMorphsConfigFilter] = get_read_filters()

    card_table_data: Optional[list[dict]] = []
    morph_table_data: Optional[list[dict]] = []
    card_morph_map_table_data: Optional[list[dict]] = []

    for config_filter_read in config_filters_read:
        note_ids, expressions = get_notes_to_update(am_db, config_filter_read)
        cards: list[Card] = get_cards_to_update(
            am_db, am_config, config_filter_read, note_ids
        )

        # TODO check if stored cards match the fetched cards from anki....
        # I now have a filtered list based on note type, so i also need to fetch cards that
        # have that same note type
        stored_card_ids = am_db.get_all_card_ids(cards[0].nid)

        if len(stored_card_ids) == len(cards):
            # hmmmm this will probably take longer than just storing the cache everytime....
            print(f"naive cache hit")
            continue

        print(f"cards len: {len(cards)}")
        print(f"stored_card_ids len: {len(stored_card_ids)}")

        card_amount = len(cards)
        for counter, card in enumerate(cards):
            if counter % 1000 == 0:
                mw.taskman.run_on_main(
                    partial(
                        mw.progress.update,
                        label=f"Caching morphs on card {counter} of {card_amount}",
                        value=counter,
                        max=card_amount,
                    )
                )

            card_dict = {
                "id": card.id,
                "note_id": card.nid,
                "queue": card.queue,
                "interval": card.ivl,
            }
            card_table_data.append(card_dict)

            morphemes = get_card_morphs(
                expressions[card.nid], am_config, config_filter_read
            )
            if morphemes is None:
                continue

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
                    "card_id": card.id,
                    "morph_norm": morph.norm,
                    "morph_inflected": morph.inflected,
                }
                card_morph_map_table_data.append(card_morph_map)

    mw.taskman.run_on_main(partial(mw.progress.update, label="Saving to ankimorphs.db"))

    am_db.insert_many_into_morph_table(morph_table_data)
    am_db.insert_many_into_card_table(card_table_data)
    am_db.insert_many_into_card_morph_map_table(card_morph_map_table_data)
    # am_db.print_table()
    am_db.con.close()


def get_card_morphs(
    expression: str, am_config: AnkiMorphsConfig, am_filter: AnkiMorphsConfigFilter
) -> Optional[set[Morpheme]]:
    try:
        morphemizer = get_morphemizer_by_name(am_filter.morphemizer_name)
        _morphs = get_morphemes(morphemizer, expression, am_config)
        return set(_morphs)
    except KeyError:
        return None


def get_notes_to_update(
    am_db: AnkiMorphsDB, config_filter_read: AnkiMorphsConfigFilter, full_rebuild=False
) -> tuple[set[int], dict[int, str]]:
    assert mw.col.db

    model_id = config_filter_read.note_type_id

    print(f"config_filter_read['tags']: {config_filter_read.tags}")
    print(f"model_id: {model_id}")

    expressions: dict[int, str] = {}
    note_ids: set[int] = set()
    for tag in config_filter_read.tags:
        notes_with_tag = set()
        print(f"ran tag: {tag}")

        if tag == "":
            tag = "%"
        else:
            tag = f"% {tag} %"

        result = mw.col.db.all(
            """
            SELECT id, flds
            FROM notes 
            WHERE mid=? AND tags LIKE ?
            """,
            model_id,
            tag,
        )
        # print(f"result: {result}")

        for item in result:
            # print(f"item[0] id: {item[0]}")
            # print(f"item[1] flds: {item[1]}")
            notes_with_tag.add(item[0])
            fields_split = split_fields(item[1])
            desire_field = fields_split[config_filter_read.field_index]
            expressions[item[0]] = desire_field
            # print(f"fields_split field index: {strip_html(desire_field)}")

        if len(note_ids) == 0:
            note_ids = notes_with_tag
        else:
            note_ids.intersection_update(notes_with_tag)

        print(f"len all_notes : {len(note_ids)}")

    if len(note_ids) == len(expressions):
        return note_ids, expressions

    filtered_expressions = {}
    for note_id in note_ids:
        filtered_expressions[note_id] = expressions[note_id]

    return note_ids, filtered_expressions


def get_cards_to_update(
    am_db: AnkiMorphsDB,
    am_config: AnkiMorphsConfig,
    config_filter_read: AnkiMorphsConfigFilter,
    note_ids: set[int],
) -> list[Card]:
    """
    We get to cards from note_types (models) via notes.
    Notes have mid (model_id/note_type_id) and cards have nid (note_id).
    """
    assert mw.col.db

    # TODO check if stored cards match the fetched cards from anki....

    cards: list[Card] = []
    for note_id in note_ids:
        query = f"nid:{note_id}"
        found_card_ids = mw.col.find_cards(query)
        for card_id in found_card_ids:
            card = mw.col.get_card(card_id)
            if am_config.parse_ignore_suspended_cards_content:
                if card.queue == -1:  # card is suspended
                    continue
            cards.append(card)

    return cards


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
