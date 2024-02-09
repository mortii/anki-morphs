import csv
import functools
import os
import re
import time
from collections import Counter
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import Any, Optional, Union

from anki.cards import Card
from anki.collection import Collection
from anki.consts import CARD_TYPE_NEW, CardQueue
from anki.models import FieldDict, ModelManager, NotetypeDict, NotetypeId
from anki.notes import Note
from anki.tags import TagManager
from anki.utils import ids2str
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QMessageBox  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from . import ankimorphs_config, ankimorphs_globals, spacy_wrapper
from .anki_data_utils import AnkiCardData, AnkiDBRowData, AnkiMorphsCardData
from .ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from .ankimorphs_db import AnkiMorphsDB
from .exceptions import (
    CancelledOperationException,
    DefaultSettingsException,
    FrequencyFileNotFoundException,
)
from .morpheme import Morpheme
from .morphemizer import SpacyMorphemizer, get_morphemizer_by_name
from .text_preprocessing import (
    get_processed_expression,
    get_processed_morphemizer_morphs,
    get_processed_spacy_morphs,
)

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
        op=_recalc_background_op,
        success=_on_success,
    )
    operation.failure(_on_failure)
    operation.with_progress().run_in_background()


def _recalc_background_op(collection: Collection) -> None:
    del collection  # unused
    assert mw is not None
    assert mw.progress is not None

    am_config = AnkiMorphsConfig()
    _cache_anki_data(am_config)
    _update_cards_and_notes(am_config)


