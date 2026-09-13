from __future__ import annotations

import hashlib
import json

from ..ankimorphs_config import AnkiMorphsConfigFilter

NoteSourceKey = tuple[int, str]


def make_source_key(config_filter: AnkiMorphsConfigFilter) -> str:
    encoded = json.dumps(
        [
            config_filter.note_type,
            config_filter.field,
            config_filter.morphemizer_description,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.blake2b(encoded, digest_size=16).hexdigest()


def get_expression_hash(source_key: str, expression: str) -> int:
    encoded = source_key.encode("ascii") + b"\0" + expression.encode("utf-8")
    return int.from_bytes(
        hashlib.blake2b(encoded, digest_size=8).digest(),
        byteorder="big",
        signed=True,
    )
