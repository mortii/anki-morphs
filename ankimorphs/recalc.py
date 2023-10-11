from collections import Counter
from collections.abc import Sequence
from functools import partial
from typing import Any, Optional, Union

from anki.cards import Card
from anki.collection import Collection
from anki.utils import int_time, split_fields, strip_html
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


def get_am_db_cards_to_update(am_db: AnkiMorphsDB, note_type_id: int) -> list[int]:
    assert mw is not None
    assert mw.col.db is not None

    raw_card_ids = am_db.con.execute(
        """
        Select id
        FROM Card
        WHERE learning_status=0 AND note_type_id=?
        """,
        (note_type_id,),
    ).fetchall()

    card_ids = [_tuple[0] for _tuple in raw_card_ids]
    return card_ids


def get_card_difficulty(
    card_id: int,
    card_morph_map_cache: dict[int, list[Any]],
    morph_cache: dict[str, int],
    morph_priority: dict[str, int],
) -> int:
    """
    Set the difficulty (due) on all cards to max by default to prevent buggy cards showing up first.
    card.due is converted to a signed 32-bit integer on the backend, so we get the constraint:
        max(difficulty) = 2147483647 before overflow  #(1.0)

    We want our algorithm to determine difficulty based on the following importance:
        1. morphs is unknown (morph_unknown_penalty)
        2. morphs priority (morph_priority_penalty)

    To achieve the behaviour described above we get the constraint:
        morph_unknown_penalty >= morph_priority_penalty  #(1.1)

    To have the least amount of loss in the algorithm we want to allow the morph_priority_penalty
    to be as high as possible, i.e. the algorithm produces better results if you can set the priority
    of 10,000 morphs vs only 100 morphs.

    With the constraints #(1.0) and #(1.1) we now have the equation:
        2,147,483,647 ÷ (2 * morph_unknown_penalty) = unknown_morphs_amount

    If we let morph_unknown_penalty = 1,000,000 then unknown_morphs_amount ~= 1073,
    This means we can set the priority of up to 1 million morphs, and it won't
    be a problem unless we have over 1073 morphs on a single card. This is an acceptable
    limit--if you have more than 1073 morphs on a single card then you are using anki wrong.

    """
    default_difficulty = 2147483647

    try:
        card_morphs = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return default_difficulty

    difficulty = 0

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

    return morph_cache


def get_card_cache(am_db: AnkiMorphsDB) -> dict[int, dict[str, int]]:
    """
    new cards have learning_status = 0
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
        card_cache[row[0]] = {
            "learning_status": row[1],
            "queue_status": row[2],
            "note_type_id": row[3],
            "learning_interval": row[4],
        }

    return card_cache


def get_card_morph_map_cache(am_db: AnkiMorphsDB) -> dict[int, list[str]]:
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

    # inverse the values, the lower the priority number the more it is prioritized
    for index, key in enumerate(card_morph_map_cache_sorted):
        card_morph_map_cache_sorted[key] = index

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


def update_cards(  # pylint:disable=too-many-locals
    am_config: AnkiMorphsConfig,
) -> None:
    """
    get config filters that have 'modify' enabled

    A single sqlite query is very fast, but looping queries is
    incredibly slow because of the overhead, so instead we query
    once and put the data in dicts which are much faster to lookup.
    """

    assert mw is not None
    assert mw.col.db is not None
    assert mw.progress is not None

    am_db = AnkiMorphsDB()

    modify_config_filters: list[AnkiMorphsConfigFilter] = get_modify_enabled_filters()
    morph_cache: dict[str, int] = get_morph_cache(am_db)
    # card_cache: dict[int, dict[Any]] = get_card_cache(am_db)
    card_morph_map_cache: dict[int, list[Any]] = get_card_morph_map_cache(am_db)
    morph_priority: dict[str, int] = get_morph_priority(am_db, am_config)
    cards_id_due_map: dict[int, int] = get_cards_id_due_map()

    for config_filter in modify_config_filters:
        assert config_filter.note_type_id is not None

        card_ids: list[int] = get_am_db_cards_to_update(
            am_db, config_filter.note_type_id
        )
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
            cards_id_due_map[card_id] = card_difficulty

    # When multiple cards have the same due (difficulty), then anki
    # chooses one for review and ignores the others, therefore
    # we need to make sure all cards have a unique due.
    # To achieve this we sort the cards_id_due_map based on due,
    # and then we replace the due with the position the card
    # has in the dict, normalizing the due value in the process.

    cards_id_due_map_sorted = dict(
        sorted(cards_id_due_map.items(), key=lambda item: item[1])
    )

    modified_time = int_time()
    cards_modified_data: list[list[int]] = []

    for index, card_id in enumerate(cards_id_due_map_sorted, start=1):
        cards_modified_data.append([index, modified_time, card_id])

    mw.col.db.executemany(
        "update cards set due=?, mod=? where id=?",
        cards_modified_data,
    )

    am_db.con.close()


def get_cards_id_due_map() -> dict[int, int]:
    assert mw is not None
    assert mw.col.db is not None

    # Only get unsuspended new cards
    ids_and_due = mw.col.db.all(
        """
        SELECT id, due 
        FROM cards 
        WHERE ivl=0 and queue!=-1
        """
    )
    card_id_due_map = {}
    for row in ids_and_due:
        card_id_due_map[row[0]] = row[1]
    return card_id_due_map


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
