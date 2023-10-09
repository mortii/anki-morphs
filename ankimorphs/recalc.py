from collections import Counter
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
    get_modify_enabled_filters,
    get_read_enabled_filters,
)
from ankimorphs.exceptions import DefaultSettingsException
from ankimorphs.morph_utils import get_morphemes
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizer import get_morphemizer_by_name


def recalc() -> None:
    assert mw is not None
    operation = QueryOp(
        parent=mw,
        op=recalc_background_op,
        success=lambda t: tooltip("Finished Recalc"),  # t = return value of the op
    )
    operation.with_progress().run_in_background()
    operation.failure(on_failure)


def recalc_background_op(collection: Collection) -> None:
    assert mw is not None
    assert mw.progress is not None

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
    update_cards(am_config)

    # # update stats and refresh display
    # stats.update_stats()

    mw.taskman.run_on_main(mw.toolbar.draw)
    mw.taskman.run_on_main(mw.progress.finish)


def get_am_db_cards_to_update(note_type_id: int) -> list[int]:
    assert mw is not None
    assert mw.col.db is not None

    am_db = AnkiMorphsDB()

    raw_card_ids = am_db.con.execute(
        """
        Select id
        FROM Card
        WHERE learning_status=0 AND note_type_id=?
        """,
        (note_type_id,),
    ).fetchall()

    am_db.con.close()

    card_ids = [_tuple[0] for _tuple in raw_card_ids]

    # cards: list[Card] = []
    #
    # for card_id in card_ids:
    #     for card_id in mw.col.find_cards(f"nid:{note_id}"):
    #         card = mw.col.get_card(card_id)
    #         if am_config.parse_ignore_suspended_cards_content:
    #             if card.queue == -1:  # card is suspended
    #                 continue
    #         cards.append(card)
    # return cards

    return card_ids


def get_card_difficulty(
    card_id: int,
    card_morph_map_cache: dict[int, list[Any]],
    morph_cache: dict[str, int],
    morph_priority: dict[str, int],
) -> int:
    """
    Set the difficulty (due) on all cards to max by default to prevent buggy cards to showing up first.
    if a card already has this due it won't update, so this will not have a negative impact on syncing.
    card.due is converted to a signed 32-bit integer on the backend, so max value is 2147483647 before overflow

    In our algorithm we want the unknown status of the morph to have the most significance then
    the priority status.

    To have the least amount of loss in the algorithm we want to allow the value of unknown and priority
    to be as high as possible, but the upper limit is 2,147,483,647 as described above.

    Since priority is less significant than unknown, its max value must be <= unknown value

    if max(priority) = max(unknown), then the max value a morph can have is 2 * unknown

    Uknown = 1,000,000
    2,147,483,647 ÷ (2 * Unknown) = 1073.7 morphs

    We can have up to 1073 morphs on a card if we allow the unknown value to be 1 million, which is
    well within reason.
    """

    default_difficulty = 2147483647
    difficulty = 0

    # for i, key in enumerate(card_morph_map_cache):
    #     if i > 10:
    #         break
    #     print(f"card_morph_map_cache[{key}]: {card_morph_map_cache[key]}")
    #
    # for i, key in enumerate(morph_priority):
    #     if i > 10:
    #         break
    #     print(f"morph_priority[{key}]: {morph_priority[key]}")

    try:
        card_morphs = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return default_difficulty

    for morph in card_morphs:
        highest_interval = morph_cache[morph]
        is_unknown = highest_interval == 0  # gives a bool
        difficulty += (1000000 * is_unknown) + morph_priority[morph]

    return difficulty


def get_morph_cache(am_db: AnkiMorphsDB) -> dict[str, int]:
    morph_cache = {}

    morphs_raw = am_db.con.execute(
        """
        SELECT norm, inflected, highest_learning_interval
        FROM Morph
        """,
    ).fetchall()

    for row in morphs_raw:
        morph_key = row[0] + row[1]
        morph_cache[morph_key] = row[2]

    # for key in morph_cache:
    #     print(f"morph_cache[{key}]: {morph_cache[key]}")

    # print(f"morph_cache size: {sys.getsizeof(morph_cache)}")

    return morph_cache


def get_card_cache(am_db: AnkiMorphsDB) -> dict[int, dict[str, int]]:
    """
    learning interval of new cards (learning_status=0)
    is always 0
    """
    card_cache: dict[int, dict[str, int]] = {}

    cards_raw = am_db.con.execute(
        """
        SELECT *
        FROM Card
        WHERE learning_status=0
        """,
    ).fetchall()

    for row in cards_raw:
        # isinstance(row[0], int)
        # isinstance(row[1], int)
        # isinstance(row[2], int)
        # isinstance(row[3], int)
        # isinstance(row[4], int)

        card_cache[row[0]] = {
            "learning_status": row[1],
            "queue_status": row[2],
            "note_type_id": row[3],
            "learning_interval": row[4],
        }

    # for key in card_cache:
    #     print(f"card_cache[{key}]: {card_cache[key]}")

    # print(f"morph_cache size: {sys.getsizeof(morph_cache)}")

    return card_cache


