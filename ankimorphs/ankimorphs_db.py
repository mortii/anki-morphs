import hashlib
import sqlite3


class AnkiMorphsDB:
    """
    A card can have many morphs
    morphs can be on many cards
    so we need a many-to-many db structure:
    card -> card_morph <- morph
    """

    def __init__(self):
        self.con: sqlite3.Connection = sqlite3.connect("ankimorphs.db")
        self.create_morph_table()
        self.create_cards_table()
        self.create_card_morph_table()

    def create_cards_table(self) -> bool:
        try:
            with self.con:
                self.con.execute(
                    """
                    CREATE TABLE card
                    (
                        id INTEGER PRIMARY KEY ASC,
                        just_reviewed INTEGER
                    )
                    """
                )
                return True
        except sqlite3.OperationalError:
            return False  # already exists, etc.

    def create_card_morph_table(self):
        try:
            with self.con:
                self.con.execute(
                    """
                    CREATE TABLE card_morph
                    (
                        card_id INTEGER,
                        morph_id INTEGER,
                        FOREIGN KEY(card_id) REFERENCES card(id),
                        FOREIGN KEY(morph_id) REFERENCES morph(id)
                    )
                    """
                )
                return True
        except sqlite3.OperationalError:
            return False  # already exists, etc.

    def create_morph_table(self) -> bool:
        try:
            with self.con:
                self.con.execute(
                    """
                    CREATE TABLE morph
                    (
                        id INTEGER PRIMARY KEY ASC,
                        norm TEXT,
                        base TEXT,
                        inflected TEXT,
                        read TEXT,
                        pos TEXT,
                        sub_pos TEXT,
                        is_base INTEGER
                    )
                    """
                )
                return True
        except sqlite3.OperationalError:
            return False  # already exists, etc.

    def insert_many_into_card_table(self, card_list: list) -> bool:
        try:
            with self.con:
                self.con.executemany(
                    """
                    INSERT OR IGNORE INTO card VALUES
                    (
                       :id,
                       :just_reviewed
                    )
                    """,
                    card_list,
                )
                return True
        except sqlite3.IntegrityError:
            return False  # already exists

    def insert_into_card_table(self, card: dict) -> bool:
        try:
            with self.con:
                self.con.execute(
                    """
                    INSERT INTO card VALUES
                    (
                       :id,
                       :just_reviewed
                    )
                    """,
                    card,
                )
                return True
        except sqlite3.IntegrityError:
            return False  # already exists

    def insert_into_card_morph_table(self, card_morph: dict) -> bool:
        try:
            with self.con:
                self.con.execute(
                    """
                    INSERT INTO card_morph VALUES
                    (
                       :card_id,
                       :morph_id
                    )
                    """,
                    card_morph,
                )
                return True
        except sqlite3.IntegrityError:
            return False  # already exists

    def insert_into_morph_table(self, morph: dict) -> bool:
        try:
            with self.con:
                self.con.execute(
                    """
                    INSERT INTO morph VALUES
                    (
                       :id,
                       :norm,
                       :base,
                       :inflected,
                       :read,
                       :pos,
                       :sub_pos,
                       :is_base
                    )
                    """,
                    morph,
                )
                return True
        except sqlite3.IntegrityError:
            return False  # already exists

    def insert_many_into_morph_table(self, morph_list: list) -> bool:
        try:
            with self.con:
                self.con.executemany(
                    """
                    INSERT OR IGNORE INTO morph VALUES
                    (
                       :id,
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

            # with self.con:
            #     for row in self.con.execute("SELECT * FROM morph"):
            #         print(f"row: {row}")

            return True
        except sqlite3.IntegrityError:
            # except KeyError:
            return False  # already exists

    def insert_many_into_card_morph_table(self, card_morph_list: list) -> bool:
        try:
            with self.con:
                self.con.executemany(
                    """
                    INSERT OR IGNORE INTO card_morph VALUES
                    (
                       :card_id,
                       :morph_id
                    )
                    """,
                    card_morph_list,
                )

            return True
        except sqlite3.IntegrityError:
            # except KeyError:
            return False  # already exists

    @staticmethod
    def get_morph_hash(morph: dict) -> int:
        # sqllite integers are max 2^(63)-1 = 9,223,372,036,854,775,807
        # The chance of hash collision is 50% when sqrt(2^(n/2)) where n is bits of the hash
        # With 64 bits the prob of collision
        # becomes sqrt(2^(64/2)) = 65,536
        byte_string = (morph["norm"] + morph["inflected"]).encode()
        hash_int = int.from_bytes(hashlib.sha256(byte_string).digest()[:7], "little")
        return hash_int

    def print_table(self, table):
        for row in self.con.execute("SELECT * FROM card_morph"):
            print(f"row: {row}")

    def test_insert_card(self, card_dict):
        try:
            with self.con:
                self.con.execute(
                    "INSERT OR IGNORE INTO card_morph VALUES(:id, :just_reviewed)",
                    card_dict,
                )
        # except sqlite3.IntegrityError:
        except KeyError:
            return False  # already exists