def _cache_anki_data(  # pylint:disable=too-many-locals, too-many-branches, too-many-statements
    am_config: AnkiMorphsConfig,
) -> None:
    # Extracting morphs from cards is expensive, so caching them yields a significant
    # performance gain.
    #
    # Note: this function is a monstrosity, but at some point it's better to have
    # most of the logic in the same function in a way that gives a better overview
    # of all the things that are happening. Refactoring this into even smaller pieces
    # will in effect lead to spaghetti code.

    assert mw is not None

    # Rebuilding the entire ankimorphs db every time is faster and much simpler than
    # updating it since we can bulk queries to the anki db.
    am_db = AnkiMorphsDB()
    am_db.drop_all_tables()
    am_db.create_all_tables()

    # We only want to cache the morphs on the note-filter that have 'read' enabled
    read_enabled_config_filters: list[AnkiMorphsConfigFilter] = (
        ankimorphs_config.get_read_enabled_filters()
    )

    # These lists contain data that will be inserted into ankimorphs.db
    card_table_data: list[dict[str, Any]] = []
    morph_table_data: list[dict[str, Any]] = []
    card_morph_map_table_data: list[dict[str, Any]] = []

    for config_filter in read_enabled_config_filters:
        if config_filter.note_type == "":
            raise DefaultSettingsException  # handled in on_failure()

        cards_data_dict: dict[int, AnkiCardData] = _create_card_data_dict(
            am_config,
            config_filter,
        )
        card_amount = len(cards_data_dict)

        # Batching the text makes spacy much faster, so we flatten the data into the all_text list.
        # To get back to the card_id for every entry in the all_text list, we create a separate list with the keys.
        # These two lists have to be synchronized, i.e., the indexes align, that way they can be used for lookup later.
        all_text: list[str] = []
        all_keys: list[int] = []

        for key, _card_data in cards_data_dict.items():
            # Some spaCy models label all capitalized words as proper nouns,
            # which is pretty bad. To prevent this, we lower case everything.
            # This in turn makes some models not label proper nouns correctly,
            # but this is preferable because we also have the 'Mark as Name'
            # feature that can be used in that case.
            expression = get_processed_expression(
                am_config, _card_data.expression.lower()
            )
            all_text.append(expression)
            all_keys.append(key)

        nlp = None  # spacy.Language
        morphemizer = get_morphemizer_by_name(config_filter.morphemizer_name)
        assert morphemizer is not None

        if isinstance(morphemizer, SpacyMorphemizer):
            spacy_model = config_filter.morphemizer_description.removeprefix("spaCy: ")
            nlp = spacy_wrapper.get_nlp(spacy_model)

        # Since function overloading isn't a thing in python, we use
        # this ugly branching with near identical code. An alternative
        # approach of using variable number of arguments (*args) would
        # require an extra function call, so this is faster.
        #
        # We don't want to store duplicate morphs because it can lead
        # to the same morph being counted twice, which is bad for the
        # difficulty algorithm. We therefore convert the lists of morphs
        # we receive from the morphemizers into sets.
        if nlp is not None:
            for index, doc in enumerate(nlp.pipe(all_text)):
                update_progress_potentially_cancel(
                    label=f"Extracting morphs from\n{config_filter.note_type} cards\n card: {index} of {card_amount}",
                    counter=index,
                    max_value=card_amount,
                )
                morphs = set(get_processed_spacy_morphs(am_config, doc))
                key = all_keys[index]
                cards_data_dict[key].morphs = morphs
        else:
            for index, _expression in enumerate(all_text):
                update_progress_potentially_cancel(
                    label=f"Extracting morphs from\n{config_filter.note_type} cards\n card: {index} of {card_amount}",
                    counter=index,
                    max_value=card_amount,
                )
                morphs = set(
                    get_processed_morphemizer_morphs(
                        morphemizer, _expression, am_config
                    )
                )
                key = all_keys[index]
                cards_data_dict[key].morphs = morphs

        for counter, card_id in enumerate(cards_data_dict):
            update_progress_potentially_cancel(
                label=f"Caching {config_filter.note_type} cards\n card: {counter} of {card_amount}",
                counter=counter,
                max_value=card_amount,
            )
            card_data: AnkiCardData = cards_data_dict[card_id]

            if card_data.automatically_known_tag or card_data.manually_known_tag:
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

            if card_data.morphs is None:
                continue

            for morph in card_data.morphs:
                morph_table_data.append(
                    {
                        "lemma": morph.lemma,
                        "inflection": morph.inflection,
                        "highest_learning_interval": highest_interval,
                    }
                )
                card_morph_map_table_data.append(
                    {
                        "card_id": card_id,
                        "morph_lemma": morph.lemma,
                        "morph_inflection": morph.inflection,
                    }
                )

    morphs_from_files: list[dict[str, Any]] = []
    if am_config.recalc_read_known_morphs_folder is True:
        morphs_from_files = _get_morphs_from_files(am_config)

    mw.taskman.run_on_main(partial(mw.progress.update, label="Saving to ankimorphs.db"))

    am_db.insert_many_into_morph_table(morph_table_data + morphs_from_files)
    am_db.insert_many_into_card_table(card_table_data)
    am_db.insert_many_into_card_morph_map_table(card_morph_map_table_data)
    # am_db.print_table("Cards")
    am_db.con.close()


def _get_morphs_from_files(am_config: AnkiMorphsConfig) -> list[dict[str, Any]]:
    assert mw is not None

    morphs_from_files: list[dict[str, Any]] = []
    known_morphs_dir: str = os.path.join(mw.pm.profileFolder(), "known-morphs")
    known_morphs_dir_path: Path = Path(known_morphs_dir)
    input_files: list[Path] = []

    for path in known_morphs_dir_path.rglob("*.csv"):
        input_files.append(path)

    for input_file in input_files:
        if mw.progress.want_cancel():  # user clicked 'x'
            raise CancelledOperationException

        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label=f"Importing known morphs from file: <br>{input_file.relative_to(known_morphs_dir_path)}",
            )
        )

        with open(input_file, encoding="utf-8") as csvfile:
            morph_reader = csv.reader(csvfile, delimiter=",")
            next(morph_reader, None)  # skip the headers
            for row in morph_reader:
                lemma: str = row[0]
                inflection: str = row[1]

                morphs_from_files.append(
                    {
                        "lemma": lemma,
                        "inflection": inflection,
                        "highest_learning_interval": am_config.recalc_interval_for_known,
                    }
                )

    return morphs_from_files


