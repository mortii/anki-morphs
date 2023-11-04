from typing import Optional

from anki.collection import SearchNode
from anki.notes import Note
from anki.utils import ids2str
from aqt import dialogs, mw
from aqt.browser.browser import Browser
from aqt.browser.table.state import ItemState
from aqt.qt import QLineEdit, QMessageBox  # pylint:disable=no-name-in-module
from aqt.reviewer import RefreshNeeded
from aqt.utils import tooltip
from .ankimorphs_db import AnkiMorphsDB
from .config import AnkiMorphsConfig, AnkiMorphsConfigFilter, get_matching_read_filter

browser: Optional[Browser] = None


def run_browse_morph(search_unknowns: bool = False) -> None:
    assert mw is not None
    assert browser is not None

    am_config = AnkiMorphsConfig()

    for cid in browser.selectedCards():
        card = mw.col.get_card(cid)
        note = card.note()
        browse_same_morphs(cid, note, am_config, search_unknowns=search_unknowns)
        return  # Only use one card since note-types can be different


def browse_same_morphs(
    card_id: int,
    note: Note,
    am_config: AnkiMorphsConfig,
    search_unknowns: bool = False,
    search_ready_tag: bool = False,
) -> None:
    # Opens browser and displays all notes with the same focus morph.
    # Useful to quickly find alternative notes to learn focus from.
    #
    # The query is a list of card ids. This might seem unnecessarily complicated, but
    # if we were to only query the text on the cards themselves we can get false positives
    # because inflected morphs with different bases can be identical to each-other.

    global browser

    am_db = AnkiMorphsDB()
    am_filter = get_matching_read_filter(note)

    if am_filter is None:
        tooltip(
            "Card's note type is either not configured in settings, or does not have 'Modify' checked"
        )
        return

    card_ids: Optional[set[int]]
    if search_unknowns:
        card_ids = am_db.get_ids_of_cards_with_same_morphs(card_id, search_unknowns)
        error_text = "No unknown morphs"
    else:
        card_ids = am_db.get_ids_of_cards_with_same_morphs(card_id)
        error_text = "No morphs"

    if card_ids is None:
        tooltip(error_text)
        return

    query = focus_query(am_config, card_ids, search_ready_tag)
    browser = dialogs.open("Browser", mw)
    assert browser is not None

    search_edit: Optional[QLineEdit] = browser.form.searchEdit.lineEdit()
    assert search_edit is not None

    search_edit.setText(query)
    browser.onSearchActivated()


def focus_query(
    am_config: AnkiMorphsConfig,
    card_ids: set[int],
    ready_tag: bool = False,
) -> Optional[str]:
    assert mw is not None

    if len(card_ids) == 0:
        return None

    query = "cid:" + "".join([f"{card_id}," for card_id in card_ids])
    query = query[:-1]  # removes the last comma

    if ready_tag:
        # we can escape characters like underscore in tags by using SearchNode
        query += " " + mw.col.build_search_string(SearchNode(tag=am_config.tag_ready))

    return query


def run_already_known_tagger() -> None:
    assert mw is not None
    assert browser is not None

    am_config = AnkiMorphsConfig()

    known_tag = am_config.tag_known
    selected_cards = browser.selectedCards()

    for cid in selected_cards:
        card = mw.col.get_card(cid)
        note = card.note()
        note.add_tag(known_tag)
        mw.col.update_note(note)

    tooltip(f"{len(selected_cards)} notes given the {known_tag} tag")


def run_learn_card_now() -> None:
    assert mw is not None
    assert mw.col.db is not None
    assert browser is not None

    selected_cards = browser.selectedCards()
    note_ids = mw.col.db.list(
        f"select distinct nid from cards where id in {ids2str(selected_cards)}"
    )
    mw.col.tags.bulk_add(note_ids, "learn-now")

    mw.col.sched.reposition_new_cards(selected_cards, 0, 1, False, True)
    mw.moveToState("review")
    mw.activateWindow()
    mw.reviewer._refresh_needed = RefreshNeeded.QUEUES
    mw.reviewer.refresh_if_needed()

    tooltip(f"Next new card(s) will be {selected_cards}")


def run_view_morphs() -> None:
    assert mw is not None
    assert browser is not None

    am_db = AnkiMorphsDB()

    for cid in browser.selectedCards():
        card = mw.col.get_card(cid)
        note = card.note()

        am_config_filter: Optional[AnkiMorphsConfigFilter] = get_matching_read_filter(
            note
        )
        if am_config_filter is None:
            tooltip("Card does not match any 'Note Filters' that has 'Read' enabled")
            return

        morphs: list[tuple[str, str]] = am_db.get_readable_card_morphs(cid)

        if len(morphs) == 0:
            tooltip("No morphs found")
        else:
            title = "AnkiMorphs: Card Morphs"
            text = "".join(
                [f"inflection: {morph[1]}, base: {morph[0]} \n" for morph in morphs]
            )
            info_box = QMessageBox(browser)
            info_box.setWindowTitle(title)
            info_box.setIcon(QMessageBox.Icon.Information)
            info_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            info_box.setText(text)
            info_box.exec()
