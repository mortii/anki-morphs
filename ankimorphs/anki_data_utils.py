"""
By using a class with slots we get the speed of a dict and also
the convenience/safety of accessing properties of an object.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import anki.utils
from anki.tags import TagManager
from aqt import mw

from .ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from .morpheme import Morpheme


class AnkiDBRowData:
    __slots__ = (
        "card_id",
        "card_interval",
        "card_type",
        "note_id",
        "note_fields",
        "note_tags",
    )

    def __init__(self, data_row: Sequence[Any]) -> None:
        assert isinstance(data_row[0], int)
        self.card_id: int = data_row[0]

        assert isinstance(data_row[1], int)
        self.card_interval: int = data_row[1]

        assert isinstance(data_row[2], int)
        self.card_type: int = data_row[2]

        assert isinstance(data_row[4], int)
        self.note_id: int = data_row[4]

        assert isinstance(data_row[5], str)
        self.note_fields: str = data_row[5]

        assert isinstance(data_row[6], str)
        self.note_tags: str = data_row[6]


class AnkiCardData:  # pylint:disable=too-many-instance-attributes
    __slots__ = (
        "interval",
        "type",
        "expression",
        "automatically_known_tag",
        "manually_known_tag",
        "ready_tag",
        "not_ready_tag",
        "fields",
        "tags",
        "note_id",
        "morphs",
    )

    def __init__(
        self,
        am_config: AnkiMorphsConfig,
        config_filter: AnkiMorphsConfigFilter,
        tag_manager: TagManager,
        anki_row_data: AnkiDBRowData,
    ) -> None:
        assert config_filter.field_index is not None

        fields_list = anki.utils.split_fields(anki_row_data.note_fields)
        tags_list = tag_manager.split(anki_row_data.note_tags)

        expression_field = fields_list[config_filter.field_index]
        expression = anki.utils.strip_html(expression_field)

        automatically_known_tag = am_config.tag_known_automatically in tags_list
        manually_known_tag = am_config.tag_known_manually in tags_list
        ready_tag = am_config.tag_ready in tags_list
        not_ready_tag = am_config.tag_not_ready in tags_list

        self.interval = anki_row_data.card_interval
        self.type = anki_row_data.card_type
        self.expression = expression
        self.automatically_known_tag = automatically_known_tag
        self.manually_known_tag = manually_known_tag
        self.ready_tag = ready_tag
        self.not_ready_tag = not_ready_tag
        self.fields = anki_row_data.note_fields
        self.tags = anki_row_data.note_tags
        self.note_id = anki_row_data.note_id

        # this is set later when spacy is used
        self.morphs: set[Morpheme] | None = None


class AnkiMorphsCardData:
    __slots__ = (
        "card_id",
        "note_id",
        "note_type_id",
        "card_type",
        "fields",
        "tags",
    )

    def __init__(self, data_row: list[int | str]) -> None:
        assert isinstance(data_row[0], int)
        self.card_id: int = data_row[0]

        assert isinstance(data_row[1], int)
        self.note_id: int = data_row[1]

        assert isinstance(data_row[2], int)
        self.note_type_id: int = data_row[2]

        assert isinstance(data_row[3], int)
        self.card_type: int = data_row[3]

        assert isinstance(data_row[4], str)
        self.fields: str = data_row[4]

        assert isinstance(data_row[5], str)
        self.tags: str = data_row[5]


def create_card_data_dict(
    am_config: AnkiMorphsConfig,
    config_filter: AnkiMorphsConfigFilter,
) -> dict[int, AnkiCardData]:
    assert mw is not None

    tag_manager = TagManager(mw.col)
    tags: dict[str, str] = config_filter.tags
    model_id: int | None = config_filter.note_type_id
    card_data_dict: dict[int, AnkiCardData] = {}

    for anki_row_data in _get_anki_data(am_config, model_id, tags).values():
        card_data = AnkiCardData(am_config, config_filter, tag_manager, anki_row_data)
        card_data_dict[anki_row_data.card_id] = card_data

    return card_data_dict


def _get_anki_data(
    am_config: AnkiMorphsConfig, model_id: int | None, tags_object: dict[str, str]
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
