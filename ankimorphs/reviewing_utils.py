# import codecs
from typing import Callable, Union

from anki.consts import CARD_TYPE_NEW
from anki.notes import Note
from aqt.qt import QKeySequence, Qt  # pylint:disable=no-name-in-module
from aqt.reviewer import Reviewer
from aqt.utils import tooltip

from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.browser_utils import browse_same_morphs
from ankimorphs.config import AnkiMorphsConfig, get_matching_modify_filter

# from ankimorphs import text_utils


# def get_focus_morphs(
#     am_config_filter: AnkiMorphsConfigFilter, note: Note
# ) -> Optional[list[str]]:
#     try:
#         focus_value = note[am_config_filter.focus_morph].strip()
#         if focus_value == "":
#             return []
#         return [f.strip() for f in focus_value.split(",")]
#     except KeyError:
#         return None


def mark_morph_seen(card_id: int) -> None:
    am_db = AnkiMorphsDB()
    am_db.insert_card_morphs_into_seen_table(card_id)
    print("Seen_Morphss")
    am_db.print_table("Seen_Morph")
    am_db.con.close()


def am_next_card(self: Reviewer, _old: Callable[[], None]) -> None:
    am_db = AnkiMorphsDB()
    am_config = AnkiMorphsConfig()
    skipped_cards = SkippedCards(am_config)

    print("entered my_next_card")

    while True:
        print("while True")

        self.previous_card = self.card
        self.card = None
        self._v3 = None

        if self.mw.col.sched.version < 3:
            self.mw.col.reset()  # rebuilds the queue
            self._get_next_v1_v2_card()
        else:
            self._get_next_v3_card()

        self._previous_card_info.set_card(self.previous_card)
        self._card_info.set_card(self.card)

        if not self.card:
            self.mw.moveToState("overview")
            return

        print(f"self.card.id: {self.card.id}, self.card.due: {self.card.due}")
        # pprint.pprint(vars(self.card))

        if self.card.type != CARD_TYPE_NEW:
            break  # ignore non-new cards

        note: Note = self.card.note()
        am_config_filter = get_matching_modify_filter(note)

        if am_config_filter is None:
            break  # card did not match (note type and tags) set in preferences GUI

        card_morphs: set[str] = am_db.get_card_morphs(self.card.id)
        print(f"card_morphs: {card_morphs}")

        skipped_card = skipped_cards.process_skip_conditions_of_card(
            am_db, note, card_morphs
        )

        if not skipped_card:
            break  # card did not meet any skip criteria

        self.mw.col.sched.buryCards([self.card.id], manual=False)

    am_db.con.close()

    if self._reps is None:
        self._initWeb()

    self._showQuestion()

    if (
        skipped_cards.skipped_at_least_one_card()
        and am_config.skip_show_num_of_skipped_cards
    ):
        skipped_cards.show_tooltip_of_skipped_cards()


def set_card_as_known_and_skip(self: Reviewer, am_config: AnkiMorphsConfig) -> None:
    assert self.card is not None

    self.mw.checkpoint("Set already known focus morph")
    note = self.card.note()
    note.add_tag(am_config.tag_stale)
    note.flush()
    mark_morph_seen(self.card.id)
    self.mw.col.sched.buryCards([self.card.id], manual=False)
    self.mw.col.reset()  # recomputes the "new card"-queue

    if am_config.skip_show_num_of_skipped_cards:
        tooltip("Set card as known and skipped")
    self.nextCard()


def am_reviewer_shortcut_keys(
    self: Reviewer,
    _old: Callable[
        [Reviewer],
        list[Union[tuple[str, Callable[[], None]], tuple[Qt.Key, Callable[[], None]]]],
    ],
) -> list[Union[tuple[str, Callable[[], None]], tuple[Qt.Key, Callable[[], None]]]]:
    # assert self.card

    am_config = AnkiMorphsConfig()

    key_browse: QKeySequence = am_config.shortcut_browse_same_unknown_ripe
    key_browse_non_vocab: QKeySequence = (
        am_config.shortcut_browse_same_unknown_ripe_budding
    )
    key_skip: QKeySequence = am_config.shortcut_set_known_and_skip

    keys = _old(self)
    keys.extend(
        [
            (
                key_browse.toString(),
                lambda: browse_same_morphs(
                    self.card.id, self.card.note(), am_config, search_unknowns=True, search_ripe_tag=True  # type: ignore[union-attr]
                ),
            ),
            (
                key_browse_non_vocab.toString(),
                lambda: browse_same_morphs(
                    self.card.id, self.card.note(), am_config, search_unknowns=True  # type: ignore[union-attr]
                ),
            ),
            (key_skip.toString(), lambda: set_card_as_known_and_skip(self, am_config)),
        ]
    )
    return keys