def get_card_morph_map_cache(am_db: AnkiMorphsDB) -> dict[int, list[str]]:
    """
    learning interval of new cards (learning_status=0)
    is always 0
    """
    card_morph_map_cache: dict[int, list[str]] = {}

    card_morph_map_cache_raw = am_db.con.execute(
        """
        SELECT card_id, morph_norm, morph_inflected
        FROM Card_Morph_Map
        """,
    ).fetchall()

    card_id_outer = None
    for row in card_morph_map_cache_raw:
        card_id_inner = row[0]

        if card_id_inner != card_id_outer:
            card_morph_map_cache[card_id_inner] = [row[1] + row[2]]
            card_id_outer = card_id_inner
        else:
            card_morph_map_cache[card_id_inner].append(row[1] + row[2])

    # for key in card_morph_map_cache:
    #     print(f"card_morph_map_cache[{key}]: {card_morph_map_cache[key]}")

    return card_morph_map_cache


def get_morph_collection_priority(am_db: AnkiMorphsDB) -> dict[str, int]:
    morph_priority = am_db.con.execute(
        """
        SELECT morph_norm, morph_inflected
        FROM Card_Morph_Map
        """,
    ).fetchall()

    temp_list = []
    for row in morph_priority:
        temp_list.append(row[0] + row[1])

    card_morph_map_cache: dict[str, int] = Counter(temp_list)
    card_morph_map_cache_sorted = dict(
        sorted(card_morph_map_cache.items(), key=lambda item: item[1], reverse=True)
    )

    # for counter, key in enumerate(card_morph_map_cache_sorted):
    #     if counter > 100:
    #         break
    #     print(f"pre morph_priority[{key}]: {card_morph_map_cache_sorted[key]}")

    # inverse the values, the lower the priority number the more it is prioritized
    for index, key in enumerate(card_morph_map_cache_sorted):
        card_morph_map_cache_sorted[key] = index

    # for counter, key in enumerate(card_morph_map_cache_sorted):
    #     if counter > 100:
    #         break
    #     print(f"post morph_priority[{key}]: {card_morph_map_cache_sorted[key]}")

    return card_morph_map_cache_sorted


def get_morph_priority(
    am_db: AnkiMorphsDB, am_config: AnkiMorphsConfig
) -> dict[str, int]:
    morph_priority: dict[str, int] = {}

    if am_config.recalc_prioritize_collection:
        print("prioritizing collection")
        morph_priority = get_morph_collection_priority(am_db)

    # TODO add text file branch

    return morph_priority


def update_cards(am_config: AnkiMorphsConfig) -> None:
    """
    get config filters that have 'modify' enabled

    A single sqlite query is very fast, but looping queries is
    incredibly slow because of the overhead, so instead we query
    once and put the data in dicts which is much faster.

    algorithm:
        1. unknowns
        2. priority of unknowns

        unknown * 10000 + unknown_priority
    """

    # for x in [1, 10, 100, 1000, 10000, 1000000]:
    #     print(f"sigmoid of {x}: {sigmoid(x)}")
    #
    # return

    assert mw is not None
    assert mw.progress is not None

    am_db = AnkiMorphsDB()

    modify_config_filters: list[AnkiMorphsConfigFilter] = get_modify_enabled_filters()

    morph_cache: dict[str, int] = get_morph_cache(am_db)
    # card_cache: dict[int, dict[Any]] = get_card_cache(am_db)
    card_morph_map_cache: dict[int, list[Any]] = get_card_morph_map_cache(am_db)
    morph_priority: dict[str, int] = get_morph_priority(am_db, am_config)

    for i, key in enumerate(morph_priority):
        if i > 10:
            break
        print(f"morph_priority1[{key}]: {morph_priority[key]}")

    for config_filter in modify_config_filters:
        assert config_filter.note_type_id is not None
        card_ids: list[int] = get_am_db_cards_to_update(config_filter.note_type_id)
        card_amount = len(card_ids)

        for counter, card_id in enumerate(card_ids):
            if counter % 1000 == 0:
                mw.taskman.run_on_main(
                    partial(
                        mw.progress.update,
                        label=f"modifying {config_filter.note_type} cards\n card: {counter} of {card_amount}",
                        value=counter,
                        max=card_amount,
                    )
                )

            card_difficulty = get_card_difficulty(
                card_id, card_morph_map_cache, morph_cache, morph_priority
            )

            print(f" card {card_id} difficulty: {card_difficulty}")

            # difficulty = 2147483647

            # use a bad implementation first to find improvements

            # morphs = am_db.con.execute(
            #     """
            #     SELECT Morph.highest_learning_interval
            #     FROM Card_Morph_Map
            #     INNER JOIN Morph
            #         ON Card_Morph_Map.morph_norm = Morph.norm AND Card_Morph_Map.morph_inflected = Morph.inflected
            #     WHERE card_id=?
            #     """,
            #     (card_id,),
            # ).fetchall()
            #
            # print(f"morphs ivls: {morphs}")

            # get difficulty of card expression (frequency list)
            # update the due of the card

    am_db.con.close()


def cache_card_morphemes(am_config: AnkiMorphsConfig) -> None:
    """
    Extracting morphs from cards is expensive so caching them yields a significant
    performance gain.

    Rebuilding the entire ankimorphs db every time is faster and much simpler than updating it since
    we can bulk queries to the anki db.
    """

    print("caching cards")

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

        print(f"notes amount: {len(note_ids)} in {config_filter.note_type}")

        cards: list[Card] = get_cards_to_update(am_config, note_ids)
        card_amount = len(cards)
        print(f" card amount: {card_amount} in {config_filter.note_type}")

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
