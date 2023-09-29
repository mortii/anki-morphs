import hashlib
import sqlite3


class AnkiMorphsDB:
    """
    A card can have many morphs
    morphs can be on many cards
    so we need a many-to-many db structure:
    Card -> Card_Morph_Map <- Morph
    """

    def __init__(self):
        self.con: sqlite3.Connection = sqlite3.connect("ankimorphs.db")
        self.create_morph_table()
        self.create_cards_table()
        self.create_card_morph_map_table()

    def create_cards_table(self):
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Card
                    (
                        id INTEGER PRIMARY KEY ASC,
                        type INTEGER,
                        interval INTEGER
                    )
                    """
            )

    def create_card_morph_map_table(self):
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

    def create_morph_table(self):
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Morph
                    (
                        norm TEXT,
                        base TEXT,
                        inflected TEXT,
                        read TEXT,
                        pos TEXT,
                        sub_pos TEXT,
                        is_base INTEGER,
                        PRIMARY KEY (norm, inflected)
                    )
                    """
            )

    def insert_many_into_card_table(self, card_list: list):
        with self.con:
            self.con.executemany(
                """
                    INSERT OR IGNORE INTO Card VALUES
                    (
                       :id,
                       :type,
                       :interval
                    )
                    """,
                card_list,
            )

    def insert_many_into_morph_table(self, morph_list: list):
        with self.con:
            self.con.executemany(
                """
                    INSERT OR IGNORE INTO Morph VALUES
                    (
                       :norm,
                       :base,
                       :inflected,
                       :read,
                       :pos,
                       :sub_pos,
                       :is_base
                    )
                    """,
                morph_list,
            )

    def insert_many_into_card_morph_map_table(self, card_morph_list: list):
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

    def print_table(self, table):
        for row in self.con.execute("SELECT * FROM Card_Morph_Map"):
            print(f"row: {row}")
