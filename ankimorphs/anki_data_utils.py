"""
By using a class with slots we get the speed of a dict and also
the convenience/safety of accessing properties of an object.
"""


from collections.abc import Sequence
from typing import Any, Optional, Union

import anki.utils
from anki.tags import TagManager

from .config import AnkiMorphsConfig, AnkiMorphsConfigFilter
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
        self.morphs: Optional[list[Morpheme]] = None


class AnkiMorphsCardData:
    __slots__ = (
        "card_id",
        "note_id",
        "note_type_id",
        "card_type",
        "fields",
        "tags",
    )

    def __init__(self, data_row: list[Union[int, str]]) -> None:
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
