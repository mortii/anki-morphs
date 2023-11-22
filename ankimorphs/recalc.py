import csv
import functools
import os
import re
import time
from collections import Counter
from collections.abc import Sequence
from functools import partial
from typing import Any, Optional, Union

from anki.cards import Card
from anki.collection import Collection
from anki.consts import CARD_TYPE_NEW
from anki.notes import Note
from anki.tags import TagManager
from anki.utils import ids2str
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QMessageBox  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from .anki_data_utils import AnkiCardData, AnkiDBRowData, AnkiMorphsCardData
from .ankimorphs_db import AnkiMorphsDB
from .config import (
    AnkiMorphsConfig,
    AnkiMorphsConfigFilter,
    get_modify_enabled_filters,
    get_read_enabled_filters,
)
from .exceptions import (
    CancelledOperationException,
    DefaultSettingsException,
    FrequencyFileNotFoundException,
)
from .morph_utils import get_morphemes
from .morpheme import Morpheme, SimplifiedMorph
from .morphemizer import get_morphemizer_by_name

start_time: Optional[float] = None


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
    global start_time

    mw.progress.start(label="Recalculating")
    start_time = time.time()

    operation = QueryOp(
        parent=mw,
        op=recalc_background_op,
        success=on_success,
    )
    operation.failure(on_failure)
    operation.with_progress().run_in_background()


def recalc_background_op(collection: Collection) -> None:
    del collection  # unused
    assert mw is not None
    assert mw.progress is not None

    am_config = AnkiMorphsConfig()
    cache_anki_data(am_config)
    update_cards_and_notes(am_config)


def cache_anki_data(  # pylint:disable=too-many-locals
    am_config: AnkiMorphsConfig,
) -> None:
    # Extracting morphs from cards is expensive so caching them yields a significant
    # performance gain.
    #
    # Rebuilding the entire ankimorphs db every time is faster and much simpler than
    # updating it since we can bulk queries to the anki db.

    assert mw is not None

    am_db = AnkiMorphsDB()
    am_db.drop_all_tables()
    am_db.create_all_tables()

    read_config_filters: list[AnkiMorphsConfigFilter] = get_read_enabled_filters()
    ignore_suspended: bool = am_config.parse_ignore_suspended_cards_content

    card_table_data: list[dict[str, Any]] = []
    morph_table_data: list[dict[str, Any]] = []
    card_morph_map_table_data: list[dict[str, Any]] = []

    for config_filter in read_config_filters:
        if config_filter.note_type == "":
            raise DefaultSettingsException  # handled in on_failure()

        card_data_dict: dict[int, AnkiCardData] = create_card_data_dict(
            config_filter,
            config_filter.note_type_id,
            config_filter.tags,
            ignore_suspended,
        )
        card_amount = len(card_data_dict)

        for counter, card_id in enumerate(card_data_dict):
            if counter % 1000 == 0:
                if mw.progress.want_cancel():  # user clicked 'x'
                    raise CancelledOperationException

                mw.taskman.run_on_main(
                    partial(
                        mw.progress.update,
                        label=f"Caching {config_filter.note_type} cards\n card: {counter} of {card_amount}",
                        value=counter,
                        max=card_amount,
                    )
                )

            card_data: AnkiCardData = card_data_dict[card_id]

            if card_data.known_tag:
                highest_interval = am_config.recalc_interval_for_known
            else:
                highest_interval = card_data.interval

            card_table_data.append(
                {
                    "card_id": card_id,
                    "note_id": card_data.note_id,
                    "note_type_id": config_filter.note_type_id,
                    "card_type": card_data.type,
                    "fields": card_data.fields,
                    "tags": card_data.tags,
                }
            )

            morphs = get_card_morphs(card_data.expression, am_config, config_filter)
            if morphs is None:
                continue

            for morph in morphs:
                morph_table_data.append(
                    {
                        "norm": morph.norm,
                        "base": morph.base,
                        "inflected": morph.inflected,
                        "is_base": morph.norm == morph.inflected,  # gives a bool
                        "highest_learning_interval": highest_interval,
                    }
                )
                card_morph_map_table_data.append(
                    {
                        "card_id": card_id,
                        "morph_norm": morph.norm,
                        "morph_inflected": morph.inflected,
                    }
                )

    mw.taskman.run_on_main(partial(mw.progress.update, label="Saving to ankimorphs.db"))

    am_db.insert_many_into_morph_table(morph_table_data)
    am_db.insert_many_into_card_table(card_table_data)
    am_db.insert_many_into_card_morph_map_table(card_morph_map_table_data)
    # am_db.print_table("Cards")
    am_db.con.close()