def _create_card_data_dict(
    am_config: AnkiMorphsConfig,
    config_filter: AnkiMorphsConfigFilter,
) -> dict[int, AnkiCardData]:
    assert mw is not None

    tag_manager = TagManager(mw.col)
    tags: dict[str, str] = config_filter.tags
    model_id: Optional[int] = config_filter.note_type_id
    card_data_dict: dict[int, AnkiCardData] = {}

    for anki_row_data in _get_anki_data(am_config, model_id, tags).values():
        card_data = AnkiCardData(am_config, config_filter, tag_manager, anki_row_data)
        card_data_dict[anki_row_data.card_id] = card_data

    return card_data_dict


def _get_anki_data(
    am_config: AnkiMorphsConfig, model_id: Optional[int], tags_object: dict[str, str]
) -> dict[int, AnkiDBRowData]:
    ################################################################
    #                        SQL QUERY
    ################################################################
    # This sql query is horrible, partly because of the limitation
    # in sqlite where you can't really build a query with variable
    # parameter length (tags in this case)
    # More info:
    # https://stackoverflow.com/questions/5766230/select-from-sqlite-table-where-rowid-in-list-using-python-sqlite3-db-api-2-0
    #
    # EXAMPLE FINAL SQL QUERY:
    #   SELECT cards.id, cards.ivl, cards.type, cards.queue, notes.id, notes.flds, notes.tags
    #   FROM cards
    #   INNER JOIN notes ON
    #       cards.nid = notes.id
    #   WHERE notes.mid = 1691076536776 AND (cards.queue != -1 OR notes.tags LIKE '% am-known-manually %') AND notes.tags LIKE '% movie %'
    ################################################################

    assert mw
    assert mw.col.db

    ignore_suspended_cards = ""
    if am_config.preprocess_ignore_suspended_cards_content:
        # If this part is included, then we don't get cards that are suspended EXCEPT for
        # the cards that were 'set known and skip' and later suspended. We want to always
        # include those cards otherwise we can lose track of known morphs
        ignore_suspended_cards = f" AND (cards.queue != -1 OR notes.tags LIKE '% {am_config.tag_known_manually} %')"

    excluded_tags = tags_object["exclude"]
    included_tags = tags_object["include"]
    tags_search_string = ""

    if len(excluded_tags) > 0:
        tags_search_string += "".join(
            [f" AND notes.tags NOT LIKE '% {_tag} %'" for _tag in excluded_tags]
        )
    if len(included_tags) > 0:
        tags_search_string += "".join(
            [f" AND notes.tags LIKE '% {_tag} %'" for _tag in included_tags]
        )

    result: list[Sequence[Any]] = mw.col.db.all(
        """
        SELECT cards.id, cards.ivl, cards.type, cards.queue, notes.id, notes.flds, notes.tags
        FROM cards
        INNER JOIN notes ON
            cards.nid = notes.id
        """
        + f"WHERE notes.mid = {model_id}{ignore_suspended_cards}{tags_search_string}",
    )

    anki_db_row_data_dict: dict[int, AnkiDBRowData] = {}
    for anki_data in map(AnkiDBRowData, result):
        anki_db_row_data_dict[anki_data.card_id] = anki_data
    return anki_db_row_data_dict


