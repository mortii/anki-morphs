from __future__ import annotations

from typing import Any

from anki.collection import Collection

from ankimorphs import ankimorphs_config
from ankimorphs.recalc import recalc_main


def recalc() -> None:
    recalc_main._recalc_background_op(
        read_enabled_config_filters=ankimorphs_config.get_read_enabled_filters(),
        modify_enabled_config_filters=ankimorphs_config.get_modify_enabled_filters(),
    )


def dump_collection(collection: Collection) -> list[Any]:
    dump: list[Any] = []
    for card_id in sorted(collection.find_cards("")):
        card = collection.get_card(card_id)
        note = card.note()
        dump.append(
            (
                card_id,
                card.due,
                card.queue,
                card.type,
                tuple(note.fields),
                tuple(sorted(note.tags)),
            )
        )
    return dump


def recalc_until_the_collection_stops_changing(collection: Collection) -> list[Any]:
    recalc()
    previous = dump_collection(collection)

    for _ in range(6):
        recalc()
        current = dump_collection(collection)
        if current == previous:
            return current
        previous = current

    raise AssertionError("recalc never reached a fixed point")
