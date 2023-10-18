import sqlite3
from typing import Optional, Union


class AnkiMorphsDB:
    """
    A card can have many morphs
    morphs can be on many cards
    so we need a many-to-many db structure:
    Cards -> Card_Morph_Map <- Morphs
    """

    def __init__(self) -> None:
        self.con: sqlite3.Connection = sqlite3.connect("ankimorphs.db")

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

    def get_card_morphs(self, card_id: int) -> set[str]:
        card_morphs: set[str] = set("")

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
                card_morphs.add(row[0] + row[1])

        return card_morphs

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

    def insert_card_morphs_into_seen_table(self, card_id: int) -> None:
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

    def get_inflected_morphs_of_card(self, card_id: int) -> Optional[list[str]]:
        inflected_morphs: list[str] = []

        with self.con:
            inflected_morphs_raw = self.con.execute(
                """
                    SELECT morph_inflected
                    FROM Card_Morph_Map
                    INNER JOIN Morphs ON
                        Card_Morph_Map.morph_norm = Morphs.norm AND Card_Morph_Map.morph_inflected = Morphs.inflected
                    WHERE Card_Morph_Map.card_id = ?
                    """,
                (card_id,),
            ).fetchall()

            for row in inflected_morphs_raw:
                # print(f"unknown_morphs_raw row: {inflected_morphs_raw}")
                inflected_morphs.append(row[0])

        print(f"inflected_morphs in db: {inflected_morphs}")
        if len(inflected_morphs) == 0:
            return None

        return inflected_morphs

    def get_unknown_inflected_morphs_of_card(self, card_id: int) -> Optional[list[str]]:
        unknown_morphs: list[str] = []

        with self.con:
            unknown_morphs_raw = self.con.execute(
                """
                    SELECT morph_inflected
                    FROM Card_Morph_Map
                    INNER JOIN Morphs ON
                        Card_Morph_Map.morph_norm = Morphs.norm AND Card_Morph_Map.morph_inflected = Morphs.inflected
                    WHERE Card_Morph_Map.card_id = ? AND Morphs.highest_learning_interval = 0
                    """,
                (card_id,),
            ).fetchall()

            for row in unknown_morphs_raw:
                # print(f"unknown_morphs_raw row: {unknown_morphs_raw}")
                unknown_morphs.append(row[0])

        print(f"unknown_morphs in db: {unknown_morphs}")
        if len(unknown_morphs) == 0:
            return None

        return unknown_morphs

    def get_unknown_morphs_of_card(self, card_id: int) -> Optional[set[str]]:
        unknown_morphs: set[str] = set()

        with self.con:
            unknown_morphs_raw = self.con.execute(
                """
                    SELECT morph_norm, morph_inflected
                    FROM Card_Morph_Map
                    INNER JOIN Morphs ON
                        Card_Morph_Map.morph_norm = Morphs.norm AND Card_Morph_Map.morph_inflected = Morphs.inflected
                    WHERE Card_Morph_Map.card_id = ? AND Morphs.highest_learning_interval = 0
                    """,
                (card_id,),
            ).fetchall()

            for row in unknown_morphs_raw:
                # print(f"unknown_morphs_raw row: {unknown_morphs_raw}")
                unknown_morphs.add(row[0] + row[1])

        print(f"unknown_morphs in db: {unknown_morphs}")
        if len(unknown_morphs) == 0:
            return None

        return unknown_morphs

    def print_table(self, table: str) -> None:
        # using f-string is terrible practice, but this is a trivial operation
        for row in self.con.execute(f"SELECT * FROM {table}"):
            print(f"row: {row}")

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
    def drop_seen_morph_table() -> None:
        am_db = AnkiMorphsDB()
        with am_db.con:
            am_db.con.execute("DROP TABLE IF EXISTS Seen_Morphs;")
