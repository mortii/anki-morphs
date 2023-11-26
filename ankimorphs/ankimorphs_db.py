import os
import sqlite3
from collections.abc import Sequence
from typing import Any, Optional, Union

from anki.collection import Collection, SearchNode
from aqt import mw
from aqt.operations import QueryOp

from .config import AnkiMorphsConfig
from .name_file_utils import get_names_from_file_as_morphs


class AnkiMorphsDB:  # pylint:disable=too-many-public-methods
    # A card can have many morphs, morphs can be on many cards
    # therefore we need a many-to-many db structure:
    # Cards -> Card_Morph_Map <- Morphs

    def __init__(self) -> None:
        assert mw is not None
        assert mw.pm is not None
        path: str = os.path.join(mw.pm.profileFolder(), "ankimorphs.db")
        self.con: sqlite3.Connection = sqlite3.connect(path)

    def create_all_tables(self) -> None:
        self.create_morph_table()
        self.create_cards_table()
        self.create_card_morph_map_table()
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
                        fields TEXT,
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
                        morph_norm TEXT,
                        morph_inflected TEXT,
                        FOREIGN KEY(card_id) REFERENCES card(id),
                        FOREIGN KEY(morph_norm, morph_inflected) REFERENCES morph(norm, inflected)
                    )
                    """
            )

    def create_morph_table(self) -> None:
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Morphs
                    (
                        norm TEXT,
                        base TEXT,
                        inflected TEXT,
                        is_base INTEGER,
                        highest_learning_interval INTEGER,
                        PRIMARY KEY (norm, inflected)
                    )
                    """
            )

    def create_seen_morph_table(self) -> None:
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Seen_Morphs
                    (
                        norm TEXT,
                        inflected TEXT,
                        PRIMARY KEY (norm, inflected)
                    )
                    """
            )

    def insert_many_into_card_table(
        self, card_list: list[dict[str, Union[int, str, bool]]]
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
                       :fields,
                       :tags
                    )
                    """,
                card_list,
            )

    def insert_many_into_morph_table(
        self, morph_list: list[dict[str, Union[int, str, bool]]]
    ) -> None:
        with self.con:
            self.con.executemany(
                """
                    INSERT INTO Morphs 
                    VALUES
                    (
                       :norm,
                       :base,
                       :inflected,
                       :is_base,
                       :highest_learning_interval
                    )
                    ON CONFLICT(norm, inflected) DO UPDATE SET
                        highest_learning_interval = :highest_learning_interval
                    WHERE highest_learning_interval < :highest_learning_interval
                """,
                morph_list,
            )

    def insert_many_into_card_morph_map_table(
        self, card_morph_list: list[dict[str, Union[int, str, bool]]]
    ) -> None:
        with self.con:
            self.con.executemany(
                """
                    INSERT OR IGNORE INTO Card_Morph_Map VALUES
                    (
                       :card_id,
                       :morph_norm,
                       :morph_inflected
                    )
                    """,
                card_morph_list,
            )

    def get_readable_card_morphs(self, card_id: int) -> list[tuple[str, str]]:
        card_morphs: list[tuple[str, str]] = []

        with self.con:
            card_morphs_raw = self.con.execute(
                """
                    SELECT morph_norm, morph_inflected
                    FROM Card_Morph_Map
                    WHERE card_id = ?
                    """,
                (card_id,),
            ).fetchall()

            for row in card_morphs_raw:
                card_morphs.append((row[0], row[1]))

        return card_morphs

    def get_all_morphs_seen_today(self) -> set[str]:
        self.create_seen_morph_table()
        card_morphs: set[str] = set("")

        with self.con:
            card_morphs_raw = self.con.execute(
                """
                    SELECT norm, inflected
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
                    INSERT OR IGNORE INTO Seen_Morphs (norm, inflected)
                    SELECT morph_norm, morph_inflected
                    FROM Card_Morph_Map
                    WHERE card_id = ?
                    """,
                (card_id,),
            )

    def get_morphs_of_card(
        self, card_id: int, search_unknowns: bool = False
    ) -> Optional[set[tuple[str, str]]]:
        morphs: set[tuple[str, str]] = set()

        if search_unknowns:
            where_query_string = "WHERE Card_Morph_Map.card_id = ? AND Morphs.highest_learning_interval = 0"
        else:
            where_query_string = "WHERE Card_Morph_Map.card_id = ?"

        with self.con:
            card_morphs = self.con.execute(
                """
                    SELECT DISTINCT morph_norm, morph_inflected
                    FROM Card_Morph_Map
                    INNER JOIN Morphs ON
                        Card_Morph_Map.morph_norm = Morphs.norm AND Card_Morph_Map.morph_inflected = Morphs.inflected
                    """
                + where_query_string,
                (card_id,),
            ).fetchall()

            for card_morph in card_morphs:
                morphs.add((card_morph[0], card_morph[1]))

        if len(morphs) == 0:
            return None

        return morphs

    def get_ids_of_cards_with_same_morphs(
        self, card_id: int, search_unknowns: bool = False
    ) -> Optional[set[int]]:
        # The where_query_string is a necessary hack to overcome the sqlite problem
        # of not allowing variable length parameters

        card_ids: set[int] = set()
        card_morphs: Optional[set[tuple[str, str]]] = self.get_morphs_of_card(
            card_id, search_unknowns
        )

        if card_morphs is None:
            return None

        where_query_string = "WHERE" + "".join(
            [
                f" (morph_norm = '{morph[0]}' AND morph_inflected = '{morph[1]}') OR"
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
                card_ids.add(card_id_raw[0])

        if len(card_ids) == 0:
            return None

        return card_ids

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
            self.con.execute("DROP TABLE IF EXISTS Seen_Morphs;")

    @staticmethod
    def drop_seen_morphs_table() -> None:
        am_db = AnkiMorphsDB()
        with am_db.con:
            am_db.con.execute("DROP TABLE IF EXISTS Seen_Morphs;")

    @staticmethod
    def rebuild_seen_morphs_today() -> None:
        # the duration of this operation can be long depending
        # on how many cards have been reviewed today and the
        # quality of the user hardware. To prevent long freezes
        # with no feedback we run this on a background thread.
        assert mw is not None

        mw.progress.start(label="Updating seen morphs...")
        operation = QueryOp(
            parent=mw,
            op=AnkiMorphsDB.rebuild_seen_morphs_today_background,
            success=_on_success,
        )
        operation.with_progress().run_in_background()

    @staticmethod
    def rebuild_seen_morphs_today_background(collection: Collection) -> None:
        # sqlite can only use a db instance in the same thread it was created
        # on, that is why this function is static.
        del collection  # unused
        assert mw is not None

        am_db = AnkiMorphsDB()
        cards_studied_today: Sequence[int] = AnkiMorphsDB.get_new_cards_seen_today()

        where_query_string = ""
        if len(cards_studied_today) > 0:
            where_query_string = "WHERE" + "".join(
                [f" card_id = {card_id} OR" for card_id in cards_studied_today]
            )
            where_query_string = where_query_string[:-3]  # removes the last " OR"

        am_db.drop_seen_morphs_table()
        am_db.create_seen_morph_table()

        with am_db.con:
            # if no cards are studied then don't insert any morphs
            if where_query_string != "":
                am_db.con.execute(
                    """
                        INSERT OR IGNORE INTO Seen_Morphs (norm, inflected)
                        SELECT morph_norm, morph_inflected
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
        #   "(introduced:1 note:ankimorphs\_sub2srs OR introduced:1 note:Basic) OR is:buried tag:am-known"
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
            SearchNode(tag=am_config.tag_known),
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


def _on_success(result: Any) -> None:
    # This function runs on the main thread.
    del result  # unused
    assert mw is not None
    assert mw.progress is not None
    mw.progress.finish()
