# -*- coding: utf-8 -*-
import codecs
import gzip
import os
import pickle
import re
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, Set

import aqt

# need some fallbacks if not running from anki and thus ankimorphs.util isn't available
try:
    from .util import error_msg
except ImportError:

    def error_msg(msg):
        pass


try:
    from .preferences import get_preference as cfg
except:

    def cfg(config_string):
        return None


def char_set(start: str, end: str) -> set:
    return set(chr(_char) for _char in range(ord(start), ord(end) + 1))


kanji_chars = char_set("㐀", "䶵") | char_set("一", "鿋") | char_set("豈", "頻")


class Morpheme:
    def __init__(  # pylint:disable=too-many-arguments
        self, norm, base, inflected, read, pos, sub_pos
    ):
        """Initialize morpheme class.

        POS means part-of-speech.

        Example morpheme infos for the expression "歩いて":

        :param str norm: 歩く [normalized base form]
        :param str base: 歩く
        :param str inflected: 歩い  [mecab cuts off all endings, so there is not て]
        :param str read: アルイ
        :param str pos: 動詞
        :param str sub_pos: 自立

        """
        # values are created by "mecab" in the order of the parameters and then directly passed into this constructor
        # example of mecab output:    "歩く     歩い    動詞    自立      アルイ"
        # matches to:                 "base     infl    pos     subPos    read"
        self.norm = norm if norm is not None else base
        self.base = base
        self.inflected = inflected
        self.read = read
        self.pos = pos  # type of morpheme determined by mecab tool. for example: u'動詞' or u'助動詞', u'形容詞'
        self.sub_pos = sub_pos

    def __setstate__(self, data):
        """Override default pickle __setstate__ to initialize missing defaults in old databases"""
        self.norm = data["norm"] if "norm" in data else data["base"]
        self.base = data["base"]
        self.inflected = data["inflected"]
        self.read = data["read"]
        self.pos = data["pos"]
        self.sub_pos = data["subPos"]

    def __eq__(self, other):
        return all(
            [
                isinstance(other, Morpheme),
                self.norm == other.norm,
                self.base == other.base,
                self.inflected == other.inflected,
                self.read == other.read,
                self.pos == other.pos,
                self.sub_pos == other.sub_pos,
            ]
        )

    def __hash__(self):
        return hash(
            (self.norm, self.base, self.inflected, self.read, self.pos, self.sub_pos)
        )

    def base_kanji(self) -> set:
        # todo: profile and maybe cache
        return set(self.base) & kanji_chars

    def get_group_key(self) -> str:
        if cfg("Option_IgnoreGrammarPosition"):
            return f"{self.norm}\t{self.read}"
        return f"{self.norm}\t{self.read}\t{self.pos}\t"

    def is_proper_noun(self):
        return self.sub_pos == "固有名詞" or self.pos == "PROPN"

    def show(self):  # str
        return "\t".join(
            [self.norm, self.base, self.inflected, self.read, self.pos, self.sub_pos]
        )

    def deinflected(self):
        if self.inflected == self.base:
            return self
        return Morpheme(
            self.norm, self.base, self.base, self.read, self.pos, self.sub_pos
        )


def ms2str(morphs):  # [(Morpheme, locs)] -> Str
    return "\n".join(["%d\t%s" % (len(m[1]), m[0].show()) for m in morphs])


class MorphDBUnpickler(pickle.Unpickler):
    def find_class(self, cmodule, cname):
        # Override default class lookup for this module to allow loading databases generated with older
        # versions of the MorphMan add-on.
        if cmodule.endswith("morphemes"):
            return globals()[cname]
        return pickle.Unpickler.find_class(self, cmodule, cname)


