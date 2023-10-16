from collections import Counter
from collections.abc import Sequence
from functools import partial
from typing import Any, Optional, Union

import anki.utils
from anki.cards import Card
from anki.collection import Collection
from anki.tags import TagManager
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

    mw.taskman.run_on_main(
        lambda: mw.progress.update(  # type: ignore
            label="Recalculating...",
        )
    )

    cache_card_morphemes(am_config)
    update_cards(am_config)

    mw.taskman.run_on_main(mw.toolbar.draw)  # update stats and refresh display
    mw.taskman.run_on_main(mw.progress.finish)


def get_am_db_cards_to_update(am_db: AnkiMorphsDB, note_type_id: int) -> list[int]:
    assert mw is not None
    assert mw.col.db is not None

    raw_card_ids = am_db.con.execute(
        """
        Select id
        FROM Card
        WHERE learning_status = 0 AND note_type_id = ?
        """,
        (note_type_id,),
    ).fetchall()

    card_ids = [row[0] for row in raw_card_ids]
    return card_ids


def get_card_difficulty_and_unknowns(
    am_config: AnkiMorphsConfig,
    card_id: int,
    card_morph_map_cache: dict[int, list[dict[str, str]]],
    morph_cache: dict[str, int],
    morph_priority: dict[str, int],
) -> tuple[int, list[str]]:
    """
    We want our algorithm to determine difficulty based on the following importance:
        1. if the card has unknown morphs (unknown_morph_penalty)
        2. the priority of the card's morphs (morph_priority_penalty)

    Stated a different way: one unknown morph must be more punishing than any amount
    of known morphs with low priority. To achieve the behaviour we get the constraint:
        unknown_morph_penalty > sum(morph_priority_penalty)  #(1.1)

    We need to set some arbitrary limits to make the algorithm practical:
        1. Assume max(morph_priority) = 50k (a frequency list of 50k morphs)  #(2.1)
        2. Limit max(sum(morph_priority_penalty)) = max(morph_priority) * 10  #(2.2)

    With the equations #(1.1), #(2.1), and #(2.2) we get:
        morph_unknown_penalty = 500,000
    """

    default_difficulty = 2147483647  # arbitrary, 32 bit int max
    morph_unknown_penalty = 500000
    unknowns: list[str] = []

    try:
        card_morphs: list[dict[str, str]] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return default_difficulty, unknowns

    difficulty = 0

    for morph in card_morphs:
        highest_interval = morph_cache[morph["entire_morph"]]
        is_unknown = highest_interval == 0  # gives a bool
        if is_unknown:
            unknowns.append(morph["inflected_morph"])
        difficulty += morph_priority[morph["entire_morph"]]

    if difficulty >= morph_unknown_penalty:
        difficulty = morph_unknown_penalty - 1

    # print(f"pre unknown difficulty: {difficulty}")
    difficulty += len(unknowns) * morph_unknown_penalty
    # print(f"post unknown difficulty: {difficulty}")

    if len(unknowns) == 0 and am_config.skip_stale_cards:
        # Move stale cards to the end of the queue
        return default_difficulty, unknowns

    return difficulty, unknowns


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
        WHERE learning_status = 0
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


