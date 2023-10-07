import sqlite3
from typing import Union

from aqt import mw
from aqt.qt import QMessageBox  # pylint:disable=no-name-in-module


class AnkiMorphsDB:
    """
    A card can have many morphs
    morphs can be on many cards
    so we need a many-to-many db structure:
    Card -> Card_Morph_Map <- Morph
    """

    def __init__(self) -> None:
        self.con: sqlite3.Connection = sqlite3.connect("ankimorphs.db")
        # self.create_all_tables()

    def create_all_tables(self) -> None:
        self.create_morph_table()
        self.create_cards_table()
        self.create_card_morph_map_table()

    def create_cards_table(self) -> None:
        with self.con:
            self.con.execute(
                """
                    CREATE TABLE IF NOT EXISTS Card
                    (
                        id INTEGER PRIMARY KEY ASC,
                        note_id INTEGER,
                        queue INTEGER,
                        interval INTEGER
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

    def insert_many_into_card_table(
        self, card_list: list[dict[str, Union[int, str, bool]]]
    ) -> None:
        with self.con:
            self.con.executemany(
                """
                    INSERT OR IGNORE INTO Card VALUES
                    (
                       :id,
                       :note_id,
                       :queue,
                       :interval
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

    def print_table(self, table: str) -> None:
        """
        tables: Card, Card_Morph_Map, Morph
        """
        # using f-string is terrible practice, but this is a trivial operation
        for row in self.con.execute(f"SELECT * FROM {table}"):
            print(f"row: {row}")

    def print_table_info(self, table: str) -> None:
        """
        tables: Card, Card_Morph_Map, Morph
        """
        with self.con:
            # using f-string is terrible practice, but this is a trivial operation
            result = self.con.execute(f"PRAGMA table_info('{table}')")
            print(f"PRAGMA {table}: {result.fetchall()}")

    def drop_all_tables(self) -> None:
        with self.con:
            self.con.execute("DROP TABLE IF EXISTS Morph;")
            self.con.execute("DROP TABLE IF EXISTS Card_Morph_Map;")
            self.con.execute("DROP TABLE IF EXISTS Card;")

    @staticmethod
    def drop_all_tables_with_confirmation() -> None:
        title = "Confirmation"
        text = "Are you sure you want to delete the ankimorphs.db cache?"
        warning_box = QMessageBox(mw)
        warning_box.setWindowTitle(title)
        warning_box.setIcon(QMessageBox.Icon.Warning)
        warning_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        warning_box.setText(text)
        answer = warning_box.exec()
        if answer == QMessageBox.StandardButton.Yes:
            am_db = AnkiMorphsDB()
            with am_db.con:
                am_db.con.execute("DROP TABLE IF EXISTS Morph;")
                am_db.con.execute("DROP TABLE IF EXISTS Card_Morph_Map;")
                am_db.con.execute("DROP TABLE IF EXISTS Card;")
