import csv
import itertools
import time
from functools import partial
from typing import Optional, Union

from anki.collection import Collection
from anki.models import FieldDict, NotetypeDict
from anki.tags import TagManager
from anki.utils import field_checksum, int_time, join_fields, split_fields, strip_html
from aqt.operations import QueryOp
from aqt.utils import tooltip

from ankimorphs import morph_stats as stats
from ankimorphs import util
from ankimorphs.exceptions import NoteFilterFieldsException
from ankimorphs.morphemes import AnkiDeck, Location, MorphDb, Morpheme, get_morphemes
from ankimorphs.morphemizer import get_morphemizer_by_name
from ankimorphs.preferences import get_preference, get_preferences
from ankimorphs.util import (
    error_msg,
    get_filter_by_mid_and_tags,
    get_modify_enabled_models,
    get_read_enabled_models,
    mw,
)
from ankimorphs.util_external import Memoize


@Memoize
def get_field_index(field_name, mid) -> Optional[int]:
    """
    Returns the index of a field in a model by its name.
    For example: we have the modelId of the card "Basic".
    The return value might be "1" for fieldName="Front" and
    "2" for fieldName="Back".
    """
    note_type: NotetypeDict = mw.col.models.get(mid)
    fields: dict[str, tuple[int, FieldDict]] = mw.col.models.field_map(note_type)

    try:
        return fields[field_name][1]["ord"]
    except KeyError:
        return None


def extract_field_data(field_name: str, fields: str, mid: str):
    """
    :type field_name: The field name (like u'Expression')
    :type fields: A string containing all field data for the model (created by anki.utils.join_fields())
    :type mid: the modelId depicting the model for the "fields" data
    """
    idx = get_field_index(field_name, mid)
    return strip_html(split_fields(fields)[idx])


@Memoize
def get_sort_field_index(mid):
    return mw.col.models.get(mid)["sortf"]


def set_field(
    model_id: int, all_fields_data: list[str], field_name: str, new_value: str
) -> None:
    if field_name != "":
        index = get_field_index(field_name, model_id)
        if index is not None:
            all_fields_data[index] = new_value


def notes_to_update(last_updated, included_mids):
    # returns list of (nid, mid, flds, guid, tags, maxmat) of
    # cards to analyze
    # ignoring cards that are leeches
    #
    # leeches are cards have tag "Leech". Anki guarantees a space before and after
    #
    # the logic of the query is:
    #   include cards in the result that are
    #     non-suspended
    #      or
    #     are suspended and are not Leeches
    #
    # we build a predicate that we append to the where clause
    if get_preference("Option_IgnoreSuspendedLeeches"):
        filter_susp_leeches = (
            "(c.queue <> -1 or (c.queue = -1 and not instr(tags, ' leech ')))"
        )
    else:
        filter_susp_leeches = "TRUE"

    #
    # First find the cards to analyze
    #   then find the max maturity of those cards
    # pylint:disable=consider-using-f-string
    query = """
        WITH notesToUpdate as (
            SELECT distinct n.id AS nid, mid, flds, guid, tags
            FROM notes n JOIN cards c ON (n.id = c.nid)
            WHERE mid IN ({0}) and (n.mod > {1} or c.mod > {1})
               and {2}) -- ignoring suspended leeches
        SELECT nid, mid, flds, guid, tags,
            max(case when ivl=0 and c.type=1 then 0.5 else ivl end) AS maxmat
        FROM notesToUpdate join cards c USING (nid)
        WHERE {2} -- ignoring suspended leeches
        GROUP by nid, mid, flds, guid, tags;
        """.format(
        ",".join([str(m) for m in included_mids]), last_updated, filter_susp_leeches
    )
    # pylint:enable=consider-using-f-string

    return mw.col.db.execute(query)


