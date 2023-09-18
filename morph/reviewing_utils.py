# -*- coding: utf-8 -*-
import codecs
import re
from typing import List, Optional

from aqt import dialogs
from aqt.reviewer import Reviewer
from aqt.utils import tooltip

from anki.notes import Note
from anki.consts import CARD_TYPE_NEW

from . import text_utils
from .util import get_filter
from .preferences import get_preference

from .morphemizer import getMorphemizerByName
from .morphemes import MorphDb, getMorphemes

seen_morphs = set()  # TODO: use the db instead


def try_to_get_focus_morphs(note: Note) -> Optional[List[str]]:
    try:
        focus_value = note[get_preference('Field_FocusMorph')].strip()
        if focus_value == '':
            return []
        return [f.strip() for f in focus_value.split(',')]
    except KeyError:
        return None


def focus_query(field_name, focus_morphs, vocab_tag=False):
    query = ' or '.join([r'"%s:re:(^|,|\s)%s($|,|\s)"' % (field_name, re.escape(morph)) for morph in focus_morphs])
    if len(focus_morphs) > 0:
        query = '(%s)' % query
    if vocab_tag:
        query += f"tag:{get_preference('Tag_Vocab')}"
    return query


def mark_morph_seen(note: Note) -> None:
    focus_morphs = try_to_get_focus_morphs(note)

    if focus_morphs is not None and len(focus_morphs) > 0:
        seen_morphs.update(focus_morphs)


def my_next_card(self: Reviewer, _old) -> None:
    skipped_cards = SkippedCards()

    print(f"startes Reviewer {Reviewer}")

    while True:
        self.previous_card = self.card
        self.card = None
        self._v3 = None

        print(f"self.mw.col.sched.version99: {self.mw.col.sched.version}")

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
        note_filter = get_filter(note)  # Note filters from preferences GUI

        if note_filter is None:
            break  # card did not match (note type and tags) set in preferences GUI

        if not note_filter['Modify']:
            break  # modify is not set in preferences GUI

        focus_morphs = try_to_get_focus_morphs(note)

        if focus_morphs is None:
            tooltip(
                ('Encountered card without the \'focus morph\' field configured in the preferences. Please check '
                 'your MorphMan settings and note models.'))
            break

        skipped_card = skipped_cards.process_skip_conditions_of_card(note, focus_morphs)

        if not skipped_card:
            break  # card did not meet any skip criteria

        self.mw.col.sched.buryCards([self.card.id], manual=False)

    if self._reps is None:
        self._initWeb()

    self._showQuestion()

    # TODO: add option to preferences GUI
    if skipped_cards.skipped_at_least_one_card() and get_preference('print number of alternatives skipped'):
        skipped_cards.show_tooltip_of_skipped_cards()


def set_known_and_skip(self: Reviewer) -> None:
    """Set card as alreadyKnown and skip along with all other cards with same focusMorph.
    Useful if you see a focusMorph you already know from external knowledge
    """
    assert self.card is not None

    self.mw.checkpoint("Set already known focus morph")
    note = self.card.note()
    note.add_tag(get_preference('Tag_AlreadyKnown'))
    note.flush()
    mark_morph_seen(note)

    # "new counter" might have been decreased (but "new card" was not answered
    # so it shouldn't) -> this function recomputes "new counter"
    self.mw.col.reset()

    self.mw.col.sched.buryCards([self.card.id], manual=False)
    self.nextCard()


def browse_same_focus(self, vocab_tag=False):  # 3
    """Opens browser and displays all notes with the same focus morph.
    Useful to quickly find alternative notes to learn focus from"""

    note = self.card.note()
    focus_morphs = try_to_get_focus_morphs(note)

    if focus_morphs is None:
        tooltip("Found no focus morph field!")
        return

    if len(focus_morphs) == 0:
        tooltip("Focus morph field is empty!")
        return

    query = focus_query(get_preference('Field_FocusMorph'), focus_morphs, vocab_tag)
    browser = dialogs.open('Browser', self.mw)
    browser.form.searchEdit.lineEdit().setText(query)
    browser.onSearchActivated()


def my_reviewer_shortcut_keys(self: Reviewer, _old):
    key_browse = get_preference('browse same focus key')
    key_browse_non_vocab = get_preference('browse same focus key non vocab')
    key_skip = get_preference('set known and skip key')

    keys = _old(self)
    keys.extend([
        (key_browse, lambda: browse_same_focus(self, vocab_tag=True)),
        (key_browse_non_vocab, lambda: browse_same_focus(self, vocab_tag=False)),
        (key_skip, lambda: set_known_and_skip(self))
    ])
    return keys


