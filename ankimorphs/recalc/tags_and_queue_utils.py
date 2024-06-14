from anki.cards import Card
from anki.consts import CardQueue
from anki.notes import Note

from ..ankimorphs_config import AnkiMorphsConfig


def update_tags_and_queue(
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