def get_morphemes(morphemizer, expression, note_tags=None):
    expression = replace_bracket_contents(expression)

    # go through all replacement rules and search if a rule (which dictates a string to morpheme conversion) can be
    # applied
    replace_rules = cfg("ReplaceRules")
    # NB: replace_rules is by default just an empty list...

    if note_tags is not None and replace_rules is not None:
        note_tags_set = set(note_tags)
        for filter_tags, regex, morphemes in replace_rules:
            if not set(filter_tags) <= note_tags_set:
                continue

            # find matches
            split_expression = re.split(regex, expression, maxsplit=1, flags=re.UNICODE)

            if len(split_expression) == 1:
                continue  # no match
            assert len(split_expression) == 2

            # make sure this rule doesn't lead to endless recursion
            if len(split_expression[0]) >= len(expression) or len(
                split_expression[1]
            ) >= len(expression):
                continue

            a_morphs = get_morphemes(morphemizer, split_expression[0], note_tags)
            b_morphs = [
                Morpheme(mstr, mstr, mstr, mstr, "UNKNOWN", "UNKNOWN")
                for mstr in morphemes
            ]
            c_morphs = get_morphemes(morphemizer, split_expression[1], note_tags)
            return a_morphs + b_morphs + c_morphs

    morphs = morphemizer.get_morphemes_from_expr(expression)

    return morphs


square_brackets_regex = re.compile(r"\[[^\]]*\]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^\)]*\)")


def replace_bracket_contents(expression):
    if cfg("Option_IgnoreBracketContents"):
        if square_brackets_regex.search(expression):
            expression = square_brackets_regex.sub("", expression)

    if cfg("Option_IgnoreRoundBracketContents"):
        if round_brackets_regex.search(expression):
            expression = round_brackets_regex.sub("", expression)

    if cfg("Option_IgnoreSlimRoundBracketContents"):
        if slim_round_brackets_regexp.search(expression):
            expression = slim_round_brackets_regexp.sub("", expression)

    return expression


class Location(ABC):
    def __init__(self, weight):
        self.weight = weight
        self.maturity = 0

    @abstractmethod
    def show(self):
        pass


class Nowhere(Location):
    def __init__(self, tag, weight=0):
        super().__init__(weight)
        self.tag = tag

    def show(self):
        return f"{self.tag}@{self.maturity}"


class Corpus(Location):
    """A corpus we want to use for priority, without storing more than morpheme frequencies."""

    def __init__(self, name, weight):
        super().__init__(weight)
        self.name = name

    def show(self):
        return f"{self.name}*{self.weight}@{self.maturity}"


class TextFile(Location):
    def __init__(self, file_path, line_no, maturity, weight=1):
        super().__init__(weight)
        self.file_path = file_path
        self.line_num = line_no
        self.maturity = maturity

    def show(self):
        return f"{self.file_path}:{self.line_num}@{self.maturity}"


class AnkiDeck(Location):
    """This maps to/contains information for one note and one relevant field like u'Expression'."""

    def __init__(  # pylint:disable=too-many-arguments
        self, note_id, field_name, field_value, guid, maturity, weight=1
    ):
        super().__init__(weight)
        self.note_id = note_id
        self.field_name = field_name  # for example u'Expression'
        self.field_value = field_value  # for example u'それだけじゃない'
        self.guid = guid
        # list of intergers, one for every card -> containg the intervals of every card for this note
        self.maturities = None
        self.maturity = maturity
        self.weight = weight

    def show(self):
        return f"{self.note_id}[{self.field_name}]@{self.maturity}"


def alt_includes_morpheme(morph: Morpheme, alt: Morpheme) -> bool:
    return morph.norm == alt.norm and (
        morph.base == alt.base or morph.base_kanji() <= alt.base_kanji()
    )


