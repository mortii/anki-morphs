from __future__ import annotations

from functools import partial
from typing import Any, Callable

from anki.cards import Card
from anki.collection import Collection, UndoStatus
from anki.consts import CARD_TYPE_NEW
from anki.notes import Note
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QKeySequence, QMessageBox, Qt  # pylint:disable=no-name-in-module
from aqt.reviewer import Reviewer
from aqt.utils import tooltip

from . import ankimorphs_config
from .ankimorphs_config import AnkiMorphsConfig
from .ankimorphs_db import AnkiMorphsDB
from .browser_utils import browse_same_morphs
from .exceptions import CancelledOperationException, CardQueueEmptyException

SET_KNOWN_AND_SKIP_UNDO = "Set known and skip"
ANKIMORPHS_UNDO = "AnkiMorphs custom undo"
VALID_UNDO_MERGE_TARGETS: set[str] = {  # a set has faster lookup than a list
    "Answer Card",
    "Bury",
    "Suspend",
    "Forget Card",
    "Set Due Date",
    "Delete Note",
}
set_known_and_skip_undo: UndoStatus | None = None


def am_next_card() -> None:
    ################################################################
    #                          FREEZING
    ################################################################
    # A lot of cards might be skipped, so to prevent Anki from
    # freezing we have to run this on a background thread by using
    # QueryOp.
    ################################################################

    assert mw is not None
    assert mw.reviewer is not None

    if mw.col.sched.version < 3:
        _show_scheduler_version_error()
        mw.moveToState("overview")
        return

    am_config = AnkiMorphsConfig()
    skipped_cards = SkippedCards()

    operation = QueryOp(
        parent=mw,
        op=partial(
            _get_next_card_background,
            am_config=am_config,
            skipped_cards=skipped_cards,
        ),
        success=partial(_show_card, am_config=am_config, skipped_cards=skipped_cards),
    )
    operation.failure(_on_failure)
    operation.with_progress().run_in_background()


def _get_next_card_background(
    collection: Collection,
    am_config: AnkiMorphsConfig,
    skipped_cards: SkippedCards,
) -> None:
    del collection  # unused

    assert mw is not None
    assert mw.reviewer is not None

    reviewer: Reviewer = mw.reviewer
    undo_status = _get_valid_undo_status()
    am_db = AnkiMorphsDB()

    while True:
        # If a break occurs in this loop it means 'show the card'
        # If a card makes it to the end it is buried/skipped

        if mw.progress.want_cancel():  # user clicked 'x'
            raise CancelledOperationException

        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label=f"Skipping {skipped_cards.total_skipped_cards} cards",
            )
        )

        reviewer.previous_card = reviewer.card
        reviewer.card = None
        reviewer._v3 = None

        reviewer._get_next_v3_card()
        reviewer._previous_card_info.set_card(reviewer.previous_card)

        # the _card_info.set_card function updates the card info window (gui)
        # if it is open, which you can't do in a background thread (it crashes),
        # so we have to run the function on the main thread
        mw.taskman.run_on_main(partial(reviewer._card_info.set_card, reviewer.card))

        if not reviewer.card:
            raise CardQueueEmptyException  # handled in _on_failure()

        if undo_status.redo != "":
            break  # The undo stack is dirty, we cannot merge undo entries.

        if reviewer.card.type != CARD_TYPE_NEW:
            break

        note: Note = reviewer.card.note()
        am_config_filter = ankimorphs_config.get_matching_modify_filter(note)

        if am_config_filter is None:
            break  # card did not match any (note type and tags) set in the settings GUI

        skipped_cards.process_skip_conditions_of_card(
            am_config, am_db, note=note, card_id=reviewer.card.id
        )

        if not skipped_cards.did_skip_card:
            break

        mw.col.sched.buryCards([reviewer.card.id], manual=False)
        mw.col.merge_undo_entries(undo_status.last_step)

    am_db.con.close()