def create_card_data_dict(
    config_filter: AnkiMorphsConfigFilter,
    model_id: Optional[int],
    tags: list[str],
    ignore_suspended: bool,
) -> dict[int, AnkiCardData]:
    assert mw is not None

    cards_data_dict: dict[int, AnkiCardData] = {}
    am_config = AnkiMorphsConfig()
    tag_manager = TagManager(mw.col)

    for anki_row_data in get_anki_data(model_id, tags, ignore_suspended).values():
        cards_data_dict[anki_row_data.card_id] = AnkiCardData(
            am_config, config_filter, tag_manager, anki_row_data
        )
    return cards_data_dict


def get_anki_data(
    model_id: Optional[int], tags: list[str], ignore_suspended: bool
) -> dict[int, AnkiDBRowData]:
    # This query is hacky because of the limitation in sqlite where you can't
    # really build a query with variable parameter length (tags in this case)
    # More info:
    # https://stackoverflow.com/questions/5766230/select-from-sqlite-table-where-rowid-in-list-using-python-sqlite3-db-api-2-0

    assert mw
    assert mw.col.db

    if ignore_suspended:
        ignore_suspended_string = " AND cards.queue != -1"
    else:
        ignore_suspended_string = ""

    if len(tags) == 1 and tags[0] == "":
        where_clause_string = f"WHERE notes.mid = {model_id}{ignore_suspended_string}"
    else:
        tags_search_string = "".join(
            [f" AND notes.tags LIKE '% {tag} %'" for tag in tags]
        )
        where_clause_string = (
            f"WHERE notes.mid = {model_id}{ignore_suspended_string}{tags_search_string}"
        )

    result: list[Sequence[Any]] = mw.col.db.all(
        """
        SELECT cards.id, cards.ivl, cards.type, cards.queue, notes.id, notes.flds, notes.tags
        FROM cards
        INNER JOIN notes ON
            cards.nid = notes.id
        """
        + where_clause_string,
    )

    anki_db_row_data_dict = {}
    for anki_data in map(AnkiDBRowData, result):
        anki_db_row_data_dict[anki_data.card_id] = anki_data
    return anki_db_row_data_dict


def get_card_morphs(
    expression: str, am_config: AnkiMorphsConfig, am_filter: AnkiMorphsConfigFilter
) -> Optional[set[Morpheme]]:
    try:
        morphemizer = get_morphemizer_by_name(am_filter.morphemizer_name)
        assert morphemizer is not None
        morphs = get_morphemes(morphemizer, expression, am_config)
        return set(morphs)
    except KeyError:
        return None


