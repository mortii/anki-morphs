from collections.abc import Sequence

from anki.cards import Card
from anki.consts import CardQueue
from anki.notes import Note, NoteId
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QWidget  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from . import progress_utils
from .ankimorphs_config import AnkiMorphsConfig


def update_tags_and_queue_of_new_cards(
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

    if has_learning_morphs:
        if am_config.tag_fresh not in note.tags:
            note.tags.append(am_config.tag_fresh)
    else:
        if am_config.tag_fresh in note.tags:
            note.tags.remove(am_config.tag_fresh)

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


def update_tags_of_review_cards(
    am_config: AnkiMorphsConfig,
    note: Note,
    has_learning_morphs: bool,
) -> None:
    if am_config.tag_ready in note.tags:
        note.tags.remove(am_config.tag_ready)
    elif am_config.tag_not_ready in note.tags:
        note.tags.remove(am_config.tag_not_ready)

    if has_learning_morphs:
        if am_config.tag_fresh not in note.tags:
            note.tags.append(am_config.tag_fresh)
    else:
        if am_config.tag_fresh in note.tags:
            note.tags.remove(am_config.tag_fresh)


def reset_am_tags(parent: QWidget) -> None:
    assert mw is not None

    # lambda is used to ignore the irrelevant arguments given by QueryOp
    operation = QueryOp(
        parent=parent,
        op=lambda _: _reset_am_tags_background_op(),
        success=lambda _: tooltip(msg="Successfully removed tags", parent=parent),
    )
    operation.with_progress().run_in_background()


def _reset_am_tags_background_op() -> None:
    assert mw is not None

    am_config = AnkiMorphsConfig()
    modified_notes: dict[NoteId, Note] = {}

    tags_to_remove = [
        am_config.tag_known_automatically,
        am_config.tag_ready,
        am_config.tag_not_ready,
        am_config.tag_fresh,
    ]
    for tag in tags_to_remove:
        note_ids: Sequence[NoteId] = mw.col.find_notes(f"tag:{tag}")
        note_amount = len(note_ids)

        for counter, note_id in enumerate(note_ids):
            progress_utils.background_update_progress_potentially_cancel(
                label=f"Removing {tag} tag from notes<br>note: {counter} of {note_amount}",
                counter=counter,
                max_value=note_amount,
                increment=100,
            )
            note: Note = modified_notes.get(note_id, mw.col.get_note(note_id))
            note.tags.remove(tag)
            modified_notes[note_id] = note

    mw.col.update_notes(list(modified_notes.values()))