def get_card_morph_map_cache(am_db: AnkiMorphsDB) -> dict[int, list[dict[str, str]]]:
    card_morph_map_cache: dict[int, list[dict[str, str]]] = {}

    card_morph_map_cache_raw = am_db.con.execute(
        """
        SELECT card_id, morph_norm, morph_inflected
        FROM Card_Morph_Map
        """,
    ).fetchall()

    card_id_outer = None
    for row in card_morph_map_cache_raw:
        card_id_inner = row[0]
        morph_base = row[1]
        morph_inflection = row[2]

        if card_id_inner != card_id_outer:
            card_morph_map_cache[card_id_inner] = [
                {
                    "entire_morph": morph_base + morph_inflection,
                    "inflected_morph": morph_inflection,
                },
            ]
            card_id_outer = card_id_inner
        else:
            card_morph_map_cache[card_id_inner].append(
                {
                    "entire_morph": morph_base + morph_inflection,
                    "inflected_morph": morph_inflection,
                }
            )

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
    A single sqlite query is very fast, but looping queries is
    incredibly slow because of the overhead, so instead we query
    once and put the data in dicts which are much faster to lookup.
    """

    assert mw is not None
    assert mw.col.db is not None
    assert mw.progress is not None

    am_db = AnkiMorphsDB()
    tag_manager = TagManager(mw.col)

    # these registers the tags in the browser if they don't already exist
    tag_manager.set_collapsed(am_config.tag_ready, collapsed=False)
    tag_manager.set_collapsed(am_config.tag_not_ready, collapsed=False)
    tag_manager.set_collapsed(am_config.tag_known, collapsed=False)

    modify_config_filters: list[AnkiMorphsConfigFilter] = get_modify_enabled_filters()
    morph_cache: dict[str, int] = get_morph_cache(am_db)
    # card_cache: dict[int, dict[str, int]] = get_card_cache(am_db)
    card_morph_map_cache: dict[int, list[dict[str, str]]] = get_card_morph_map_cache(
        am_db
    )
    morph_priority: dict[str, int] = get_morph_priority(am_db, am_config)
    cards_data_map: dict[int, dict[str, Union[int, str]]] = get_cards_data_map()
    end_of_queue: int = mw.col.db.scalar("select count() from cards where type = 0")

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
                        label=f"Updating {config_filter.note_type} cards\n card: {counter} of {card_amount}",
                        value=counter,
                        max=card_amount,
                    )
                )

            if cards_data_map[card_id]["note_type_id"] != config_filter.note_type_id:
                continue

            card_difficulty, unknowns = get_card_difficulty_and_unknowns(
                am_config,
                card_id,
                card_morph_map_cache,
                morph_cache,
                morph_priority,
            )

            cards_data_map[card_id]["due"] = end_of_queue + card_difficulty

            cards_data_map[card_id]["fields"] = modify_card_fields(
                cards_data_map, card_id, config_filter, unknowns
            )

            tags = cards_data_map[card_id]["tags"]

            assert isinstance(tags, str)

            original_tags: set[str] = set(tag_manager.split(tags))

            cards_data_map[card_id]["tags"] = get_new_tags(
                am_config, len(unknowns), original_tags
            )

    # When multiple cards have the same due (difficulty), then anki chooses one
    # for review and ignores the others, therefore we need to make sure all cards
    # have a unique due. To achieve this we sort the cards_id_due_map based on due,
    # and then we replace the due with the position the card has in the dict,
    # normalizing the due value in the process.

    cards_data_map_sorted = dict(
        sorted(cards_data_map.items(), key=lambda item: cards_data_map[item[0]]["due"])
    )

    modified_time = anki.utils.int_time()
    cards_modified_data: list[list[int]] = []
    notes_modified_data: list[list[Union[str, int]]] = []

    for index, card_id in enumerate(cards_data_map_sorted, start=1):
        # print(f"card_id: {card_id}, index:{index}")
        cards_modified_data.append([index, modified_time, card_id])
        notes_modified_data.append(
            [
                cards_data_map_sorted[card_id]["tags"],
                cards_data_map_sorted[card_id]["fields"],
                modified_time,
                cards_data_map_sorted[card_id]["note_id"],
            ]
        )

    mw.col.db.executemany(
        "update cards set due=?, mod=? where id=?",
        cards_modified_data,
    )

    mw.col.db.executemany(
        "update notes set tags=?, flds=?, mod=? where id=?",
        notes_modified_data,
    )

    # mw.col.db.executemany(
    #     "update notes set tags=?, flds=?, sfld=?, csum=?, mod=?, usn=? where id=?",
    #     _notes_to_update,
    # )

    am_db.con.close()


def modify_card_fields(
    cards_data_map: dict[int, dict[str, Union[int, str]]],
    card_id: int,
    config_filter: AnkiMorphsConfigFilter,
    unknowns: list[str],
) -> str:
    fields_any: Union[int, str] = cards_data_map[card_id]["fields"]
    assert isinstance(fields_any, str)
    fields_list: list[str] = anki.utils.split_fields(fields_any)

    if config_filter.focus_morph_field_index is not None:
        if len(unknowns) > 0 and config_filter.focus_morph_field_index > 0:
            focus_morph_string: str = "".join(f"{unknown}, " for unknown in unknowns)
            focus_morph_string = focus_morph_string[:-2]  # removes last comma
            fields_list[config_filter.focus_morph_field_index - 1] = focus_morph_string

    return anki.utils.join_fields(fields_list)


def get_new_tags(am_config: AnkiMorphsConfig, unknowns: int, tags: set[str]) -> str:
    # TODO add the new tags added to config
    if unknowns == 0:
        if am_config.tag_known not in tags:
            tags.add(am_config.tag_known)
        if am_config.tag_ready in tags:
            tags.remove(am_config.tag_ready)
    elif unknowns == 1:
        if am_config.tag_ready not in tags:
            tags.add(am_config.tag_ready)
        if am_config.tag_not_ready in tags:
            tags.remove(am_config.tag_not_ready)
    else:
        if am_config.tag_not_ready not in tags:
            tags.add(am_config.tag_not_ready)

    if not tags:
        return ""
    return f" {' '.join(list(tags))} "


def get_cards_data_map() -> dict[int, dict[str, Union[int, str]]]:
    assert mw is not None
    assert mw.col.db is not None

    # Only get new cards
    ids_and_due = mw.col.db.all(
        """
        SELECT cards.id, cards.due, cards.nid, notes.tags, notes.mid, notes.flds
        FROM cards
        INNER JOIN notes ON
            cards.nid = notes.id
        WHERE cards.type = 0
        """
    )
    card_data_map = {}
    for row in ids_and_due:
        # print(f"row: {row}")
        card_data_map[row[0]] = {
            "due": row[1],
            "note_id": row[2],
            "tags": row[3],
            "note_type_id": row[4],
            "fields": row[5],
        }
    return card_data_map


def cache_card_morphemes(  # pylint:disable=too-many-locals
    am_config: AnkiMorphsConfig,
) -> None:
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

        note_ids, expressions, note_tags_map = get_notes_to_update(config_filter)
        cards: list[Card] = get_cards_to_update(am_config, note_ids)
        card_amount = len(cards)

        print(f"notes amount: {len(note_ids)} in {config_filter.note_type}")
        print(f" card amount: {card_amount} in {config_filter.note_type}")
        # print(f"note_tags_map: {pprint.pprint(note_tags_map)}")

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

            if note_tags_map[card.nid] == am_config.tag_known:
                highest_interval = am_config.recalc_interval_for_known
            else:
                highest_interval = card.ivl

            card_table_data.append(
                create_card_dict(card, config_filter, highest_interval)
            )
            morphs = get_card_morphs(expressions[card.nid], am_config, config_filter)
            if morphs is None:
                continue

            for morph in morphs:
                morph_table_data.append(create_morph_dict(morph, highest_interval))
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
    card: Card, config_filter: AnkiMorphsConfigFilter, highest_interval: int
) -> dict[str, int]:
    assert config_filter.note_type_id
    return {
        "id": card.id,
        "learning_status": card.type,
        "queue_status": card.queue,
        "learning_interval": highest_interval,
        "note_type_id": config_filter.note_type_id,
    }


def create_morph_dict(
    morph: Morpheme,
    highest_interval: int,
) -> dict[str, Union[bool, str, int]]:
    return {
        "norm": morph.norm,
        "base": morph.base,
        "inflected": morph.inflected,
        "is_base": morph.norm == morph.inflected,  # gives a bool
        "highest_learning_interval": highest_interval,  # this is updated later in update_morphs()
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


def get_notes_to_update(  # pylint:disable=too-many-locals
    config_filter_read: AnkiMorphsConfigFilter,
) -> tuple[set[int], dict[int, str], dict[int, str]]:
    assert mw
    assert mw.col.db

    am_config = AnkiMorphsConfig()
    tag_manager = TagManager(mw.col)
    model_id: Optional[int] = config_filter_read.note_type_id
    expressions: dict[int, str] = {}
    note_ids: set[int] = set()
    note_id_tags_map: dict[int, str] = {}

    for tag in config_filter_read.tags:
        notes_with_tag = set()

        for id_fields_tags in get_notes_with_tags(model_id, tag):
            note_id = id_fields_tags[0]
            fields = id_fields_tags[1]
            note_tags = id_fields_tags[2]

            notes_with_tag.add(note_id)
            fields_split = anki.utils.split_fields(fields)

            assert config_filter_read.field_index is not None
            field = fields_split[config_filter_read.field_index]

            # store the field now, that way we don't have to re-query
            expressions[note_id] = anki.utils.strip_html(field)

            if am_config.tag_known in tag_manager.split(note_tags):
                note_id_tags_map[note_id] = am_config.tag_known
            else:
                note_id_tags_map[note_id] = ""

        # only get the notes that intersect all the specified tags
        # i.e. only get the subset of notes that have all the tags
        if len(note_ids) == 0:
            note_ids = notes_with_tag
        else:
            note_ids.intersection_update(notes_with_tag)

    # if the notes have not been reduced, simply return everything stored
    if len(note_ids) == len(expressions):
        return note_ids, expressions, note_id_tags_map

    # only return the expressions of the new subset of notes
    filtered_expressions = {}
    for note_id in note_ids:
        filtered_expressions[note_id] = expressions[note_id]

    return note_ids, filtered_expressions, note_id_tags_map


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
        SELECT id, flds, tags
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
            # if am_config.parse_ignore_suspended_cards_content:
            #     if card.queue == -1:  # card is suspended
            #         continue
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
