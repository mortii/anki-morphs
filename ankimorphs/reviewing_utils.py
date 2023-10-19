from functools import partial
from typing import Callable, Optional, Union

from anki.collection import Collection
from anki.consts import CARD_TYPE_NEW
from anki.notes import Note
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QKeySequence, Qt  # pylint:disable=no-name-in-module
from aqt.reviewer import Reviewer
from aqt.utils import tooltip

from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.browser_utils import browse_same_morphs
from ankimorphs.config import AnkiMorphsConfig, get_matching_modify_filter


def mark_morph_seen(card_id: int) -> None:
    am_db = AnkiMorphsDB()
    am_db.insert_card_morphs_into_seen_table(card_id)
    # print("Seen_Morphs")
    # am_db.print_table("Seen_Morphs")
    am_db.con.close()


def am_next_card(self: Reviewer, _old: Callable[[], None]) -> None:
    """
    Since many cards can be skipped it's important to give feedback
    to the user and not just have a frozen UI, therefore we run the function
    as a QueryOp on a background thread and display a progress dialog.
    """

    operation = QueryOp(
        parent=self.mw,
        op=partial(next_card_background_op, self=self),
        success=lambda t: None,  # t = return value of the op
    )
    operation.with_progress().run_in_background()


def next_card_background_op(
    collection: Collection,
    self: Optional[Reviewer] = None,
) -> None:
    assert mw is not None
    assert self is not None

    am_config = AnkiMorphsConfig()
    skipped_cards = SkippedCards(am_config)
    am_db = AnkiMorphsDB()

    while True:
        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label=f"Skipping {skipped_cards.total_skipped_cards} cards",
            )
        )

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

        if self.card.type != CARD_TYPE_NEW:
            break  # ignore non-new cards

        note: Note = self.card.note()
        am_config_filter = get_matching_modify_filter(note)

        if am_config_filter is None:
            break  # card did not match note type and tags set in preferences GUI

        card_unknown_morphs: Optional[set[tuple[str, str]]] = am_db.get_morphs_of_card(
            self.card.id, search_unknowns=True
        )

        if card_unknown_morphs is None:
            break

        skipped_card = skipped_cards.process_skip_conditions_of_card(
            am_db, note, card_unknown_morphs
        )

        if not skipped_card:
            break  # card did not meet any skip criteria

        self.mw.col.sched.buryCards([self.card.id], manual=False)
        note.add_tag(am_config.tag_known)
        note.flush()

    am_db.con.close()

    if self._reps is None:
        self.mw.taskman.run_on_main(self._initWeb)

    self.mw.taskman.run_on_main(self._showQuestion)

    if (
        skipped_cards.total_skipped_cards > 0
        and am_config.skip_show_num_of_skipped_cards
    ):
        self.mw.taskman.run_on_main(skipped_cards.show_tooltip_of_skipped_cards)


def set_card_as_known_and_skip(self: Reviewer, am_config: AnkiMorphsConfig) -> None:
    assert self.card is not None

    # self.mw.checkpoint("Set already known focus morph")
    note = self.card.note()
    note.add_tag(am_config.tag_known)
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
    am_config = AnkiMorphsConfig()

    key_browse: QKeySequence = am_config.shortcut_browse_ready_same_unknown
    key_browse_non_vocab: QKeySequence = am_config.shortcut_browse_all_same_unknown
    key_skip: QKeySequence = am_config.shortcut_set_known_and_skip

    keys = _old(self)
    keys.extend(
        [
            (
                key_browse.toString(),
                lambda: browse_same_morphs(
                    self.card.id, self.card.note(), am_config, search_unknowns=True, search_ready_tag=True  # type: ignore[union-attr]
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
        self.skipped_cards_dict = {"comprehension": 0, "today": 0}
        self.total_skipped_cards = 0
        self.skip_comprehension = am_config.skip_stale_cards
        self.skip_focus_morph_seen_today = am_config.skip_unknown_morph_seen_today_cards

    def process_skip_conditions_of_card(
        self,
        am_db: AnkiMorphsDB,
        note: Note,
        card_unknown_morphs: set[tuple[str, str]],
    ) -> bool:
        is_comprehension_card = note.has_tag(self.am_config.tag_known)
        morphs_already_seen_morphs_today = am_db.get_all_morphs_seen_today()

        unknown_card_morphs_combined: set[str] = {
            morph[0] + morph[1] for morph in card_unknown_morphs
        }

        if is_comprehension_card:
            if self.skip_comprehension:
                self.skipped_cards_dict["comprehension"] += 1
                self.total_skipped_cards += 1
                return True
        elif self.skip_focus_morph_seen_today:
            if unknown_card_morphs_combined.issubset(morphs_already_seen_morphs_today):
                self.skipped_cards_dict["today"] += 1
                self.total_skipped_cards += 1
                return True
        return False

    def show_tooltip_of_skipped_cards(self) -> None:
        skipped_string = ""

        if self.skipped_cards_dict["comprehension"] > 0:
            skipped_string += (
                f"Skipped <b>{self.skipped_cards_dict['comprehension']}</b> stale cards"
            )
        if self.skipped_cards_dict["today"] > 0:
            if skipped_string != "":
                skipped_string += "<br>"
            skipped_string += f"Skipped <b>{self.skipped_cards_dict['today']}</b> cards with morphs already seen today"

        tooltip(skipped_string, parent=mw)