def _update_cards_and_notes(  # pylint:disable=too-many-locals, too-many-statements, too-many-branches
    am_config: AnkiMorphsConfig,
) -> None:
    assert mw is not None
    assert mw.col.db is not None
    assert mw.progress is not None

    model_manager: ModelManager = mw.col.models
    am_db = AnkiMorphsDB()
    modify_config_filters: list[AnkiMorphsConfigFilter] = (
        ankimorphs_config.get_modify_enabled_filters()
    )
    card_morph_map_cache: dict[int, list[Morpheme]] = _get_card_morph_map_cache(am_db)
    original_due: dict[int, int] = {}
    original_queue: dict[int, int] = {}
    handled_cards: dict[int, None] = {}  # we only care about the key lookup, not values
    modified_cards: list[Card] = []
    modified_notes: list[Note] = []

    # clear the morph collection frequency cache between recalcs
    _get_morph_collection_priority.cache_clear()

    for config_filter in modify_config_filters:
        assert config_filter.note_type_id is not None
        note_type_id: NotetypeId = NotetypeId(config_filter.note_type_id)

        _add_extra_fields(config_filter, note_type_id, model_manager)
        note_type_dict = model_manager.get(note_type_id)
        assert note_type_dict is not None
        note_type_field_name_dict = model_manager.field_map(note_type_dict)

        morph_priority: dict[str, int] = _get_morph_priority(am_db, config_filter)
        cards_data_dict: dict[int, AnkiMorphsCardData] = _get_am_cards_data_dict(
            am_db, config_filter.note_type_id
        )
        card_amount = len(cards_data_dict)

        for counter, card_id in enumerate(cards_data_dict):
            update_progress_potentially_cancel(
                label=f"Updating {config_filter.note_type} cards\n card: {counter} of {card_amount}",
                counter=counter,
                max_value=card_amount,
            )

            # check if the card has already been handled in a previous note filter
            if card_id in handled_cards:
                continue

            card = mw.col.get_card(card_id)
            note = card.note()

            # make sure to get the values and not references
            original_due[card_id] = int(card.due)
            original_queue[card_id] = int(card.queue)
            original_fields = note.fields.copy()
            original_tags = note.tags.copy()

            if card.type == CARD_TYPE_NEW:
                (
                    card_difficulty,
                    card_unknown_morphs,
                    card_has_learning_morphs,
                ) = _get_card_difficulty_and_unknowns_and_learning_status(
                    am_config,
                    card_id,
                    card_morph_map_cache,
                    morph_priority,
                )

                card.due = card_difficulty

                _update_tags_and_queue(
                    am_config,
                    note,
                    card,
                    len(card_unknown_morphs),
                    card_has_learning_morphs,
                )

                if config_filter.extra_unknowns:
                    _update_unknowns_field(
                        note_type_field_name_dict, note, card_unknown_morphs
                    )
                if config_filter.extra_unknowns_count:
                    _update_unknowns_count_field(
                        note_type_field_name_dict, note, card_unknown_morphs
                    )
                if config_filter.extra_difficulty:
                    _update_difficulty_field(
                        note_type_field_name_dict, note, card_difficulty
                    )

            if config_filter.extra_highlighted:
                _update_highlighted_field(
                    am_config,
                    config_filter,
                    note_type_field_name_dict,
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
    # chooses one for review and ignores the others, therefore, we
    # need to make sure all cards have a unique due. To achieve this,
    # we sort modified_cards based on due, and then we replace
    # the due with the index the card has in the list.
    ################################################################

    # if the due is the same, then the secondary sort is by id
    modified_cards.sort(key=lambda _card: (_card.due, _card.id))

    end_of_queue = _get_end_of_new_cards_queue(modified_cards)

    for index, card in enumerate(modified_cards, start=end_of_queue):
        if card.type == CARD_TYPE_NEW:
            card.due = index

    modified_cards = [
        _card
        for _card in modified_cards
        if _card_is_modified(_card, original_due, original_queue)
    ]

    mw.taskman.run_on_main(
        partial(
            mw.progress.update,
            label="Inserting into Anki collection",
        )
    )

    mw.col.update_cards(modified_cards)
    mw.col.update_notes(modified_notes)


def _add_extra_fields(
    config_filter: AnkiMorphsConfigFilter,
    note_type_id: NotetypeId,
    model_manager: ModelManager,
) -> None:
    note_type_dict: Optional[NotetypeDict] = model_manager.get(note_type_id)
    assert note_type_dict is not None
    existing_field_names = model_manager.field_names(note_type_dict)
    new_field: FieldDict

    if config_filter.extra_unknowns:
        if ankimorphs_globals.EXTRA_FIELD_UNKNOWNS not in existing_field_names:
            new_field = model_manager.new_field(ankimorphs_globals.EXTRA_FIELD_UNKNOWNS)
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)

    if config_filter.extra_unknowns_count:
        if ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT not in existing_field_names:
            new_field = model_manager.new_field(
                ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT
            )
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)

    if config_filter.extra_highlighted:
        if ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED not in existing_field_names:
            new_field = model_manager.new_field(
                ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
            )
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)

    if config_filter.extra_difficulty:
        if ankimorphs_globals.EXTRA_FIELD_DIFFICULTY not in existing_field_names:
            new_field = model_manager.new_field(
                ankimorphs_globals.EXTRA_FIELD_DIFFICULTY
            )
            model_manager.add_field(note_type_dict, new_field)
            model_manager.update_dict(note_type_dict)


