from typing import Optional

from anki.utils import strip_html

from aqt.reviewer import RefreshNeeded
from aqt import mw
from aqt.utils import tooltip
from aqt.browser import Browser

from . import util
from .preferences import get_preference
from .morphemes import getMorphemes, ms2str
from .reviewing_utils import try_to_get_focus_morphs, focus_query
from .morphemizer import getMorphemizerByName

browser: Optional[Browser] = None


def run_browse_morph() -> None:
    run_browse_morph_dict = dict({"focusMorphs": set()})

    for cid in browser.selectedCards():
        card = mw.col.get_card(cid)
        note = card.note()

        for focusMorph in try_to_get_focus_morphs(note):
            run_browse_morph_dict["focusMorphs"].add(focusMorph)

        focus_field = get_preference("Field_FocusMorph")
        focus_morphs = run_browse_morph_dict["focusMorphs"]

        query = focus_query(focus_field, focus_morphs)
        if query != "":
            browser.form.searchEdit.lineEdit().setText(query)
            browser.onSearchActivated()
            tooltip(f"Browsing {(len(focus_morphs))} morphs")

        return  # Only use one card since note-types can be different


def run_already_known_tagger():
    known_tag = get_preference("Tag_AlreadyKnown")
    selected_cards = browser.selectedCards()

    for cid in selected_cards:
        card = mw.col.get_card(cid)
        note = card.note()
        note.add_tag(known_tag)
        note.flush()

    tooltip(f"{len(selected_cards)} notes given the {known_tag} tag")


def run_learn_card_now() -> None:
    selected_cards = browser.selectedCards()

    for cid in selected_cards:
        card = mw.col.get_card(cid)
        card.due = 0
        mw.col.update_card(card)

    mw.moveToState("review")
    mw.activateWindow()
    mw.reviewer._refresh_needed = RefreshNeeded.QUEUES
    mw.reviewer.refresh_if_needed()

    tooltip(f"Next new card(s) will be {selected_cards}")


def run_view_morphs() -> None:
    morph_dict = dict({"morphemes": []})

    for cid in browser.selectedCards():
        card = mw.col.get_card(cid)
        note = card.note()

        notecfg = util.get_filter(note)
        if notecfg is None:
            return None

        morphemizer = getMorphemizerByName(notecfg["Morphemizer"])

        for note_filter_field in notecfg["Fields"]:
            morphemes = getMorphemes(
                morphemizer, strip_html(note[note_filter_field]), note.tags
            )
            morph_dict["morphemes"] += morphemes

        if len(morph_dict["morphemes"]) == 0:
            util.infoMsg("----- No morphemes, check your filters -----")
        else:
            morph_strings = ms2str([(m, []) for m in morph_dict["morphemes"]])
            util.infoMsg("----- All -----\n" + morph_strings)