def make_all_db(
    all_db=None,
):  # pylint:disable=too-many-locals,too-many-statements,too-many-branches
    # from . import config
    # importlib.reload(config)

    # t_0 = time.time()
    # db = mw.col.db
    col_tags = mw.col.tags

    mw.taskman.run_on_main(
        partial(
            mw.progress.start, label="Prep work for all.db creation", immediate=True
        )
    )
    # for providing an error message if there is no note that is used for processing
    n_enabled_notes = 0

    if not all_db:
        all_db = MorphDb()

    # Recompute everything if preferences changed.
    last_preferences = all_db.meta.get("last_preferences", {})
    if not last_preferences == get_preferences():
        print("Preferences changed.  Recomputing all_db...")
        all_db = MorphDb()  # Clear all db
        last_updated = 0
    else:
        last_updated = all_db.meta.get("last_updated", 0)

    fid_db = all_db.fid_db()
    loc_db = all_db.loc_db(recalc=False)  # fidDb() already forces locDb recalc

    included_types, include_all = get_read_enabled_models()
    included_mids = [
        m["id"]
        for m in mw.col.models.all()
        if include_all or m["name"] in included_types
    ]

    notes = notes_to_update(last_updated, included_mids)
    notes_amount = len(notes)

    print("notes to update:", notes_amount)

    mw.taskman.run_on_main(mw.progress.finish)
    mw.taskman.run_on_main(
        partial(
            mw.progress.start,
            label="Generating all.db data",
            max=notes_amount,
            immediate=True,
        )
    )

    for i, (nid, mid, flds, guid, tags, max_mat) in enumerate(notes):
        # if i % 500 == 0:
        mw.taskman.run_on_main(partial(mw.progress.update, value=i))

        tags_list = col_tags.split(tags)
        mid_cfg = get_filter_by_mid_and_tags(mid, tags_list)
        if mid_cfg is None:
            continue

        n_enabled_notes += 1

        m_name = mid_cfg["Morphemizer"]
        morphemizer = get_morphemizer_by_name(m_name)

        conf = partial(get_preference, model_id=mid)

        if conf("ignore maturity"):
            max_mat = 0
        tags_list, already_known_tag = col_tags.split(tags), get_preference(
            "Tag_AlreadyKnown"
        )
        if already_known_tag in tags_list:
            max_mat = max(max_mat, conf("threshold_mature") + 1)

        for field_name in mid_cfg["Fields"]:
            try:  # if doesn't have field, continue
                field_value = extract_field_data(field_name, flds, mid)
            except KeyError:
                continue
            except TypeError as error:
                mw.taskman.run_on_main(mw.progress.finish)
                note_type = mw.col.models.get(mid)["name"]
                # This gets handled in the on_failure function
                raise NoteFilterFieldsException(field_name, note_type) from error

            assert max_mat is not None, "Maxmat should not be None"

            loc = fid_db.get((nid, guid, field_name), None)
            if not loc:
                loc = AnkiDeck(nid, field_name, field_value, guid, max_mat)
                morphs = get_morphemes(morphemizer, field_value, tags_list)
                if morphs:  # TODO: this needed? should we change below too then?
                    loc_db[loc] = morphs
            else:
                # mats changed -> new loc (new mats), move morphs
                if loc.field_value == field_value and loc.maturity != max_mat:
                    new_loc = AnkiDeck(nid, field_name, field_value, guid, max_mat)
                    loc_db[new_loc] = loc_db.pop(loc)
                # field changed -> new loc, new morphs
                elif loc.field_value != field_value:
                    new_loc = AnkiDeck(nid, field_name, field_value, guid, max_mat)
                    morphs = get_morphemes(morphemizer, field_value, tags_list)
                    loc_db.pop(loc)
                    loc_db[new_loc] = morphs

    # printf('Processed %d notes in %f sec' % (N_notes, time.time() - t_0))

    mw.taskman.run_on_main(partial(mw.progress.update, label="Creating all.db objects"))
    old_meta = all_db.meta
    all_db.clear()
    all_db.add_from_loc_db(loc_db)
    all_db.meta = old_meta
    mw.taskman.run_on_main(mw.progress.finish)
    return all_db


def filter_db_by_mat(db, mat):  # pylint:disable=invalid-name
    """Assumes safe to use cached locDb"""
    new_db = MorphDb()
    for loc, morphs in db.loc_db(recalc=False).items():
        if loc.maturity > mat:
            new_db.add_morphs_to_loc(morphs, loc)
    return new_db