def _card_is_modified(
    _card: Card, original_due: dict[int, int], original_queue: dict[int, int]
) -> bool:
    if _card.due != original_due[_card.id]:
        return True
    if _card.queue != original_queue[_card.id]:
        return True
    return False


def _get_card_morph_map_cache(am_db: AnkiMorphsDB) -> dict[int, list[Morpheme]]:
    card_morph_map_cache: dict[int, list[Morpheme]] = {}

    # Sorting the morphs (ORDER BY) is crucial to avoid bugs
    card_morph_map_cache_raw = am_db.con.execute(
        """
        SELECT Card_Morph_Map.card_id, Morphs.lemma, Morphs.inflection, Morphs.highest_learning_interval
        FROM Card_Morph_Map
        INNER JOIN Morphs ON
            Card_Morph_Map.morph_lemma = Morphs.lemma AND Card_Morph_Map.morph_inflection = Morphs.inflection
        ORDER BY Morphs.lemma, Morphs.inflection
        """,
    ).fetchall()

    for row in card_morph_map_cache_raw:
        card_id = row[0]
        morph = Morpheme(
            lemma=row[1], inflection=row[2], highest_learning_interval=row[3]
        )

        if card_id not in card_morph_map_cache:
            card_morph_map_cache[card_id] = [morph]
        else:
            card_morph_map_cache[card_id].append(morph)

    return card_morph_map_cache


def _get_morph_priority(
    am_db: AnkiMorphsDB,
    am_config_filter: AnkiMorphsConfigFilter,
) -> dict[str, int]:
    if am_config_filter.morph_priority_index == 0:
        morph_priority = _get_morph_collection_priority(am_db)
    else:
        morph_priority = _get_morph_frequency_file_priority(
            am_config_filter.morph_priority
        )
    return morph_priority


@functools.cache
def _get_morph_collection_priority(am_db: AnkiMorphsDB) -> dict[str, int]:
    # Sorting the morphs (ORDER BY) is crucial to avoid bugs
    morph_priority = am_db.con.execute(
        """
        SELECT morph_lemma, morph_inflection
        FROM Card_Morph_Map
        ORDER BY morph_lemma, morph_inflection
        """,
    ).fetchall()

    temp_list = []
    for row in morph_priority:
        temp_list.append(row[0] + row[1])

    card_morph_map_cache_sorted: dict[str, int] = dict(Counter(temp_list).most_common())

    # reverse the values, the lower the priority number is, the more it is prioritized
    for index, key in enumerate(card_morph_map_cache_sorted):
        card_morph_map_cache_sorted[key] = index

    return card_morph_map_cache_sorted


