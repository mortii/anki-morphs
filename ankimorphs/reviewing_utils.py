from typing import Callable, Optional, Union

from anki.collection import UndoStatus
from anki.consts import CARD_TYPE_NEW
from anki.notes import Note
from aqt import mw
from aqt.qt import QKeySequence, QMessageBox, Qt  # pylint:disable=no-name-in-module
from aqt.reviewer import Reviewer
from aqt.utils import tooltip

from .ankimorphs_db import AnkiMorphsDB
from .browser_utils import browse_same_morphs
from .config import AnkiMorphsConfig, get_matching_modify_filter

SET_KNOWN_AND_SKIP_STRING = "Set known and skip"
ANKIMORPHS_UNDO_TARGET = "AnkiMorphs custom undo target"
set_known_and_skip_undo: Optional[UndoStatus] = None
valid_undo_merge_targets: set[str] = {  # a set has faster lookup than a list
    "Answer Card",
    "Bury",
    "Suspend",
    "Forget Card",
    "Set Due Date",
    "Delete Note",
}


def am_next_card(  # pylint:disable=too-many-branches,too-many-statements
    self: Reviewer, _old: Callable[[Reviewer], None]
) -> None:
    ################################################################
    #                          FREEZING
    ################################################################
    # We cannot run this on a background thread because it will
    # cause Anki to crash upon review completion. Anki also does
    # not support async operations (e.g. asyncio), therefore it is
    # unavoidable that the UI freezes if many cards are skipped.
    # The only thing we can do to alleviate the problem is to make
    # the algorithm more efficient.
    ################################################################
    ################################################################
    #                          UNDO/REDO
    ################################################################
    # We are making changes (burying, tagging) BEFORE the next card
    # is shown, that means the changes have to be merged into the
    # previous undo entry.
    #
    # If the current undo status has a 'redo' value it means the
    # user undid the previous operation and the undo stack is now
    # 'dirty', which means we cannot merge undo entries--you get
    # an error if you try.
    #
    # The new anki undo system only works on the v3 scheduler which
    # means we can stop supporting the v2 scheduler and just display
    # an error message if it is used.
    ################################################################

    assert mw is not None
    assert self is not None

    if self.mw.col.sched.version < 3:
        show_scheduler_version_error()
        self.mw.moveToState("overview")
        return

    undo_status = self.mw.col.undo_status()

    if undo_status.undo == SET_KNOWN_AND_SKIP_STRING:
        # The undo stack has been altered, so we cannot use
        # the normal 'last_step' as a merge point, we have
        # to use set_known_and_skip_undo last_step instead.
        # See comment in set_card_as_known_and_skip for more info
        assert set_known_and_skip_undo is not None
        undo_status = set_known_and_skip_undo
    elif undo_status.undo not in valid_undo_merge_targets:
        # We have to create a custom undo_targets that can be merged into.
        mw.col.add_custom_undo_entry(ANKIMORPHS_UNDO_TARGET)
        undo_status = self.mw.col.undo_status()

    am_config = AnkiMorphsConfig()
    skipped_cards = SkippedCards(am_config)
    am_db = AnkiMorphsDB()
    am_db.update_seen_unknown_morphs()

    while True:
        # If a break occurs in this loop it means 'show the card'
        # If a card makes it to the end it is buried and tagged as 'known'

        self.previous_card = self.card
        self.card = None
        self._v3 = None

        self._get_next_v3_card()

        self._previous_card_info.set_card(self.previous_card)
        self._card_info.set_card(self.card)

        if not self.card:
            self.mw.moveToState("overview")
            return

        if undo_status.redo != "":
            break  # The undo stack is dirty, we cannot merge undo entries.

        if self.card.type != CARD_TYPE_NEW:
            break

        note: Note = self.card.note()
        am_config_filter = get_matching_modify_filter(note)

        if am_config_filter is None:
            break  # card did not match note type and tags set in preferences GUI

        card_unknown_morphs: Optional[set[tuple[str, str]]] = am_db.get_morphs_of_card(
            self.card.id, search_unknowns=True
        )

        if card_unknown_morphs is None:
            break

        skip_card = skipped_cards.process_skip_conditions_of_card(
            am_db, note, card_unknown_morphs
        )

        if not skip_card:
            break

        self.mw.col.sched.buryCards([self.card.id], manual=False)
        self.mw.col.merge_undo_entries(undo_status.last_step)

    am_db.con.close()

    if self._reps is None:
        self._initWeb()

    self._showQuestion()

    if (
        skipped_cards.total_skipped_cards > 0
        and am_config.skip_show_num_of_skipped_cards
    ):
        skipped_cards.show_tooltip_of_skipped_cards()