class MorphDb:  # pylint:disable=too-many-instance-attributes,too-many-public-methods
    @staticmethod
    def merge_files(
        a_path, b_path, dest_path=None, ignore_errors=False
    ):  # FilePath -> FilePath -> Maybe FilePath -> Maybe Book -> IO MorphDb
        db_a, db_b = MorphDb(a_path, ignore_errors), MorphDb(b_path, ignore_errors)
        db_a.merge(db_b)
        if dest_path:
            db_a.save(dest_path)
        return db_a

    @staticmethod
    def mk_from_file(path, morphemizer, maturity=0):  # FilePath -> Maturity? -> IO Db
        """Returns None and shows error dialog if failed"""
        data = MorphDb()
        try:
            data.import_file(path, morphemizer, maturity=maturity)
        except (UnicodeDecodeError, IOError) as error:
            return error_msg(
                "Unable to import file. Please verify it is a UTF-8 text file and you have "
                + f"permissions.\nFull error:\n{error}"
            )
        return data

    def __init__(self, path=None, ignore_errors=False):  # Maybe Filepath -> m ()
        self.v_count = None
        self.k_count = None
        self._loc_db = None
        self._fid_db = None
        self.pos_break_down = None
        self.db = (  # pylint:disable=invalid-name
            {}
        )  # type: Dict[Morpheme, Set[Location]]
        self.groups = {}  # Map NormMorpheme {Set(Morpheme)}
        self.meta = {}
        if path:
            try:
                self.load(path)
            except IOError:
                if not ignore_errors:
                    raise
        self.analyze()

    # Serialization
    def show(self):  # Str
        _string = ""
        for morph, locs in self.db.items():
            _string += f"{morph.show()}\n"
            for loc in locs:
                _string += f"  {loc.show()}\n"
        return _string

    def show_loc_db(self):  # m Str
        _string = ""
        for loc, morphs in self.loc_db().items():
            _string += f"{loc.show()}\n"
            for morph in morphs:
                _string += f"  {morph.show()}\n"
        return _string

    def show_ms(self):  # Str
        return ms2str(sorted(self.db.items(), key=lambda it: it[0].show()))

    def save(self, path):  # FilePath -> IO ()
        par = os.path.split(path)[0]
        if not os.path.exists(par):
            os.makedirs(par)
        file = gzip.open(path, "wb")

        data = {"db": self.db, "meta": self.meta}
        pickle.dump(data, file, -1)
        file.close()
        if cfg("saveSQLite"):
            save_db(self.db, path)

    def load(self, path):  # FilePath -> m ()
        file = gzip.open(path)
        try:
            data = MorphDBUnpickler(file).load()
            if "meta" in data:
                self.meta = data["meta"]
                db = data["db"]  # pylint:disable=invalid-name
            else:
                db = data  # pylint:disable=invalid-name
            for morph, locs in db.items():
                self.update_morph_locs(morph, locs)
        except ModuleNotFoundError as error:
            print(f"ModuleNotFoundError exception: {error}")
            aqt.utils.showInfo(
                "ModuleNotFoundError was thrown. That probably means that you're using database files generated in "
                "the older versions of MorphMan. To fix this issue, please refer to the written guide on database "
                "migration (copy-pasteable link will appear in the next window): "
                "https://gist.github.com/InfiniteRain/1d7ca9ad307c4203397a635b514f00c2"
            )
            raise error
        file.close()

    # Returns True if DB has variations that can match 'm'.
    def matches(self, morph: Morpheme) -> bool:
        group_key = morph.get_group_key()
        morphs = self.groups.get(group_key, None)
        if morphs is None:
            return False

        # Fuzzy match to variations
        return any(alt_includes_morpheme(morph, alt) for alt in morphs)

    # Returns set of morph locations that can match 'm'
    def get_matching_locs(self, morph):  # Morpheme
        # type: (Morpheme) -> Set[Location]
        locs = set()
        group_key = morph.get_group_key()
        morphs = self.groups.get(group_key, None)
        if morphs is None:
            return locs

        # Fuzzy match to variations
        for variation in morphs:
            if alt_includes_morpheme(morph, variation):
                locs.update(self.db[variation])
        return locs

    # Adding
    def clear(self):  # m ()
        self.db = {}
        self.groups = {}
        self.meta = {}

    def _add_morph_locs(self, morph_locs):  # [ (Morpheme,Location) ] -> m ()
        for morph, loc in morph_locs:
            if morph in self.db:
                self.db[morph].add(loc)
            else:
                self.db[morph] = {loc}
                group_key = morph.get_group_key()
                if group_key not in self.groups:
                    self.groups[group_key] = {morph}
                else:
                    self.groups[group_key].add(morph)

    def update_morph_locs(self, morph, locs):  # Morpheme -> {Location} -> m ()
        if morph in self.db:
            self.db[morph].update(locs)
        else:
            self.db[morph] = set(locs)
            group_key = morph.get_group_key()
            if group_key not in self.groups:
                self.groups[group_key] = {morph}
            else:
                self.groups[group_key].add(morph)

    def add_morphs_to_loc(self, morphs, loc):  # [Morpheme] -> Location -> m ()
        self._add_morph_locs((morph, loc) for morph in morphs)

    def add_from_loc_db(self, ldb):  # Map Location {Morpheme} -> m ()
        for loc, morphs in ldb.items():
            self._add_morph_locs([(m, loc) for m in morphs])

    def remove_morphs(self, _iter):
        for morph in _iter:
            if morph in self.db:
                self.db.pop(morph)
                group_key = morph.get_group_key()
                if group_key in self.groups:
                    self.groups[group_key].remove(morph)

    # returns number of added entries
    def merge(self, morph_db):  # Db -> m Int
        new = 0
        for morph, locs in morph_db.db.items():
            if morph in self.db:
                new += len(locs - self.db[morph])
                self.db[morph].update(locs)
            else:
                new += len(locs)
                self.update_morph_locs(morph, locs)

        return new

    # FilePath -> Morphemizer -> Maturity? -> IO ()
    def import_file(self, path, morphemizer, maturity=0):
        _input = ""
        with codecs.open(path, encoding="utf-8") as file:
            _input = file.readlines()

        for i, line in enumerate(_input):
            morphs = get_morphemes(morphemizer, line.strip())
            self._add_morph_locs(
                (morph, TextFile(path, i + 1, maturity)) for morph in morphs
            )

    # Analysis (local)
    def frequency(self, morph: Morpheme) -> int:
        return sum(getattr(loc, "weight", 1) for loc in self.get_matching_locs(morph))

    # Analysis (global)
    def loc_db(self, recalc: bool = True) -> Dict[Location, Set[Morpheme]]:
        if hasattr(self, "_locDb") and not recalc:
            return self._loc_db  # pylint: disable=E0203 # pylint is wrong
        self._loc_db = data = {}  # type: Dict[Location, Set[Morpheme]]
        for morph, locs in self.db.items():
            for loc in locs:
                if loc in data:
                    data[loc].add(morph)
                else:
                    data[loc] = {morph}
        return data

    def fid_db(self, recalc=True):  # Maybe Bool -> m Map FactId Location
        if hasattr(self, "_fidDb") and not recalc:
            return self._fid_db  # pylint: disable=E0203 # pylint is wrong
        self._fid_db = data = {}
        for loc in self.loc_db():
            try:
                data[(loc.noteId, loc.guid, loc.fieldName)] = loc
            except AttributeError:
                pass  # location isn't an anki fact
        return data

    def count_by_type(self):  # Map Pos Int
        data = {}
        for morph in self.db.keys():
            data[morph.pos] = data.get(morph.pos, 0) + 1
        return data

    def analyze(self):  # m ()
        self.pos_break_down = self.count_by_type()
        self.k_count = len(self.groups)
        self.v_count = len(self.db)

    def analyze2str(self):  # m Str
        self.analyze()
        pos_str = "\n".join(
            "%d\t%d%%\t%s" % (v, 100.0 * v / self.v_count, k)
            for k, v in self.pos_break_down.items()
        )
        return f"Total normalized morphemes: {self.k_count}\nTotal variations: {self.v_count}\nBy part of speech:\n{pos_str}"