# def am_highlight(  # pylint:disable=too-many-locals
#     txt: str, field, note_filter: str, ctx
# ) -> str:
#     """When a field is marked with the 'focusMorph' command, we format it by
#     wrapping all the morphemes in <span>s with attributes set to its maturity"""

# if note_filter != "morphHighlight":
#     return txt
#
# frequency_list_path = get_preference("path_frequency")
# try:
#     with codecs.open(frequency_list_path, encoding="utf-8") as file:
#         frequency_list = [line.strip().split("\t")[0] for line in file.readlines()]
# except FileNotFoundError:
#     frequency_list = []
#
# note = ctx.note()
# tags = note.string_tags()
#
# note_filter = get_filter(note)
# if note_filter is None:
#     return txt
#
# morphemizer = get_morphemizer_by_name(note_filter["Morphemizer"])
# if morphemizer is None:
#     return txt
#
# proper_nouns_known = get_preference("Option_ProperNounsAlreadyKnown")
#
# # TODO: store these somewhere fitting to avoid instantiating them every function call
# known_db = MorphDb(path=get_preference("path_known"))
# mature_db = MorphDb(path=get_preference("path_mature"))
# priority_db = MorphDb(get_preference("path_priority"), ignore_errors=True).db
#
# morphemes = get_morphemes(morphemizer, txt, tags)
#
# # Avoid formatting a smaller morph that is contained in a bigger morph, reverse sort fixes this
# sorted_morphs = sorted(morphemes, key=lambda x: len(x.inflected), reverse=True)
#
# for morph in sorted_morphs:
#     if proper_nouns_known and morph.is_proper_noun():
#         maturity = "none"
#     elif mature_db.matches(morph):
#         maturity = "mature"
#     elif known_db.matches(morph):  # TODO: fix knowndb...
#         maturity = "unmature"
#     else:
#         maturity = "unknown"
#
#     priority = "true" if morph in priority_db else "false"
#
#     focus_morph_string = morph.show().split()[0]
#     frequency = "true" if focus_morph_string in frequency_list else "false"
#
#     replacement = f'<span class="morphHighlight" mtype="{maturity}" priority="{priority}" frequency="{frequency}"">\\1</span>'
#     txt = text_utils.non_span_sub(f"({morph.inflected})", replacement, txt)

# return txt


class SkippedCards:
    def __init__(self, am_config: AnkiMorphsConfig) -> None:
        self.am_config = am_config
        self.skipped_cards = {"comprehension": 0, "today": 0}
        self.skip_comprehension = am_config.skip_stale_cards
        self.skip_focus_morph_seen_today = am_config.skip_unknown_morph_seen_today_cards

    def process_skip_conditions_of_card(
        self, am_db: AnkiMorphsDB, note: Note, card_morphs: set[str]
    ) -> bool:
        is_comprehension_card = note.has_tag(self.am_config.tag_stale)
        morphs_already_seen_morphs_today = am_db.get_all_morphs_seen_today()

        if is_comprehension_card:
            if self.skip_comprehension:
                self.skipped_cards["comprehension"] += 1
                return True

        if self.skip_focus_morph_seen_today:
            if card_morphs.issubset(morphs_already_seen_morphs_today):
                self.skipped_cards["today"] += 1
                return True
        return False

    def skipped_at_least_one_card(self) -> bool:
        for value in self.skipped_cards.values():
            if value > 0:
                return True
        return False

    def show_tooltip_of_skipped_cards(self) -> None:
        skipped_string = ""

        if self.skipped_cards["comprehension"] > 0:
            skipped_string += (
                f"Skipped <b>{self.skipped_cards['comprehension']}</b> stale cards"
            )
        if self.skipped_cards["today"] > 0:
            if skipped_string != "":
                skipped_string += "<br>"
            skipped_string += f"Skipped <b>{self.skipped_cards['today']}</b> morph already seen today cards"

        tooltip(skipped_string)