def _get_valid_undo_status() -> UndoStatus:
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

    undo_status = mw.col.undo_status()

    if undo_status.undo == SET_KNOWN_AND_SKIP_UNDO:
        # The undo stack has been altered, so we cannot use
        # the normal 'last_step' as a merge point, we have
        # to use set_known_and_skip_undo last_step instead.
        # See comment in set_card_as_known_and_skip for more info
        assert set_known_and_skip_undo is not None
        undo_status = set_known_and_skip_undo
    elif undo_status.undo not in VALID_UNDO_MERGE_TARGETS:
        # We have to create a custom undo_targets that can be merged into.
        mw.col.add_custom_undo_entry(ANKIMORPHS_UNDO)
        undo_status = mw.col.undo_status()

    return undo_status


def _show_card(
    result: Any,
    am_config: AnkiMorphsConfig,
    skipped_cards: SkippedCards,
) -> None:
    # this function runs on the main thread
    del result  # unused

    assert mw is not None
    assert mw.reviewer is not None

    # The lifecycle of the reviewer and its properties
    # are somewhat mysterious and inconsistent, so using
    # normal 'is None' checks are not enough to prevent
    # runtime errors. We therefore have to use try catch
    # and just silently ignore the errors, everything
    # usually works regardless, so it's just noise.
    try:
        if mw.reviewer._reps is None:
            mw.reviewer._initWeb()
        mw.reviewer._showQuestion()

    except AttributeError:
        # This triggers on NoneType exceptions.
        # On Reviewer.cleanup() the card is set to None.
        # Usually a new reviewer object will take over,
        # so everything should still work, and we can just
        # ignore the error.
        print("AnkiMorphs: mw.reviewer.card is None!")

    if am_config.skip_show_num_of_skipped_cards:
        if skipped_cards.total_skipped_cards > 0:
            skipped_cards.show_tooltip_of_skipped_cards()


def _set_card_as_known_and_skip(am_config: AnkiMorphsConfig) -> None:
    ################################################################
    #                          KNOWN BUG
    ################################################################
    # When the 'set known and skip' is the only operation that
    # has taken place the user cannot undo it. If any manual
    # operation takes place before or after, e.g. answering a card,
    # THEN you can undo it...
    #
    # So for example, if you start reviewing a deck, and you press
    # 'K' on the first card you see, it gets set as known and is
    # skipped. At that point, you cannot undo. If you answer the
    # next card that is shown (or bury it or change it in any way),
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
    # When merging undo entries, this is the value that is used as
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
    # want to merge into those, then we need to merge into 1 instead.
    # This is why we need to store set_known_and_skip_undo as a global
    # variable--to keep track of where the entries were merged into,
    # so we can merge into this point later in am_next_card.
    ################################################################
    global set_known_and_skip_undo

    assert mw is not None
    assert mw.reviewer is not None
    assert mw.reviewer.card is not None

    card: Card = mw.reviewer.card
    note: Note = card.note()
    am_config_filter = ankimorphs_config.get_matching_modify_filter(note)

    if am_config_filter is None:
        tooltip("Card does not match any note filter...")
        return

    if card.type != CARD_TYPE_NEW:
        tooltip("Card is not in the 'new'-queue")
        return

    mw.col.add_custom_undo_entry(SET_KNOWN_AND_SKIP_UNDO)
    set_known_and_skip_undo = mw.col.undo_status()

    mw.col.sched.buryCards([card.id], manual=False)

    note.add_tag(am_config.tag_known_manually)
    mw.col.update_note(note)

    mw.col.merge_undo_entries(set_known_and_skip_undo.last_step)

    # update seen morphs table with this card's morphs
    am_db = AnkiMorphsDB()
    am_db.update_seen_morphs_today_single_card(card.id)
    am_db.con.close()

    if am_config.skip_show_num_of_skipped_cards:
        tooltip("Set card as known and skipped")

    mw.reviewer.nextCard()