def update_cards_and_notes(  # pylint:disable=too-many-locals,too-many-statements
    am_config: AnkiMorphsConfig,
) -> None:
    assert mw is not None
    assert mw.col.db is not None
    assert mw.progress is not None

    am_db = AnkiMorphsDB()
    modify_config_filters: list[AnkiMorphsConfigFilter] = get_modify_enabled_filters()
    card_morph_map_cache: dict[int, list[SimplifiedMorph]] = get_card_morph_map_cache(
        am_db
    )
    original_due: dict[int, int] = {}
    handled_cards: dict[int, None] = {}  # we only care about the key lookup, not values
    modified_cards: list[Card] = []
    modified_notes: list[Note] = []

    # clear the morph collection frequency cache between recalcs
    get_morph_collection_priority.cache_clear()

    for config_filter in modify_config_filters:
        assert config_filter.note_type_id is not None

        morph_priority: dict[str, int] = get_morph_priority(am_db, config_filter)
        cards_data_dict: dict[int, AnkiMorphsCardData] = get_am_cards_data_dict(
            am_db, config_filter.note_type_id
        )
        card_amount = len(cards_data_dict)

        for counter, card_id in enumerate(cards_data_dict):
            if counter % 1000 == 0:
                if mw.progress.want_cancel():  # user clicked 'x'
                    raise CancelledOperationException

                mw.taskman.run_on_main(
                    partial(
                        mw.progress.update,
                        label=f"Updating {config_filter.note_type} cards\n card: {counter} of {card_amount}",
                        value=counter,
                        max=card_amount,
                    )
                )

            # check if card has already been handled in a previous note filter
            if card_id in handled_cards:
                continue

            card = mw.col.get_card(card_id)
            note = card.note()

            # make sure to get the values and not references
            original_due[card_id] = int(card.due)
            original_fields = note.fields.copy()
            original_tags = note.tags.copy()

            if card.type == CARD_TYPE_NEW:
                (
                    card_difficulty,
                    card_unknown_morphs,
                    card_has_learning_morphs,
                ) = get_card_difficulty_and_unknowns_and_learning_status(
                    am_config,
                    card_id,
                    card_morph_map_cache,
                    morph_priority,
                )

                card.due = card_difficulty
                update_unknowns_field(config_filter, note, card_unknown_morphs)
                update_difficulty_field(config_filter, note, card_difficulty)
                update_tags(
                    am_config, note, len(card_unknown_morphs), card_has_learning_morphs
                )

            update_highlighted_field(
                am_config,
                config_filter,
                card_morph_map_cache,
                card.id,
                note,
            )

            # We cannot check if due is different from the original here
            # because due is recalculated later.
            modified_cards.append(card)
            handled_cards[card_id] = None

            if original_fields != note.fields or original_tags != note.tags:
                modified_notes.append(note)

    am_db.con.close()

    mw.taskman.run_on_main(
        partial(
            mw.progress.update,
            label="Sorting & filtering cards",
        )
    )

    ################################################################
    #                          UNIQUE DUE
    ################################################################
    # When multiple cards have the same due (difficulty), then anki
    # chooses one for review and ignores the others, therefore we
    # need to make sure all cards have a unique due. To achieve this
    # we sort modified_cards based on due, and then we replace
    # the due with the index the card has in the list.
    ################################################################

    # if the due is the same then the secondary sort is by id
    modified_cards.sort(key=lambda _card: (_card.due, _card.id))

    end_of_queue = get_end_of_queue(modified_cards)

    for index, card in enumerate(modified_cards, start=end_of_queue):
        if card.type == CARD_TYPE_NEW:
            card.due = index

    modified_cards = [
        _card for _card in modified_cards if _card.due != original_due[_card.id]
    ]

    mw.taskman.run_on_main(
        partial(
            mw.progress.update,
            label="Inserting into Anki collection",
        )
    )

    mw.col.update_cards(modified_cards)
    mw.col.update_notes(modified_notes)


