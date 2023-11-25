from anki.notes import Note
from aqt import mw
from aqt.utils import tooltip

from .ankimorphs_db import AnkiMorphsDB
from .config import AnkiMorphsConfig


class SkippedCards:
    __slots__ = (
        "skipped_known_cards",
        "skipped_already_seen_morphs_cards",
        "total_skipped_cards",
        "did_skip_card",
    )

    def __init__(self) -> None:
        self.skipped_known_cards = 0
        self.skipped_already_seen_morphs_cards = 0
        self.total_skipped_cards = 0
        self.did_skip_card = False

    def process_skip_conditions_of_card(
        self,
        am_config: AnkiMorphsConfig,
        am_db: AnkiMorphsDB,
        note: Note,
        card_unknown_morphs_raw: set[tuple[str, str]],
    ) -> None:
        self.did_skip_card = False

        morphs_already_seen_morphs_today: set[str] = am_db.get_all_morphs_seen_today()

        card_unknown_morphs: set[str] = {
            morph_raw[0] + morph_raw[1] for morph_raw in card_unknown_morphs_raw
        }

        if note.has_tag("learn-now"):
            self.did_skip_card = False
        elif note.has_tag(am_config.tag_known):
            if am_config.skip_only_known_morphs_cards:
                self.skipped_known_cards += 1
                self.did_skip_card = True
        elif am_config.skip_unknown_morph_seen_today_cards:
            if card_unknown_morphs.issubset(morphs_already_seen_morphs_today):
                self.skipped_already_seen_morphs_cards += 1
                self.did_skip_card = True

        self.total_skipped_cards = (
            self.skipped_known_cards + self.skipped_already_seen_morphs_cards
        )

    def show_tooltip_of_skipped_cards(self) -> None:
        skipped_string = ""

        if self.skipped_known_cards > 0:
            skipped_string += f"Skipped <b>{self.skipped_known_cards}</b> stale cards"
        if self.skipped_already_seen_morphs_cards > 0:
            if skipped_string != "":
                skipped_string += "<br>"
            skipped_string += f"Skipped <b>{self.skipped_already_seen_morphs_cards}</b> cards with morphs already seen today"

        tooltip(skipped_string, parent=mw)