def _get_morph_frequency_file_priority(frequency_file_name: str) -> dict[str, int]:
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


def _get_am_cards_data_dict(
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


def _get_card_difficulty_and_unknowns_and_learning_status(
    am_config: AnkiMorphsConfig,
    card_id: int,
    card_morph_map_cache: dict[int, list[Morpheme]],
    morph_priority: dict[str, int],
) -> tuple[int, list[str], bool]:
    ####################################################################################
    #                                      ALGORITHM
    ####################################################################################
    # We want our algorithm to determine difficulty based on the following importance:
    #     1. If the card has unknown morphs (unknown_morph_penalty)
    #     2. The priority of the card's morphs (morph_priority_penalty)
    #
    # Stated in a different way: one unknown morph must be penalized more than any number
    # of known morphs with low priorities. To achieve this, we get the constraint:
    #     unknown_morph_penalty > sum(morph_priority_penalty) #(1.1)
    #
    # We need to set some arbitrary limits to make the algorithm practical:
    #     1. Assume max(morph_priority_penalty) = 50k (a frequency list of 50k morphs) #(2.1)
    #     2. Limit max(sum(morph_priority_penalty)) = max(morph_priority_penalty) * 10 #(2.2)
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
        card_morphs: list[Morpheme] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return default_difficulty, unknown_morphs, has_learning_morph

    difficulty = 0

    for morph in card_morphs:
        assert morph.highest_learning_interval is not None

        if morph.highest_learning_interval == 0:
            unknown_morphs.append(morph.inflection)
        elif morph.highest_learning_interval <= am_config.recalc_interval_for_known:
            has_learning_morph = True

        if morph.lemma_and_inflection not in morph_priority:
            # Heavily penalizes if a morph is not in frequency file
            difficulty = morph_unknown_penalty - 1
        else:
            difficulty += morph_priority[morph.lemma_and_inflection]

    if difficulty >= morph_unknown_penalty:
        # Cap morph priority penalties as described in #(2.2)
        difficulty = morph_unknown_penalty - 1

    difficulty += len(unknown_morphs) * morph_unknown_penalty

    if len(unknown_morphs) == 0 and am_config.skip_only_known_morphs_cards:
        # Move stale cards to the end of the queue
        return default_difficulty, unknown_morphs, has_learning_morph

    return difficulty, unknown_morphs, has_learning_morph


def _update_unknowns_field(
    note_type_field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    unknowns: list[str],
) -> None:
    focus_morph_string: str = "".join(f"{unknown}, " for unknown in unknowns)
    focus_morph_string = focus_morph_string[:-2]  # removes last comma
    index: int = note_type_field_name_dict[ankimorphs_globals.EXTRA_FIELD_UNKNOWNS][0]
    note.fields[index] = focus_morph_string


def _update_unknowns_count_field(
    note_type_field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    unknowns: list[str],
) -> None:
    index: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT
    ][0]
    note.fields[index] = str(len(unknowns))


def _update_difficulty_field(
    note_type_field_name_dict: dict[str, tuple[int, FieldDict]],
    note: Note,
    difficulty: int,
) -> None:
    index: int = note_type_field_name_dict[ankimorphs_globals.EXTRA_FIELD_DIFFICULTY][0]
    note.fields[index] = str(difficulty)


def _update_highlighted_field(  # pylint:disable=too-many-arguments
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

    assert config_filter.field_index is not None
    text_to_highlight = note.fields[config_filter.field_index]
    highlighted_text = _highlight_text(
        am_config,
        card_morphs,
        text_to_highlight,
    )

    highlighted_index: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
    ][0]
    note.fields[highlighted_index] = highlighted_text