# sqlite code


def connect_db(path):
    conn = sqlite3.connect(path)
    return conn


def drop_table(cur, name):
    sql = f"drop table if exists {name};"
    cur.execute(sql)


def create_table(cur, name, fields, extra=""):
    sql = f"create table {name} ({fields}{extra});"
    cur.execute(sql)


# helper functions to convert morphman objectsi into sql tuples
def transcode_item(item):
    return item.norm, item.base, item.inflected, item.read, item.pos, item.sub_pos


def transcode_location(loc):
    return (
        loc.note_id,
        loc.field_name,
        loc.field_value,
        loc.maturity,
        loc.guid,
        loc.weight,
    )


def save_db_all_morphs(current, db, table_name):  # pylint:disable=invalid-name
    # we cannot use the name 'all' for a table
    # since it is a reserved word in sql
    if table_name == "all":
        # used 'morphs' instead
        table_name = "morphs"

    # fields  of table to be created
    fields = "morphid, norm, base, inflected, read, pos, subpos"

    drop_table(current, table_name)

    create_table(current, table_name, fields, ", primary key (morphid)")

    def transcode_item_pair(element):
        # el is a pair: <the morphid (an int), morph object>
        # this is a helper function for the map below
        item = element[1]
        return (element[0],) + transcode_item(item)

    # convert the info in the db into list of tuples
    tuples = map(transcode_item_pair, enumerate(db.keys()))

    # insert them all at once
    current.executemany(
        "INSERT INTO %s (%s) VALUES(?,?,?,?,?,?,?);" % (table_name, fields), tuples
    )


