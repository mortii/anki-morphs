from __future__ import annotations

import functools
import sqlite3
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from anki.cards import CardId
from anki.collection import SearchNode
from anki.models import NotetypeId
from aqt import mw
from aqt.operations import QueryOp

from . import ankimorphs_globals
from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme
from .name_file_utils import get_names_from_file_as_morphs
from .recalc.anki_data_utils import AnkiMorphsCardData


class AnkiMorphsDB:  # pylint:disable=too-many-public-methods
    # A card can have many morphs, morphs can be on many cards,
    # therefore, we need a many-to-many db structure:
    # Cards -> Card_Morph_Map <- Morphs

    def __init__(self, db_path: Path | None = None) -> None:
        """
        db_path is used for swapping dbs during testing
        """
        assert mw is not None
        assert mw.pm is not None

        if db_path is None:
            db_path = Path(mw.pm.profileFolder(), "ankimorphs.db")

        self.con: sqlite3.Connection = sqlite3.connect(db_path)

    def __enter__(self) -> AnkiMorphsDB:
        """
        Creates a context manager
        """
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """
        Closes the database connection when exiting the context.
        Commits if no exception occurred, else rolls back.
        """
        if self.con:
            if exc_type is None:
                self.con.commit()
            else:
                print(f"exc_type: {exc_type}")
                print(f"exc_value: {exc_value}")
                print(f"traceback: {traceback}")
                self.con.rollback()
            self.con.close()

    def create_all_tables(self) -> None:
        self.create_morph_table()
        self.create_cards_table()
        self.create_card_morph_map_table()
        self.create_card_scoring_morph_map_table()
        self.create_seen_morph_table()

    def create_cards_table(self) -> None:
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Cards
                    (
                        card_id INTEGER PRIMARY KEY ASC,
                        note_id INTEGER,
                        note_type_id INTEGER,
                        card_type INTEGER,
                        tags TEXT
                    )
                    """
            )

    def create_card_morph_map_table(self) -> None:
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Card_Morph_Map
                    (
                        card_id INTEGER,
                        morph_lemma TEXT,
                        morph_inflection TEXT,
                        FOREIGN KEY(card_id) REFERENCES card(id),
                        FOREIGN KEY(morph_lemma, morph_inflection) REFERENCES morph(lemma, inflection)
                        PRIMARY KEY(card_id, morph_lemma, morph_inflection)
                    )
                    """
            )

    def create_card_scoring_morph_map_table(self) -> None:
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Card_Scoring_Morph_Map
                    (
                        card_id INTEGER,
                        morph_lemma TEXT,
                        morph_inflection TEXT,
                        FOREIGN KEY(card_id) REFERENCES card(id),
                        FOREIGN KEY(morph_lemma, morph_inflection) REFERENCES morph(lemma, inflection)
                        PRIMARY KEY(card_id, morph_lemma, morph_inflection)
                    )
                    """
            )

    def create_morph_table(self) -> None:
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Morphs
                    (
                        lemma TEXT,
                        inflection TEXT,
                        highest_lemma_learning_interval INTEGER,
                        highest_inflection_learning_interval INTEGER,
                        PRIMARY KEY (lemma, inflection)
                    )
                    """
            )

    def create_seen_morph_table(self) -> None:
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Seen_Morphs
                    (
                        lemma TEXT,
                        inflection TEXT,
                        PRIMARY KEY (lemma, inflection)
                    )
                    """
            )

    def insert_many_into_card_table(
        self, card_list: list[dict[str, int | str | bool]]
    ) -> None:
        with self.con:
            self.con.executemany(
                """
                    INSERT OR IGNORE INTO Cards VALUES
                    (
                       :card_id,
                       :note_id,
                       :note_type_id,
                       :card_type,
                       :tags
                    )
                    """,
                card_list,
            )

    def insert_many_into_morph_table(
        self, morph_list: list[dict[str, int | str | bool]]
    ) -> None:
        with self.con:
            # we only need to update the inflections on conflict since the lemmas
            # have already been updated before they are inserted here
            self.con.executemany(
                """
                    INSERT INTO Morphs
                    VALUES
                    (
                       :lemma,
                       :inflection,
                       :highest_lemma_learning_interval,
                       :highest_inflection_learning_interval
                    )
                    ON CONFLICT(lemma, inflection) DO UPDATE SET
                        highest_inflection_learning_interval = :highest_inflection_learning_interval
                    WHERE highest_inflection_learning_interval < :highest_inflection_learning_interval
                """,
                morph_list,
            )

    def insert_many_into_card_morph_map_table(
        self, card_morph_list: list[dict[str, int | str | bool]]
    ) -> None:
        with self.con:
            self.con.executemany(
                """
                    INSERT OR IGNORE INTO Card_Morph_Map VALUES
                    (
                       :card_id,
                       :morph_lemma,
                       :morph_inflection
                    )
                    """,
                card_morph_list,
            )

    def insert_many_into_card_scoring_morph_map_table(
        self, card_morph_list: list[dict[str, int | str | bool]]
    ) -> None:
        with self.con:
            self.con.executemany(
                """
                    INSERT OR IGNORE INTO Card_Scoring_Morph_Map VALUES
                    (
                       :card_id,
                       :morph_lemma,
                       :morph_inflection
                    )
                    """,
                card_morph_list,
            )

    def get_readable_card_morphs(self, card_id: int) -> list[tuple[str, str]]:
        card_morphs: list[tuple[str, str]] = []

        with self.con:
            card_morphs_raw = self.con.execute(
                """
                    SELECT morph_lemma, morph_inflection
                    FROM Card_Morph_Map
                    WHERE card_id = ?
                    """,
                (card_id,),
            ).fetchall()

            for row in card_morphs_raw:
                card_morphs.append((row[0], row[1]))

        return card_morphs

    def get_all_morphs_seen_today(self, only_lemma: bool = False) -> set[str]:
        self.create_seen_morph_table()
        card_morphs: set[str] = set("")
        select_statement: str = "SELECT lemma, inflection"

        if only_lemma:
            select_statement = "SELECT lemma, lemma"

        with self.con:
            card_morphs_raw = self.con.execute(
                f"""
                    {select_statement}
                    FROM Seen_Morphs
                    """
            ).fetchall()

            for row in card_morphs_raw:
                card_morphs.add(row[0] + row[1])

        return card_morphs

    def update_seen_morphs_today_single_card(self, card_id: int) -> None:
        with self.con:
            self.con.execute(
                """
                    INSERT OR IGNORE INTO Seen_Morphs (lemma, inflection)
                    SELECT morph_lemma, morph_inflection
                    FROM Card_Morph_Map
                    WHERE card_id = ?
                    """,
                (card_id,),
            )

    def get_card_morphs(
        self, card_id: int, search_unknowns: bool = False, only_lemma: bool = False
    ) -> set[tuple[str, str]] | None:
        """
        Returns a set of tuples (lemma, inflection)
        """
        morphs: set[tuple[str, str]] = set()

        if only_lemma:
            raw_base_card_morphs = self._get_card_morph_lemma_and_lemma(
                card_id, search_unknowns
            )
        else:
            raw_base_card_morphs = self._get_card_morph_lemma_and_inflection(
                card_id, search_unknowns
            )

        for card_morph in raw_base_card_morphs:
            morphs.add((card_morph[0], card_morph[1]))

        if len(morphs) == 0:
            return None

        return morphs

    def _get_card_morph_lemma_and_inflection(
        self, card_id: int, search_unknowns: bool
    ) -> list[str]:
        where_query_string = "WHERE Card_Morph_Map.card_id = ?"

        if search_unknowns:
            where_query_string += " AND Morphs.highest_inflection_learning_interval = 0"

        with self.con:
            card_morphs = self.con.execute(
                """
                    SELECT DISTINCT morph_lemma, morph_inflection
                    FROM Card_Morph_Map
                    INNER JOIN Morphs ON
                        Card_Morph_Map.morph_lemma = Morphs.lemma AND Card_Morph_Map.morph_inflection = Morphs.inflection
                    """
                + where_query_string,
                (card_id,),
            ).fetchall()

        return card_morphs

    def _get_card_morph_lemma_and_lemma(
        self, card_id: int, search_unknowns: bool
    ) -> list[str]:
        where_query_string = "WHERE Card_Morph_Map.card_id = ?"

        if search_unknowns:
            where_query_string += " AND Morphs.highest_lemma_learning_interval = 0"

        with self.con:
            card_morphs = self.con.execute(
                """
                    SELECT DISTINCT morph_lemma, morph_lemma
                    FROM Card_Morph_Map
                    INNER JOIN Morphs ON
                        Card_Morph_Map.morph_lemma = Morphs.lemma
                    """
                + where_query_string,
                (card_id,),
            ).fetchall()

        return card_morphs

    def get_ids_of_cards_with_same_morphs(
        self,
        card_id: CardId,
        search_unknowns: bool = False,
        search_lemma_only: bool = False,
    ) -> set[CardId] | None:
        # The "where_query_string" is a necessary hack to overcome the sqlite problem
        # of not allowing variable length parameters

        card_ids: set[CardId] = set()
        card_morphs: set[tuple[str, str]] | None = self.get_card_morphs(
            card_id, search_unknowns
        )
        if card_morphs is None:
            return None

        if search_lemma_only:
            where_query_string = "WHERE" + "".join(
                [f" (morph_lemma = '{morph[0]}') OR" for morph in card_morphs]
            )
        else:
            where_query_string = "WHERE" + "".join(
                [
                    f" (morph_lemma = '{morph[0]}' AND morph_inflection = '{morph[1]}') OR"
                    for morph in card_morphs
                ]
            )

        where_query_string = where_query_string[:-3]  # removes last ' OR'

        with self.con:
            raw_card_ids = self.con.execute(
                """
                SELECT DISTINCT card_id
                FROM Card_Morph_Map
                """
                + where_query_string,
            ).fetchall()

            for card_id_raw in raw_card_ids:
                card_ids.add(CardId(card_id_raw[0]))

        if len(card_ids) == 0:
            return None

        return card_ids

    def get_highest_inflection_learning_interval(self, morph: Morpheme) -> int | None:
        with self.con:
            highest_learning_interval = self.con.execute(
                """
                    SELECT highest_inflection_learning_interval
                    FROM Morphs
                    WHERE lemma = ? And inflection = ?
                    """,
                (morph.lemma, morph.inflection),
            ).fetchone()

            if highest_learning_interval is None:
                return None

            # un-tuple the result
            highest_learning_interval = highest_learning_interval[0]
            assert isinstance(highest_learning_interval, int)
            return highest_learning_interval

    def get_highest_lemma_learning_interval(self, morph: Morpheme) -> int | None:
        with self.con:
            highest_learning_interval = self.con.execute(
                """
                    SELECT highest_lemma_learning_interval
                    FROM Morphs
                    WHERE lemma = ?
                    LIMIT 1
                    """,
                (morph.lemma,),
            ).fetchone()

            if highest_learning_interval is None:
                return None

            # un-tuple the result
            highest_learning_interval = highest_learning_interval[0]
            assert isinstance(highest_learning_interval, int)
            return highest_learning_interval

    def get_morph_inflections_learning_statuses(self) -> dict[str, str]:
        morph_status_dict: dict[str, str] = {}
        am_config = AnkiMorphsConfig()

        with self.con:
            card_morphs_raw = self.con.execute(
                """
                    SELECT lemma, inflection, highest_inflection_learning_interval
                    FROM Morphs
                    ORDER BY lemma, inflection
                    """,
            ).fetchall()

            for row in card_morphs_raw:
                key = row[0] + row[1]
                interval = row[2]
                if interval >= am_config.interval_for_known_morphs:
                    learning_status = ankimorphs_globals.STATUS_KNOWN
                elif interval > 0:
                    learning_status = ankimorphs_globals.STATUS_LEARNING
                else:
                    learning_status = ankimorphs_globals.STATUS_UNKNOWN

                morph_status_dict[key] = learning_status

        return morph_status_dict

    def get_morph_lemmas_learning_statuses(self) -> dict[str, str]:
        morph_status_dict: dict[str, str] = {}
        am_config = AnkiMorphsConfig()

        with self.con:
            card_morphs_raw = self.con.execute(
                """
                    SELECT DISTINCT lemma, highest_lemma_learning_interval
                    FROM Morphs
                    """,
            ).fetchall()

            for row in card_morphs_raw:
                key = row[0]
                interval = row[1]
                if interval >= am_config.interval_for_known_morphs:
                    learning_status = ankimorphs_globals.STATUS_KNOWN
                elif interval > 0:
                    learning_status = ankimorphs_globals.STATUS_LEARNING
                else:
                    learning_status = ankimorphs_globals.STATUS_UNKNOWN

                morph_status_dict[key] = learning_status

        return morph_status_dict

    def get_card_morph_map_cache(self) -> dict[int, list[Morpheme]]:
        card_morph_map_cache: dict[int, list[Morpheme]] = {}

        # Sorting the morphs (ORDER BY) is crucial to avoid bugs
        card_morph_map_cache_raw = self.con.execute(
            """
            SELECT Card_Morph_Map.card_id, Morphs.lemma, Morphs.inflection, Morphs.highest_lemma_learning_interval, Morphs.highest_inflection_learning_interval
            FROM Card_Morph_Map
            INNER JOIN Morphs ON
                Card_Morph_Map.morph_lemma = Morphs.lemma AND Card_Morph_Map.morph_inflection = Morphs.inflection
            ORDER BY Morphs.lemma, Morphs.inflection
            """,
        ).fetchall()

        for row in card_morph_map_cache_raw:
            card_id = row[0]
            morph = Morpheme(
                lemma=row[1],
                inflection=row[2],
                highest_lemma_learning_interval=row[3],
                highest_inflection_learning_interval=row[4],
            )

            if card_id not in card_morph_map_cache:
                card_morph_map_cache[card_id] = [morph]
            else:
                card_morph_map_cache[card_id].append(morph)

        return card_morph_map_cache

    def get_card_scoring_morph_map_cache(
        self, evaluate_inflection: bool
    ) -> dict[int, list[Morpheme]]:
        """
        Returns sentence morphs (from modify_field) with intervals looked up from
        knowledge morphs (from read_field). Used when read_field != modify_field.
        """
        card_scoring_morph_map_cache: dict[int, list[Morpheme]] = {}

        if evaluate_inflection:
            # Match on exact lemma + inflection
            # Morphs that don't exist in knowledge base get interval 0
            query = """
                SELECT
                    Card_Scoring_Morph_Map.card_id,
                    Card_Scoring_Morph_Map.morph_lemma,
                    Card_Scoring_Morph_Map.morph_inflection,
                    COALESCE(Morphs.highest_lemma_learning_interval, 0),
                    COALESCE(Morphs.highest_inflection_learning_interval, 0)
                FROM Card_Scoring_Morph_Map
                LEFT JOIN Morphs ON
                    Card_Scoring_Morph_Map.morph_lemma = Morphs.lemma AND
                    Card_Scoring_Morph_Map.morph_inflection = Morphs.inflection
                ORDER BY Card_Scoring_Morph_Map.morph_lemma, Card_Scoring_Morph_Map.morph_inflection
            """
        else:
            # Match on lemma only, use max interval for that lemma
            # This allows any inflection of a known lemma to count as known
            query = """
                SELECT
                    Card_Scoring_Morph_Map.card_id,
                    Card_Scoring_Morph_Map.morph_lemma,
                    Card_Scoring_Morph_Map.morph_inflection,
                    COALESCE(lemma_intervals.interval, 0),
                    COALESCE(lemma_intervals.interval, 0)
                FROM Card_Scoring_Morph_Map
                LEFT JOIN (
                    SELECT lemma, MAX(highest_lemma_learning_interval) as interval
                    FROM Morphs
                    GROUP BY lemma
                ) AS lemma_intervals ON Card_Scoring_Morph_Map.morph_lemma = lemma_intervals.lemma
                ORDER BY Card_Scoring_Morph_Map.morph_lemma, Card_Scoring_Morph_Map.morph_inflection
            """

        card_scoring_morph_map_cache_raw = self.con.execute(query).fetchall()

        for row in card_scoring_morph_map_cache_raw:
            card_id = row[0]
            morph = Morpheme(
                lemma=row[1],
                inflection=row[2],
                highest_lemma_learning_interval=row[3],
                highest_inflection_learning_interval=row[4],
            )

            if card_id not in card_scoring_morph_map_cache:
                card_scoring_morph_map_cache[card_id] = [morph]
            else:
                card_scoring_morph_map_cache[card_id].append(morph)

        return card_scoring_morph_map_cache

    def get_am_cards_data_dict(
        self,
        note_type_id: NotetypeId | None,
        include_tags: str,  # whitespace separated string
        exclude_tags: str,  # whitespace separated string
    ) -> dict[CardId, AnkiMorphsCardData]:
        assert mw is not None
        assert mw.col.db is not None
        assert note_type_id is not None

        query = """
            SELECT card_id, note_id, note_type_id, card_type, tags
            FROM Cards
            WHERE note_type_id = ?
        """

        params: list[Any] = [note_type_id]

        if len(include_tags) > 0:
            required_conditions = " AND ".join(["tags LIKE ?"] * len(include_tags))
            query += f" AND {required_conditions}"
            params.extend([f"% {tag} %" for tag in include_tags])

        if len(exclude_tags) > 0:
            excluded_conditions = " AND ".join(["tags NOT LIKE ?"] * len(exclude_tags))
            query += f" AND {excluded_conditions}"
            params.extend([f"% {tag} %" for tag in exclude_tags])

        result = self.con.execute(query, tuple(params)).fetchall()

        am_db_row_data_dict: dict[CardId, AnkiMorphsCardData] = {}
        for am_data in map(AnkiMorphsCardData, result):
            am_db_row_data_dict[am_data.card_id] = am_data

        return am_db_row_data_dict

    # the cache needs to have a max size to maintain garbage collection
    @functools.lru_cache(maxsize=131072)
    def get_morph_priorities_from_collection(
        self, only_lemma_priorities: bool
    ) -> dict[tuple[str, str], int]:
        # Sorting the morphs (ORDER BY) is crucial to avoid bugs
        morphs_query = self.con.execute(
            """
            SELECT morph_lemma, morph_inflection
            FROM Card_Morph_Map
            ORDER BY morph_lemma, morph_inflection
            """,
        ).fetchall()

        intermediate_morph_list = []

        if only_lemma_priorities:
            for lemma, _ in morphs_query:
                intermediate_morph_list.append((lemma, lemma))
        else:
            for lemma, inflection in morphs_query:
                intermediate_morph_list.append((lemma, inflection))

        morphs_sorted_amount: dict[tuple[str, str], int] = dict(
            Counter(intermediate_morph_list).most_common()
        )

        morph_priorities: dict[tuple[str, str], int] = {}

        # Reverse the values, the lower the priority number is, the more it is prioritized.
        # Note: we can use a shortcut of providing the same priority (index) for both
        # the lemma and the inflection since we generate the intermediate lists from
        # scratch every recalc, so which ever ends up being used will have the correct value.
        for index, key in enumerate(morphs_sorted_amount):
            morph_priorities[key] = index
            # print(f"key: {key}, index: {index}")

        return morph_priorities

    def get_known_lemmas_with_count(
        self, highest_lemma_learning_interval: int
    ) -> list[tuple[str, int]]:
        """
        returns: (lemma, lemma_count)
        """
        with self.con:
            return self.con.execute(
                """
                SELECT morph_lemma, COUNT(morph_lemma)
                FROM Card_Morph_Map cmm
                INNER JOIN Morphs m ON
                    cmm.morph_lemma = m.lemma AND cmm.morph_inflection = m.inflection
                WHERE m.highest_lemma_learning_interval >= ?
                GROUP BY morph_lemma
                ORDER BY morph_lemma
                """,
                (highest_lemma_learning_interval,),
            ).fetchall()

    def get_known_lemmas_and_inflections_with_count(
        self, highest_inflection_learning_interval: int
    ) -> list[tuple[str, str, int]]:
        """
        returns: (lemma, inflection, inflection_count)
        """
        with self.con:
            return self.con.execute(
                """
                SELECT morph_lemma, morph_inflection, COUNT(morph_inflection)
                FROM Card_Morph_Map cmm
                INNER JOIN Morphs m ON
                    cmm.morph_lemma = m.lemma AND cmm.morph_inflection = m.inflection
                WHERE m.highest_inflection_learning_interval >= ?
                GROUP BY morph_lemma, morph_inflection
                ORDER BY morph_lemma, morph_inflection
                """,
                (highest_inflection_learning_interval,),
            ).fetchall()

    def print_table(self, table: str) -> None:
        try:
            # using f-string is terrible practice, but this is a trivial operation
            for row in self.con.execute(f"SELECT * FROM {table}"):
                print(f"row: {row}")
        except sqlite3.OperationalError:
            print(f"table: '{table}' does not exist")

    def print_table_info(self, table: str) -> None:
        with self.con:
            # using f-string is terrible practice, but this is a trivial operation
            result = self.con.execute(f"PRAGMA table_info('{table}')")
            print(f"PRAGMA {table}: {result.fetchall()}")

    def drop_all_tables(self) -> None:
        with self.con:
            self.con.execute("DROP TABLE IF EXISTS Cards;")
            self.con.execute("DROP TABLE IF EXISTS Morphs;")
            self.con.execute("DROP TABLE IF EXISTS Card_Morph_Map;")
            self.con.execute("DROP TABLE IF EXISTS Card_Scoring_Morph_Map;")
            self.con.execute("DROP TABLE IF EXISTS Seen_Morphs;")

    @staticmethod
    def drop_seen_morphs_table() -> None:
        am_db = AnkiMorphsDB()
        with am_db.con:
            am_db.con.execute("DROP TABLE IF EXISTS Seen_Morphs;")

    @staticmethod
    def rebuild_seen_morphs_today() -> None:
        # The duration of this operation can be long depending
        # on how many cards have been reviewed today and the
        # quality of the user hardware. To prevent long freezes
        # with no feedback, we run this on a background thread.
        assert mw is not None

        mw.progress.start(label="Updating seen morphs...")
        operation = QueryOp(
            parent=mw,
            op=lambda _: AnkiMorphsDB.rebuild_seen_morphs_today_background(),
            success=lambda _: _on_success(),
        )
        operation.failure(_on_failure)
        operation.with_progress().run_in_background()

    @staticmethod
    def rebuild_seen_morphs_today_background() -> None:
        # sqlite can only use a db instance in the same thread it was created
        # on, which is why this function is static.
        assert mw is not None

        am_db = AnkiMorphsDB()
        cards_studied_today: Sequence[int] = AnkiMorphsDB.get_new_cards_seen_today()

        where_query_string = ""
        if len(cards_studied_today) > 0:
            where_query_string = (
                "WHERE card_id IN (" + ",".join(map(str, cards_studied_today)) + ")"
            )

        am_db.drop_seen_morphs_table()
        am_db.create_seen_morph_table()

        with am_db.con:
            # don't insert any morphs if no cards have been studied
            if where_query_string != "":
                am_db.con.execute(
                    """
                        INSERT OR IGNORE INTO Seen_Morphs (lemma, inflection)
                        SELECT morph_lemma, morph_inflection
                        FROM Card_Morph_Map
                        """
                    + where_query_string
                )
        am_db.con.close()

        am_db.insert_names_to_seen_morphs()

    @staticmethod
    def get_new_cards_seen_today() -> Sequence[int]:
        # SearchNode handles escaping characters for us (e.g. 'am_known' -> 'am\_known')
        # it is also more robust to api changes than hardcoded strings.
        # An example of the resulting total_search_string is:
        #   "(introduced:1 note:ankimorphs\_sub2srs OR introduced:1 note:Basic) OR is:buried tag:am-known-manually"
        assert mw is not None

        am_config = AnkiMorphsConfig()

        total_search_string = "("
        for _filter in am_config.filters:
            if _filter.read:
                search_string = mw.col.build_search_string(
                    SearchNode(introduced_in_days=1), SearchNode(note=_filter.note_type)
                )
                total_search_string += search_string + " OR "

        known_and_skipped_search_string = mw.col.build_search_string(
            SearchNode(card_state=SearchNode.CARD_STATE_BURIED),
            SearchNode(tag=am_config.tag_known_manually),
        )

        total_search_string = total_search_string[:-4]  # remove last " OR "
        total_search_string += ") OR " + known_and_skipped_search_string

        known_and_skipped_cards: Sequence[int] = mw.col.find_cards(total_search_string)
        return known_and_skipped_cards

    @staticmethod
    def insert_names_to_seen_morphs() -> None:
        name_morphs: list[tuple[str, str]] = get_names_from_file_as_morphs()
        am_db = AnkiMorphsDB()

        with am_db.con:
            am_db.con.executemany(
                """
                    INSERT OR IGNORE INTO Seen_Morphs VALUES (?, ?)
                    """,
                name_morphs,
            )
        am_db.con.close()


def _on_success() -> None:
    # This function runs on the main thread.
    assert mw is not None
    assert mw.progress is not None
    mw.progress.finish()


def _on_failure(error: Exception | sqlite3.OperationalError) -> None:
    # This function runs on the main thread.
    assert mw is not None
    assert mw.progress is not None
    mw.progress.finish()

    if isinstance(error, sqlite3.OperationalError):
        # schema has been changed
        with AnkiMorphsDB() as am_db:
            am_db.drop_all_tables()
        return

    raise error