def _update_tags_and_queue(
    am_config: AnkiMorphsConfig,
    note: Note,
    card: Card,
    unknowns: int,
    has_learning_morphs: bool,
) -> None:
    # There are 3 different tags that we want recalc to update:
    # - am-ready
    # - am-not-ready
    # - am-known-automatically
    #
    # These tags should be mutually exclusive, and there are many
    # complicated scenarios where a normal tag progression might
    # not occur, so we have to make sure that we remove all the
    # tags that shouldn't be there for each case, even if it seems
    # redundant.
    #
    # Note: only new cards are handled in this function!

    suspended = CardQueue(-1)
    mutually_exclusive_tags: list[str] = [
        am_config.tag_ready,
        am_config.tag_not_ready,
        am_config.tag_known_automatically,
    ]

    if am_config.tag_known_manually in note.tags:
        remove_exclusive_tags(note, mutually_exclusive_tags)
    elif unknowns == 0:
        if am_config.recalc_suspend_known_new_cards and card.queue != suspended:
            card.queue = suspended
        if am_config.tag_known_automatically not in note.tags:
            remove_exclusive_tags(note, mutually_exclusive_tags)
            # if a card has any learning morphs, then we don't want to
            # give it a 'known' tag because that would automatically
            # give the morphs a 'known'-status instead of 'learning'
            if not has_learning_morphs:
                note.tags.append(am_config.tag_known_automatically)
    elif unknowns == 1:
        if am_config.tag_ready not in note.tags:
            remove_exclusive_tags(note, mutually_exclusive_tags)
            note.tags.append(am_config.tag_ready)
    else:
        if am_config.tag_not_ready not in note.tags:
            remove_exclusive_tags(note, mutually_exclusive_tags)
            note.tags.append(am_config.tag_not_ready)


def remove_exclusive_tags(note: Note, mutually_exclusive_tags: list[str]) -> None:
    for tag in mutually_exclusive_tags:
        if tag in note.tags:
            note.tags.remove(tag)


def _highlight_text(
    am_config: AnkiMorphsConfig,
    card_morphs: list[Morpheme],
    text_to_highlight: str,
) -> str:
    highlighted_text = text_to_highlight

    # Avoid formatting a smaller morph contained in a bigger morph, reverse sort fixes this
    sorted_morphs = sorted(
        card_morphs,
        key=lambda _simple_morph: len(_simple_morph.inflection),
        reverse=True,
    )

    for morph in sorted_morphs:
        # print(f"morph: {morph.base}, {morph.inflected}")
        assert morph.highest_learning_interval is not None

        if morph.highest_learning_interval == 0:
            morph_status = "unknown"
        elif morph.highest_learning_interval < am_config.recalc_interval_for_known:
            morph_status = "learning"
        else:
            morph_status = "known"

        replacement = f'<span morph-status="{morph_status}">\\1</span>'
        highlighted_text = _create_highlight_span(
            f"({morph.inflection})", replacement, highlighted_text
        )

    # print(f"highlighted_text: {highlighted_text}")
    return highlighted_text


def _create_highlight_span(sub: str, repl: str, string: str) -> str:
    txt = ""
    for span in re.split("(<span.*?</span>)", string):
        if span.startswith("<span"):
            txt += span
        else:
            try:
                txt += "".join(re.sub(sub, repl, span, flags=re.IGNORECASE))
            except re.error as error:
                # malformed text like this: "え工ｴｴｪｪ(´д｀)ｪｪｴｴ工" causes an error
                txt += f"this text is broken: {error}"

    # print(f"non_span_sub: {txt}")
    return txt


def _get_end_of_new_cards_queue(modified_cards: list[Card]) -> int:
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


def _on_success(result: Any) -> None:
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


def _on_failure(
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


def update_progress_potentially_cancel(
    label: str, counter: int, max_value: int
) -> None:
    assert mw is not None

    if counter % 1000 == 0:
        if mw.progress.want_cancel():  # user clicked 'x'
            raise CancelledOperationException

        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label=label,
                value=counter,
                max=max_value,
            )
        )