def am_reviewer_shortcut_keys(
    self: Reviewer,
    _old: Callable[
        [Reviewer],
        list[tuple[str, Callable[[], None]] | tuple[Qt.Key, Callable[[], None]]],
    ],
) -> list[tuple[str, Callable[[], None]] | tuple[Qt.Key, Callable[[], None]]]:
    am_config = AnkiMorphsConfig()

    key_browse_ready: QKeySequence = am_config.shortcut_browse_ready_same_unknown
    key_browse_ready_lemma: QKeySequence = (
        am_config.shortcut_browse_ready_same_unknown_lemma
    )
    key_browse_all: QKeySequence = am_config.shortcut_browse_all_same_unknown
    key_skip: QKeySequence = am_config.shortcut_set_known_and_skip

    keys = _old(self)
    keys.extend(
        [
            (
                key_browse_ready.toString(),
                lambda: browse_same_morphs(
                    am_config, search_unknowns=True, search_ready_tag=True
                ),
            ),
            (
                key_browse_ready_lemma.toString(),
                lambda: browse_same_morphs(
                    am_config,
                    search_unknowns=True,
                    search_ready_tag=True,
                    search_lemma_only=True,
                ),
            ),
            (
                key_browse_all.toString(),
                lambda: browse_same_morphs(am_config, search_unknowns=True),
            ),
            (key_skip.toString(), lambda: _set_card_as_known_and_skip(am_config)),
        ]
    )
    return keys


def _show_scheduler_version_error() -> None:
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


def _on_failure(
    error: Exception | CardQueueEmptyException | CancelledOperationException,
) -> None:
    # This function runs on the main thread.
    assert mw is not None
    assert mw.progress is not None
    mw.progress.finish()

    if isinstance(error, CardQueueEmptyException):
        mw.moveToState("overview")
    elif isinstance(error, CancelledOperationException):
        tooltip("Cancelled get_next_card")
        mw.moveToState("overview")
    else:
        raise error


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
        card_id: int,
    ) -> None:
        self.did_skip_card = False

        learn_now_tag: bool = note.has_tag(am_config.tag_learn_card_now)
        known_automatically: bool = note.has_tag(am_config.tag_known_automatically)
        known_manually: bool = note.has_tag(am_config.tag_known_manually)
        known_tag: bool = known_automatically or known_manually

        if learn_now_tag:
            self.did_skip_card = False
        elif known_tag:
            if am_config.skip_only_known_morphs_cards:
                self.skipped_known_cards += 1
                self.did_skip_card = True
        elif am_config.skip_unknown_morph_seen_today_cards:
            morphs_already_seen_morphs_today: set[str] = (
                am_db.get_all_morphs_seen_today(
                    only_lemma=am_config.algorithm_lemma_priority
                )
            )
            card_unknown_morphs_raw: set[tuple[str, str]] | None = (
                am_db.get_card_morphs(
                    card_id,
                    search_unknowns=True,
                    only_lemma=am_config.algorithm_lemma_priority,
                )
            )
            # print(
            #     f"morphs_already_seen_morphs_today: {morphs_already_seen_morphs_today}"
            # )
            # print(f"card_unknown_morphs_raw: {card_unknown_morphs_raw}")

            if card_unknown_morphs_raw is not None:
                card_unknown_morphs: set[str] = {
                    morph_raw[0] + morph_raw[1] for morph_raw in card_unknown_morphs_raw
                }
                if card_unknown_morphs.issubset(morphs_already_seen_morphs_today):
                    self.skipped_already_seen_morphs_cards += 1
                    self.did_skip_card = True

        self.total_skipped_cards = (
            self.skipped_known_cards + self.skipped_already_seen_morphs_cards
        )

    def show_tooltip_of_skipped_cards(self) -> None:
        skipped_string = ""

        if self.skipped_known_cards > 0:
            skipped_string += f"Skipped <b>{self.skipped_known_cards}</b> cards with only known morphs"
        if self.skipped_already_seen_morphs_cards > 0:
            if skipped_string != "":
                skipped_string += "<br>"
            skipped_string += f"Skipped <b>{self.skipped_already_seen_morphs_cards}</b> cards with morphs already seen today"

        tooltip(skipped_string, parent=mw)