def get_card_morph_map_cache(am_db: AnkiMorphsDB) -> dict[int, list[SimplifiedMorph]]:
    card_morph_map_cache: dict[int, list[SimplifiedMorph]] = {}

    # Sorting the morphs (ORDER BY) is crucial to avoid bugs
    card_morph_map_cache_raw = am_db.con.execute(
        """
        SELECT Card_Morph_Map.card_id, Morphs.norm, Morphs.inflected, Morphs.highest_learning_interval
        FROM Card_Morph_Map
        INNER JOIN Morphs ON
            Card_Morph_Map.morph_norm = Morphs.norm AND Card_Morph_Map.morph_inflected = Morphs.inflected
        ORDER BY Morphs.norm, Morphs.inflected
        """,
    ).fetchall()

    for row in card_morph_map_cache_raw:
        card_id = row[0]
        morph = SimplifiedMorph(row[1], row[2], row[3])

        if card_id not in card_morph_map_cache:
            card_morph_map_cache[card_id] = [morph]
        else:
            card_morph_map_cache[card_id].append(morph)

    return card_morph_map_cache


def get_morph_priority(
    am_db: AnkiMorphsDB,
    am_config_filter: AnkiMorphsConfigFilter,
) -> dict[str, int]:
    if am_config_filter.morph_priority_index == 0:
        morph_priority = get_morph_collection_priority(am_db)
    else:
        morph_priority = get_morph_frequency_file_priority(
            am_config_filter.morph_priority
        )
    return morph_priority


@functools.cache
def get_morph_collection_priority(am_db: AnkiMorphsDB) -> dict[str, int]:
    # Sorting the morphs (ORDER BY) is crucial to avoid bugs
    morph_priority = am_db.con.execute(
        """
        SELECT morph_norm, morph_inflected
        FROM Card_Morph_Map
        ORDER BY morph_norm, morph_inflected
        """,
    ).fetchall()

    temp_list = []
    for row in morph_priority:
        temp_list.append(row[0] + row[1])

    card_morph_map_cache_sorted: dict[str, int] = dict(Counter(temp_list).most_common())

    # reverse the values, the lower the priority number the more it is prioritized
    for index, key in enumerate(card_morph_map_cache_sorted):
        card_morph_map_cache_sorted[key] = index

    return card_morph_map_cache_sorted


def get_morph_frequency_file_priority(frequency_file_name: str) -> dict[str, int]:
    assert mw is not None

    morph_priority: dict[str, int] = {}
    frequency_file_path = os.path.join(
        mw.pm.profileFolder(), "frequency-files", frequency_file_name
    )
    try:
        with open(frequency_file_path, mode="r+", encoding="utf-8") as csvfile:
            morph_reader = csv.reader(csvfile, delimiter=",")
            next(morph_reader, None)  # skip the headers
            for index, row in enumerate(morph_reader):
                if index > 50000:
                    # the difficulty algorithm ignores values > 50K
                    # so any rows after this will be ignored anyway
                    break
                key = row[0] + row[1]
                morph_priority[key] = index
    except FileNotFoundError as error:
        raise FrequencyFileNotFoundException(frequency_file_path) from error
    return morph_priority


def get_am_cards_data_dict(
    am_db: AnkiMorphsDB, note_type_id: int
) -> dict[int, AnkiMorphsCardData]:
    assert mw is not None
    assert mw.col.db is not None

    result = am_db.con.execute(
        """
        SELECT card_id, note_id, note_type_id, card_type, fields, tags
        FROM Cards
        WHERE note_type_id = ?
        """,
        (note_type_id,),
    ).fetchall()

    am_db_row_data_dict: dict[int, AnkiMorphsCardData] = {}
    for am_data in map(AnkiMorphsCardData, result):
        am_db_row_data_dict[am_data.card_id] = am_data
    return am_db_row_data_dict