def read_db_all_morphs(cur):
    # read the morphs as a dictionary, where the key is the morph tuple and
    # the value is the morphid
    # see save_db_all_morphs for the schema of the morphs relation

    cur.execute("SELECT * FROM morphs;")
    rows = cur.fetchall()
    for_dict = map(lambda x: (x[1:], x[0]), rows)
    return dict(for_dict)


def save_db_locations(cur, db, table_name="locations"):  # pylint:disable=invalid-name
    # save a morphman db as a table in database
    # it is usually faster to drop the table than delete/update the tuples
    # in it
    drop_table(cur, table_name)

    # fields for the table
    fields = "morphid, noteid, field, fieldvalue, maturity, guid, weight"
    create_table(
        cur,
        table_name,
        fields,
        ", primary key (morphid, noteid, field), foreign key (morphid) references morphs",
    )

    # we need to know the morphid of each morph
    # so we can properly reference them in the table locations
    # (see foreign key constraint in the table create above)
    # in theory we have this info, but this mades the code
    # simpler and less error prone and it the time penalty
    # seems to be minimal

    # morphs is a dictionary that maps
    #  transcode_item(morph) to its morphid (int)
    morphs = read_db_all_morphs(cur)

    # we need to convert the db of morphs into a list of tuples
    # where the first value is the morphid (stored in the table
    # we just created)

    # a morph might have multiple locations
    # map each morph in db into a list [morphidlist, location info]
    locations_lists = map(
        lambda x: list(  # this is a pair of morph and list of locations
            map(lambda y: (morphs[transcode_item(x[0])],) + transcode_location(y), x[1])
        ),
        db.items(),
    )

    # flatten the list... because we have a list of lists (one list per morph)
    tuples = [val for sublist in locations_lists for val in sublist]

    cur.executemany(
        "INSERT INTO %s (%s) VALUES(?,?,?,?,?,?,?);" % (table_name, fields), tuples
    )


def save_db(db, path):  # pylint:disable=invalid-name
    # assume that the directory is already created...
    # exceptions will handle the errors

    # we need to wedge this code in here, while we refactor the code...
    # morphman stores info in a bunch of files.
    #
    # database with each "file" as a table
    # so let use the basefilename of the relation as
    tname = os.path.basename(path)
    dir_name = os.path.dirname(path)
    # it ends with .db so cut it
    assert len(tname) > 3 and tname[-3:] == ".db", "extension is no longer .db?"

    # name of the morphs to save (all, known, etc.)
    tname = tname[:-3]
    db_name = dir_name + "/morphman.sqlite"

    conn = connect_db(db_name)
    with conn:
        cur = conn.cursor()
        # it looks like we only need to save the "all" data
        # the others seem to be subsets of it (based on the
        # maturity field)
        if tname == "all":
            # save morphs
            save_db_all_morphs(cur, db, tname)
            # then we need to save the locations
            # every morph in location is guaranteed in db at this point
            save_db_locations(cur, db)
        conn.commit()

    print(f"Saved to sqlite Tname [{tname}] dbname [{db_name}]")