def set_card_as_known_and_skip(self: Reviewer, am_config: AnkiMorphsConfig) -> None:
    ################################################################
    #                          KNOWN BUG
    ################################################################
    # When the 'set known and skip' is the only operation that
    # has taken place the user cannot undo it. If any manual
    # operation takes place before or after, e.g. answering a card,
    # THEN you can undo it...
    #
    # So for example if you start reviewing a deck, and you press
    # 'K' on the first card you see, it gets set as known and is
    # skipped. At that point you cannot undo. If you answer the
    # next card that is shown (or bury it or change it in any way)
    # you can now undo twice and the previous 'set known and skip'
    # will be undone.
    #
    # This is a weird bug, but I suspect it is due to some guards
    # Anki has about not being able to undo something until the user
    # has made a change manually first.
    ################################################################
    ################################################################
    #                     MERGING UNDO ENTRIES
    ################################################################
    # Every undo entry/undo status has a 'last_step' value. This
    # is an incremented value assigned when the operation is created.
    # When merging undo entries this is the value that is used as
    # a pointer/id to the undo entry.
    #
    # Let's say we have 3 undo entries:
    # first_entry: UndoState(undo='answered card', redo='', last_step=1)
    # second_entry: UndoState(undo='answered card', redo='', last_step=2)
    # third_entry: UndoState(undo='answered card', redo='', last_step=3)
    #
    # If we now merged the second and third entries into the first
    # entry, e.g. col.merge_undo_entries(1), we cannot later merge
    # entries into 2 or 3, because they don't 'exist' anymore. If we
    # want to merge into those then we need to merge into 1 instead.
    # This is why we need to store set_known_and_skip_undo as a global
    # variable--to keep track of where the entries were merged into,
    # so we can merge into this point later in am_next_card.
    ################################################################

    assert self.card is not None
    global set_known_and_skip_undo  # pylint:disable=global-statement

    note: Note = self.card.note()
    am_config_filter = get_matching_modify_filter(note)

    if am_config_filter is None:
        tooltip("Card does not match any note filter...")
        return

    if self.card.type != CARD_TYPE_NEW:
        tooltip("Card is not in the 'new'-queue")
        return

    self.mw.col.add_custom_undo_entry(SET_KNOWN_AND_SKIP_STRING)
    set_known_and_skip_undo = self.mw.col.undo_status()

    self.mw.col.sched.buryCards([self.card.id], manual=False)

    note = self.card.note()
    note.add_tag(am_config.tag_known)
    self.mw.col.update_note(note)

    self.mw.col.merge_undo_entries(set_known_and_skip_undo.last_step)

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


def show_scheduler_version_error() -> None:
    assert mw is not None

    title = "AnkiMorphs Error"
    text = (
        f"You are currently using the <b>V{mw.col.sched_ver()}</b> scheduler.<br>"
        f"AnkiMorphs only works on the V3 scheduler.<br>"
        f"To start using the V3 scheduler go to:<br>"
        f" Tools -> Preferences -> 'Review' tab -> Check 'V3 scheduler'"
    )
    critical_box = QMessageBox(mw)
    critical_box.setWindowTitle(title)
    critical_box.setIcon(QMessageBox.Icon.Critical)
    critical_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    critical_box.setText(text)
    critical_box.exec()


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