def get_card_difficulty_and_unknowns_and_learning_status(
    am_config: AnkiMorphsConfig,
    card_id: int,
    card_morph_map_cache: dict[int, list[SimplifiedMorph]],
    morph_priority: dict[str, int],
) -> tuple[int, list[str], bool]:
    ####################################################################################
    #                                      ALGORITHM
    ####################################################################################
    # We want our algorithm to determine difficulty based on the following importance:
    #     1. if the card has unknown morphs (unknown_morph_penalty)
    #     2. the priority of the card's morphs (morph_priority_penalty)
    #
    # Stated a different way: one unknown morph must be more punishing than any amount
    # of known morphs with low priority. To achieve the behaviour we get the constraint:
    #     unknown_morph_penalty > sum(morph_priority_penalty)  #(1.1)
    #
    # We need to set some arbitrary limits to make the algorithm practical:
    #     1. Assume max(morph_priority_penalty) = 50k (a frequency list of 50k morphs)  #(2.1)
    #     2. Limit max(sum(morph_priority_penalty)) = max(morph_priority_penalty) * 10  #(2.2)
    #
    # With the equations #(1.1), #(2.1), and #(2.2) we get:
    #     morph_unknown_penalty = 500,000
    ####################################################################################

    # Anki stores 'due' as a 32-bit integers on the backend,
    # 2147483647 is therefore the max value before overflow.
    default_difficulty = 2147483647
    morph_unknown_penalty = 500000
    unknown_morphs: list[str] = []
    has_learning_morph: bool = False

    try:
        card_morphs: list[SimplifiedMorph] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return default_difficulty, unknown_morphs, has_learning_morph

    difficulty = 0

    for morph in card_morphs:
        if morph.highest_learning_interval == 0:
            unknown_morphs.append(morph.inflected)
        elif morph.highest_learning_interval <= am_config.recalc_interval_for_known:
            has_learning_morph = True

        if morph.norm_and_inflected not in morph_priority:
            # Heavily penalizes if a morph is not in frequency file
            difficulty = morph_unknown_penalty - 1
        else:
            difficulty += morph_priority[morph.norm_and_inflected]

    if difficulty >= morph_unknown_penalty:
        # Cap morph priority penalties as described in #(2.2)
        difficulty = morph_unknown_penalty - 1

    difficulty += len(unknown_morphs) * morph_unknown_penalty

    if len(unknown_morphs) == 0 and am_config.skip_only_known_morphs_cards:
        # Move stale cards to the end of the queue
        return default_difficulty, unknown_morphs, has_learning_morph

    return difficulty, unknown_morphs, has_learning_morph


def update_unknowns_field(
    config_filter: AnkiMorphsConfigFilter, note: Note, unknowns: list[str]
) -> None:
    if config_filter.unknowns_field_index is not None:
        if config_filter.unknowns_field_index > 0:
            focus_morph_string: str = "".join(f"{unknown}, " for unknown in unknowns)
            focus_morph_string = focus_morph_string[:-2]  # removes last comma
            note.fields[config_filter.unknowns_field_index - 1] = focus_morph_string


def update_difficulty_field(
    config_filter: AnkiMorphsConfigFilter, note: Note, difficulty: int
) -> None:
    if config_filter.difficulty_field_index is not None:
        if config_filter.difficulty_field_index > 0:
            note.fields[config_filter.difficulty_field_index - 1] = str(difficulty)


def update_highlighted_field(
    am_config: AnkiMorphsConfig,
    config_filter: AnkiMorphsConfigFilter,
    card_morph_map_cache: dict[int, list[SimplifiedMorph]],
    card_id: int,
    note: Note,
) -> None:
    try:
        card_morphs: list[SimplifiedMorph] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return

    if config_filter.highlighted_field_index is not None:
        assert config_filter.field_index is not None
        if config_filter.highlighted_field_index > 0:
            text_to_highlight = note.fields[config_filter.field_index]
            highlighted_text = highlight_text(
                am_config,
                card_morphs,
                text_to_highlight,
            )
            note.fields[config_filter.highlighted_field_index - 1] = highlighted_text