def update_notes(
    all_db,
):  # pylint:disable=too-many-branches,too-many-statements,too-many-locals
    # t_0 = time.time()
    now = int_time()
    db = mw.col.db  # pylint:disable=invalid-name

    col_tags: TagManager = mw.col.tags
    _notes_to_update = []
    note_id_morphman_index = {}

    mw.taskman.run_on_main(
        partial(mw.progress.start, label="Updating data", immediate=True)
    )

    fid_db = all_db.fid_db(recalc=True)
    loc_db: dict[Location, set[Morpheme]] = all_db.loc_db(recalc=False)

    # read tag names
    (
        comp_tag,
        vocab_tag,
        fresh_tag,
        not_ready_tag,
        already_known_tag,  # pylint:disable=unused-variable
        priority_tag,
        too_short_tag,
        too_long_tag,
        frequency_tag,
    ) = tag_names = (
        get_preference("Tag_Comprehension"),
        get_preference("Tag_Vocab"),
        get_preference("Tag_Fresh"),
        get_preference("Tag_NotReady"),
        get_preference("Tag_AlreadyKnown"),
        get_preference("Tag_Priority"),
        get_preference("Tag_TooShort"),
        get_preference("Tag_TooLong"),
        get_preference("Tag_Frequency"),
    )
    col_tags.register(tag_names)
    bad_length_tag = get_preference("Tag_BadLength")

    # handle secondary databases
    mw.taskman.run_on_main(
        partial(mw.progress.update, label="Creating seen/known/mature from all.db")
    )

    seen_db = filter_db_by_mat(all_db, get_preference("threshold_seen"))
    known_db = filter_db_by_mat(all_db, get_preference("threshold_known"))
    mature_db = filter_db_by_mat(all_db, get_preference("threshold_mature"))

    mw.taskman.run_on_main(partial(mw.progress.update, label="Loading priority.db"))
    priority_db = MorphDb(get_preference("path_priority"), ignore_errors=True)

    mw.taskman.run_on_main(partial(mw.progress.update, label="Loading frequency.txt"))

    frequency_list_path = get_preference("path_frequency")
    frequency_map = {}
    frequency_list_exists = False

    try:
        with open(frequency_list_path, encoding="utf-8-sig") as csvfile:
            csvreader = csv.reader(csvfile, delimiter="\t")
            rows = list(csvreader)

            if rows[0][0] == "#study_plan_frequency":
                frequency_list_exists = True
                frequency_map = dict(
                    zip(
                        [
                            Morpheme(row[0], row[1], row[2], row[3], row[4], row[5])
                            for row in rows[1:]
                        ],
                        itertools.count(0),
                    )
                )
            else:
                frequency_map = dict(zip([row[0] for row in rows], itertools.count(0)))

    except (FileNotFoundError, IndexError):
        pass

    frequency_list_length = len(frequency_map)

    # prefetch cfg for fields
    field_focus_morph = get_preference("Field_FocusMorph")
    field_unknown_count = get_preference("Field_UnknownMorphCount")
    field_unmature_count = get_preference("Field_UnmatureMorphCount")
    field_morph_man_index = get_preference("Field_MorphManIndex")
    field_unknowns = get_preference("Field_Unknowns")
    field_unmatures = get_preference("Field_Unmatures")
    field_unknown_freq = get_preference("Field_UnknownFreq")
    field_focus_morph_pos = get_preference("Field_FocusMorphPos")

    skip_comprehension_cards = get_preference("Option_SkipComprehensionCards")
    skip_fresh_cards = get_preference("Option_SkipFreshVocabCards")

    # Find all morphs that changed maturity and the notes that refer to them.
    last_maturities = all_db.meta.get("last_maturities", {})
    new_maturities = {}
    refresh_notes = set()

    # Recompute everything if preferences changed.
    last_preferences = all_db.meta.get("last_preferences", {})
    if not last_preferences == get_preferences():
        print("Preferences changed.  Updating all notes...")
        last_updated = 0
    else:
        last_updated = all_db.meta.get("last_updated", 0)

    # Todo: Remove this forced 0 once we add checks for other changes like new frequency.txt files.
    last_updated = 0

    # If we're updating everything anyway, clear the notes set.
    if last_updated > 0:
        for _morph, locs in all_db.db.items():
            maturity_bits = 0
            if seen_db.matches(_morph):
                maturity_bits |= 1
            if known_db.matches(_morph):
                maturity_bits |= 2
            if mature_db.matches(_morph):
                maturity_bits |= 4

            new_maturities[_morph] = maturity_bits

            if last_maturities.get(_morph, -1) != maturity_bits:
                for loc in locs:
                    if isinstance(loc, AnkiDeck):
                        refresh_notes.add(loc.note_id)

    included_types, include_all = get_modify_enabled_models()
    included_mids = [
        m["id"]
        for m in mw.col.models.all()
        if include_all or m["name"] in included_types
    ]

    # pylint:disable=consider-using-f-string
    query = """
        SELECT n.id as nid, mid, flds, guid, tags, max(c.type) AS maxtype
        FROM notes n JOIN cards c ON (n.id = c.nid)
        WHERE mid IN ({0}) and ( n.mod > {2} or n.id in ({1}) )
        GROUP by nid, mid, flds, guid, tags;
        """.format(
        ",".join([str(m) for m in included_mids]),
        ",".join([str(id) for id in refresh_notes]),
        last_updated,
    )
    # pylint:enable=consider-using-f-string

    query_results = db.execute(query)

    notes_amount = len(query_results)

    for i, (note_id, model_id, fields, guid, tags, max_type) in enumerate(
        query_results
    ):
        tags_list = col_tags.split(tags)

        if i % 1000 == 0:
            mw.taskman.run_on_main(
                partial(
                    mw.progress.update,
                    label=f"Recalculated {i} of {notes_amount} cards ",
                    value=i,
                    max=notes_amount,
                )
            )

        note_cfg = get_filter_by_mid_and_tags(model_id, tags_list)
        if note_cfg is None or not note_cfg["Modify"]:
            continue

        # add bonus for morphs in priority.db and frequency.txt
        conf = partial(get_preference, model_id=model_id)

        frequency_bonus = conf("frequency.txt bonus")
        if conf("Option_AlwaysPrioritizeFrequencyMorphs"):
            no_priority_penalty = conf("no priority penalty")
        else:
            no_priority_penalty = 0
        reinforce_new_vocab_weight = conf("reinforce new vocab weight")
        priority_db_weight = conf("priority.db weight")
        proper_nouns_known = get_preference("Option_ProperNounsAlreadyKnown")

        # Get all morphemes for note
        morphemes = set()
        for field_name in note_cfg["Fields"]:
            try:
                loc = fid_db[(note_id, guid, field_name)]
                morphemes.update(loc_db[loc])
            except KeyError:
                continue

        # Determine un-seen/known/mature and i+N
        unseens, unknowns, unmatures, new_knowns = set(), set(), set(), set()
        for morpheme in morphemes:
            if proper_nouns_known and morpheme.is_proper_noun():
                continue
            morpheme = morpheme.deinflected()
            if not seen_db.matches(morpheme):
                unseens.add(morpheme)
            if not known_db.matches(morpheme):
                unknowns.add(morpheme)
            if not mature_db.matches(morpheme):
                unmatures.add(morpheme)
                if known_db.matches(morpheme):
                    new_knowns.add(morpheme)

        # Determine MMI - Morph Man Index
        morphemes_amount = len(morphemes)
        unknows_amount = len(unknowns)
        unmatures_amount = len(unmatures)

        # Set the mmi (due) on all cards to max by default to prevent buggy cards to showing up first
        # if a card already has this mmi (due) it won't update, so this will not have a negative impact on syncing.
        # card.due is converted to a signed 32-bit integer on the backend, so max value is 2147483647 before overflow
        morphman_index = 2147483647
        note_id_morphman_index[note_id] = morphman_index

        # Bail early if card has more than 3 unknown morphs for lite update
        # TODO: Add to preferences GUI to make it adjustable
        if unknows_amount > 3:
            continue
        if skip_comprehension_cards and unknows_amount == 0:
            continue

        is_priority = False
        is_frequency = False
        unknown_morph = None
        morph_frequency = 0
        usefulness = 0

        for unknown_morph in unknowns:
            morph_frequency += all_db.frequency(unknown_morph)

            if priority_db.frequency(unknown_morph) > 0:
                is_priority = True
                usefulness += priority_db_weight

            if frequency_list_exists:
                focus_morph_index = frequency_map.get(unknown_morph, -1)
            else:
                focus_morph_index = frequency_map.get(unknown_morph.base, -1)

            if focus_morph_index >= 0:
                is_frequency = True

                # The bigger this number, the lower mmi becomes
                usefulness += int(
                    round(
                        frequency_bonus
                        * (1 - focus_morph_index / frequency_list_length)
                    )
                )

        # average frequency of unknowns (i.e. how common the word is within your collection)
        frequency_avg = (
            morph_frequency // unknows_amount if unknows_amount > 0 else morph_frequency
        )
        usefulness += frequency_avg

        # add bonus for studying recent learned knowns (reinforce)
        for morpheme in new_knowns:
            locs = known_db.get_matching_locs(morpheme)
            if locs:
                ivl = min(1, max(loc.maturity for loc in locs))
                # TODO: maybe average this so it doesnt favor long sentences
                usefulness += reinforce_new_vocab_weight // ivl

        if any(
            morpheme.pos == "動詞" for morpheme in unknowns
        ):  # FIXME: this isn't working???
            usefulness += conf("verb bonus")

        usefulness = 99999 - min(99999, usefulness)

        # difference from optimal length range (too little context vs long sentence)
        len_diff_raw = min(
            morphemes_amount - conf("min good sentence length"),
            max(0, morphemes_amount - conf("max good sentence length")),
        )
        len_diff = min(9, abs(len_diff_raw))

        # Fill in various fields/tags on the note based on cfg
        fields_list = split_fields(fields)

        # clear any 'special' tags, the appropriate will be set in the next few lines
        tags_list = [
            t
            for t in tags_list
            if t not in (not_ready_tag, comp_tag, vocab_tag, fresh_tag)
        ]

        # apply penalty for cards that aren't prioritized for learning
        if not (is_priority or is_frequency):
            usefulness += no_priority_penalty

        # determine card type
        if unmatures_amount == 0:  # sentence comprehension card, m+0
            tags_list.append(comp_tag)
            if skip_comprehension_cards:
                usefulness += (
                    1000000  # Add a penalty to put these cards at the end of the queue
                )
        elif unknows_amount == 1:  # new vocab card, k+1
            tags_list.append(vocab_tag)
            if max_type == 0:  # Only update focus fields on 'new' card types.
                set_field(model_id, fields_list, field_focus_morph, unknown_morph.base)
                set_field(
                    model_id, fields_list, field_focus_morph_pos, unknown_morph.pos
                )
        elif unknows_amount > 1:  # M+1+ and K+2+
            tags_list.append(not_ready_tag)
            if max_type == 0:  # Only update focus fields on 'new' card types.
                set_field(
                    model_id,
                    fields_list,
                    field_focus_morph,
                    ", ".join([u.base for u in unknowns]),
                )
                set_field(
                    model_id,
                    fields_list,
                    field_focus_morph_pos,
                    ", ".join([u.pos for u in unknowns]),
                )
        else:  # only case left: we have k+0, but m+1 or higher, so this card does not introduce a new vocabulary -> card for newly learned morpheme
            tags_list.append(fresh_tag)
            if skip_fresh_cards:
                usefulness += (
                    1000000  # Add a penalty to put these cards at the end of the queue
                )
            if max_type == 0:  # Only update focus fields on 'new' card types.
                set_field(
                    model_id,
                    fields_list,
                    field_focus_morph,
                    ", ".join([u.base for u in unmatures]),
                )
                set_field(
                    model_id,
                    fields_list,
                    field_focus_morph_pos,
                    ", ".join([u.pos for u in unmatures]),
                )

        # calculate mmi
        morphman_index = (
            100000 * unknows_amount + 1000 * len_diff + int(round(usefulness))
        )
        if conf("set due based on mmi"):
            note_id_morphman_index[note_id] = morphman_index

        # set type agnostic fields
        set_field(model_id, fields_list, field_unknown_count, f"{unknows_amount}")
        set_field(model_id, fields_list, field_unmature_count, f"{unmatures_amount}")
        set_field(model_id, fields_list, field_morph_man_index, f"{morphman_index}")
        set_field(
            model_id, fields_list, field_unknowns, ", ".join(u.base for u in unknowns)
        )
        set_field(
            model_id, fields_list, field_unmatures, ", ".join(u.base for u in unmatures)
        )
        set_field(model_id, fields_list, field_unknown_freq, f"{frequency_avg}")

        # remove deprecated tag
        if bad_length_tag is not None and bad_length_tag in tags_list:
            tags_list.remove(bad_length_tag)

        # other tags
        if priority_tag in tags_list:
            tags_list.remove(priority_tag)
        if is_priority:
            tags_list.append(priority_tag)

        if frequency_tag in tags_list:
            tags_list.remove(frequency_tag)
        if is_frequency:
            tags_list.append(frequency_tag)

        if too_short_tag in tags_list:
            tags_list.remove(too_short_tag)
        if len_diff_raw < 0:
            tags_list.append(too_short_tag)

        if too_long_tag in tags_list:
            tags_list.remove(too_long_tag)
        if len_diff_raw > 0:
            tags_list.append(too_long_tag)

        # remove unnecessary tags
        if not get_preference("Option_SetNotRequiredTags"):
            unnecessary = [priority_tag, too_short_tag, too_long_tag]
            tags_list = [tag for tag in tags_list if tag not in unnecessary]

        # update sql db
        tags_ = col_tags.join(tags_list)
        flds_ = join_fields(fields_list)
        if fields != flds_ or tags != tags_:  # only update notes that have changed
            csum = field_checksum(fields_list[0])
            sfld = strip_html(fields_list[get_sort_field_index(model_id)])
            _notes_to_update.append(
                (tags_, flds_, sfld, csum, now, mw.col.usn(), note_id)
            )

    mw.taskman.run_on_main(
        partial(mw.progress.update, label="Updating anki database...")
    )
    mw.col.db.executemany(
        "update notes set tags=?, flds=?, sfld=?, csum=?, mod=?, usn=? where id=?",
        _notes_to_update,
    )

    # Now reorder new cards based on MMI
    mw.taskman.run_on_main(
        partial(mw.progress.update, label="Updating new card ordering...")
    )
    _notes_to_update = []

    # "type = 0": new cards
    # "type = 1": learning cards [is supposed to be learning: in my case no learning card had this type]
    # "type = 2": review cards
    for cid, note_id, due in db.execute(
        "select id, nid, due from cards where type = 0"
    ):
        if note_id in note_id_morphman_index:  # owise it was disabled
            due_ = note_id_morphman_index[note_id]
            if due != due_:  # only update cards that have changed
                _notes_to_update.append((due_, now, mw.col.usn(), cid))

    mw.col.db.executemany(
        "update cards set due=?, mod=?, usn=? where id=?", _notes_to_update
    )

    mw.taskman.run_on_main(mw.reset)

    all_db.meta["last_preferences"] = get_preferences()
    all_db.meta["last_maturities"] = new_maturities
    all_db.meta["last_updated"] = int(time.time() + 0.5)

    # printf('Updated %d notes in %f sec' % (N_notes, time.time() - t_0))

    if get_preference("saveDbs"):
        mw.taskman.run_on_main(
            partial(mw.progress.update, label="Saving all/seen/known/mature dbs")
        )
        all_db.save(get_preference("path_all"))
        seen_db.save(get_preference("path_seen"))
        known_db.save(get_preference("path_known"))
        mature_db.save(get_preference("path_mature"))
        # printf('Updated %d notes + saved dbs in %f sec' % (N_notes, time.time() - t_0))

    mw.taskman.run_on_main(mw.progress.finish)
    return known_db