def highlight(txt: str, field, note_filter: str, ctx) -> str:
    """When a field is marked with the 'focusMorph' command, we format it by
    wrapping all the morphemes in <span>s with attributes set to its maturity"""

    if note_filter != "morphHighlight":
        return txt

    frequency_list_path = get_preference('path_frequency')
    try:
        with codecs.open(frequency_list_path, encoding='utf-8') as f:
            frequency_list = [line.strip().split('\t')[0] for line in f.readlines()]
    except FileNotFoundError:
        frequency_list = []

    note = ctx.note()
    tags = note.string_tags()

    note_filter = get_filter(note)
    if note_filter is None:
        return txt

    morphemizer = getMorphemizerByName(note_filter['Morphemizer'])
    if morphemizer is None:
        return txt

    proper_nouns_known = get_preference('Option_ProperNounsAlreadyKnown')

    # TODO: store these somewhere fitting to avoid instantiating them every function call
    known_db = MorphDb(path=get_preference('path_known'))
    mature_db = MorphDb(path=get_preference('path_mature'))
    priority_db = MorphDb(get_preference('path_priority'), ignoreErrors=True).db

    morphemes = getMorphemes(morphemizer, txt, tags)

    # Avoid formatting a smaller morph that is contained in a bigger morph, reverse sort fixes this
    sorted_morphs = sorted(morphemes, key=lambda x: len(x.inflected), reverse=True)

    for morph in sorted_morphs:
        if proper_nouns_known and morph.isProperNoun():
            maturity = 'none'
        elif mature_db.matches(morph):
            maturity = 'mature'
        elif known_db.matches(morph):  # TODO: fix knowndb...
            maturity = 'unmature'
        else:
            maturity = 'unknown'

        priority = 'true' if morph in priority_db else 'false'

        focus_morph_string = morph.show().split()[0]
        frequency = 'true' if focus_morph_string in frequency_list else 'false'

        replacement = f'<span class="morphHighlight" mtype="{maturity}" priority="{priority}" frequency="{frequency}"">\\1</span>'
        txt = text_utils.non_span_sub('(%s)' % morph.inflected, replacement, txt)

    return txt


class SkippedCards:

    def __init__(self):
        self.skipped_cards = {'comprehension': 0, 'fresh': 0, 'known': 0, 'today': 0}
        self.skip_comprehension = get_preference('Option_SkipComprehensionCards')
        self.skip_fresh = get_preference('Option_SkipFreshVocabCards')
        self.skip_focus_morph_seen_today = get_preference('Option_SkipFocusMorphSeenToday')

    def process_skip_conditions_of_card(self, note: Note, focus_morphs: list[str]) -> bool:
        # skip conditions set in preferences GUI
        is_comprehension_card = note.has_tag(get_preference('Tag_Comprehension'))
        is_fresh_vocab = note.has_tag(get_preference('Tag_Fresh'))
        is_already_known = note.has_tag(get_preference('Tag_AlreadyKnown'))

        if is_comprehension_card:
            if self.skip_comprehension:
                self.skipped_cards['comprehension'] += 1
                return True
        elif is_fresh_vocab:
            if self.skip_fresh:
                self.skipped_cards['fresh'] += 1
                return True
        elif is_already_known:  # the user requested that the vocabulary does not have to be shown
            self.skipped_cards['known'] += 1
            return True
        elif self.skip_focus_morph_seen_today and any([focus in seen_morphs for focus in focus_morphs]):
            self.skipped_cards['today'] += 1
            return True

        return False

    def skipped_at_least_one_card(self):
        for key in self.skipped_cards.keys():
            if self.skipped_cards[key] > 0:
                return True
        return False

    def show_tooltip_of_skipped_cards(self):
        skipped_string = ''

        if self.skipped_cards['comprehension'] > 0:
            skipped_string += f"Skipped <b>{self.skipped_cards['comprehension']}</b> comprehension cards"
        if self.skipped_cards['fresh'] > 0:
            if skipped_string != '':
                skipped_string += '<br>'
            skipped_string += f"Skipped <b>{self.skipped_cards['fresh']}</b> fresh vocab cards"
        if self.skipped_cards['known'] > 0:
            if skipped_string != '':
                skipped_string += '<br>'
            skipped_string += f"Skipped <b>{self.skipped_cards['known']}</b> already known vocab cards"
        if self.skipped_cards['today'] > 0:
            if skipped_string != '':
                skipped_string += '<br>'
            skipped_string += f"Skipped <b>{self.skipped_cards['today']}</b> morph already seen today cards"

        tooltip(skipped_string)