def update_tags(
    am_config: AnkiMorphsConfig, note: Note, unknowns: int, has_learning_morphs: bool
) -> None:
    if unknowns == 0:
        if not has_learning_morphs:
            if am_config.tag_known not in note.tags:
                note.tags.append(am_config.tag_known)
        if am_config.tag_ready in note.tags:
            note.tags.remove(am_config.tag_ready)
    elif unknowns == 1:
        if am_config.tag_ready not in note.tags:
            note.tags.append(am_config.tag_ready)
        if am_config.tag_not_ready in note.tags:
            note.tags.remove(am_config.tag_not_ready)
    else:
        if am_config.tag_not_ready not in note.tags:
            note.tags.append(am_config.tag_not_ready)


def highlight_text(
    am_config: AnkiMorphsConfig,
    card_morphs: list[SimplifiedMorph],
    text_to_highlight: str,
) -> str:
    highlighted_text = text_to_highlight

    # TODO: sorting might be redundant now since morphs are ordered on sqlite query
    # Avoid formatting a smaller morph that is contained in a bigger morph, reverse sort fixes this
    sorted_morphs = sorted(
        card_morphs,
        key=lambda _simple_morph: len(_simple_morph.inflected),
        reverse=True,
    )

    for morph in sorted_morphs:
        if morph.highest_learning_interval == 0:
            morph_status = "unknown"
        elif morph.highest_learning_interval < am_config.recalc_interval_for_known:
            morph_status = "learning"
        else:
            morph_status = "known"

        # print(f"morph: {morph}")
        # print(f"maturity: {morph_status}")
        replacement = f'<span morph-status="{morph_status}">\\1</span>'
        highlighted_text = non_span_sub(
            f"({morph.inflected})", replacement, highlighted_text
        )

    # print(f"highlighted_text: {highlighted_text}")
    return highlighted_text


def non_span_sub(sub: str, repl: str, string: str) -> str:
    txt = ""
    for span in re.split("(<span.*?</span>)", string):
        if span.startswith("<span"):
            txt += span
        else:
            txt += "".join(re.sub(sub, repl, span, flags=re.IGNORECASE))

    # print(f"non_span_sub: {txt}")
    return txt


def get_end_of_queue(modified_cards: list[Card]) -> int:
    assert mw is not None
    assert mw.col.db is not None

    end_of_queue_query_string = (
        """
    SELECT MAX(due) 
    FROM cards 
    """
        + f"WHERE type = 0 AND due != 2147483647 AND id NOT IN {ids2str(card.id for card in modified_cards)}"
    )
    try:
        highest_due: int = int(mw.col.db.scalar(end_of_queue_query_string))
    except TypeError:
        # if all your cards match the note filters then the query will return None
        highest_due = 0
    return highest_due + 1


def on_success(result: Any) -> None:
    # This function runs on the main thread.
    del result  # unused
    assert mw is not None
    assert mw.progress is not None
    global start_time

    mw.toolbar.draw()  # updates stats
    mw.progress.finish()
    tooltip("Finished Recalc", parent=mw)
    if start_time is not None:
        end_time: float = time.time()
        print(f"Recalc duration: {round(end_time - start_time, 3)} seconds")
        start_time = None


def on_failure(
    error: Union[
        Exception,
        DefaultSettingsException,
        CancelledOperationException,
        FrequencyFileNotFoundException,
    ]
) -> None:
    # This function runs on the main thread.
    assert mw is not None
    assert mw.progress is not None
    mw.progress.finish()

    if isinstance(error, CancelledOperationException):
        tooltip("Cancelled Recalc")
        return

    if isinstance(error, DefaultSettingsException):
        title = "AnkiMorphs Error"
        text = "Save settings before using Recalc!"
    elif isinstance(error, FrequencyFileNotFoundException):
        title = "AnkiMorphs Error"
        text = f"Frequency file: {error.path} not found!"
    else:
        raise error

    critical_box = QMessageBox(mw)
    critical_box.setWindowTitle(title)
    critical_box.setIcon(QMessageBox.Icon.Critical)
    critical_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    critical_box.setText(text)
    critical_box.exec()