def main():
    print(f"recalc main pre, mw.inMainThread(): {mw.inMainThread()}")

    operation = QueryOp(
        parent=mw,
        op=main_background_op,
        success=lambda t: tooltip("Finished Recalc"),  # t = return value of the op
    )

    # if with_progress() is not called, no progress window will be shown.
    # note: QueryOp.with_progress() was broken until Anki 2.1.50
    operation.with_progress().run_in_background()
    operation.failure(on_failure)


def main_background_op(collection: Collection):
    assert mw is not None

    print("running main")

    mw.taskman.run_on_main(
        partial(mw.progress.start, label="Loading existing all.db", immediate=True)
    )
    current_all_db = util.get_all_db() if get_preference("loadAllDb") else None
    mw.taskman.run_on_main(mw.progress.finish)

    print("running main2")

    # update all.db
    all_db = make_all_db(current_all_db)

    print("running main3")

    # merge in external.db
    mw.taskman.run_on_main(
        partial(mw.progress.start, label="Merging ext.db", immediate=True)
    )
    ext = MorphDb(get_preference("path_ext"), ignore_errors=True)
    all_db.merge(ext)
    mw.taskman.run_on_main(mw.progress.finish)

    print("running main3.5")

    # TODO: 'Known' is a horrendously bad name for this db... it actually contains every morph that has ever been
    #  seen, so it is super misleading... rename it to something better like 'learned' or 'unmature'
    known_db = update_notes(all_db)

    print("running main4")

    # update stats and refresh display
    stats.update_stats(known_db)

    print("running main5")

    mw.taskman.run_on_main(mw.toolbar.draw)

    # set global allDb
    util._all_db = all_db

    print("running main6")


def on_failure(_exception: Union[Exception, NoteFilterFieldsException]):
    if isinstance(_exception, NoteFilterFieldsException):
        error_msg(
            f'Did not find a field called "{_exception.field_name}" in the Note Type "{_exception.note_type}"\n\n'
            f"Field names are case-sensitive!\n\n"
            f"Read the guide for more info:\n"
            f"https://mortii.github.io/MorphMan/user_guide/setup/preferences/note-filter.html "
        )
    else:
        raise _exception
