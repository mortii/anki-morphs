import sqlite3

from .ankimorphs_db import AnkiMorphsDB


class MorphToolbarStats:
    # TODO: have a settings option to
    #  see the true 'known' morphs
    #  instead of seen morphs like
    #  it is now?
    def __init__(self) -> None:
        self.unique_morphs = "U: ?"
        self.all_morphs = "A: ?"
        self.update_stats()

    def update_stats(self) -> None:
        try:
            am_db = AnkiMorphsDB()
        except TypeError:
            # The toolbar initiates before the profile,
            # when this happens, the path to the db can't
            # be found, and we get a type error.
            return

        am_db.create_morph_table()

        try:
            all_unique_morphs = am_db.con.execute(
                """
                SELECT COUNT(*)
                FROM Morphs
                WHERE highest_learning_interval > 0 AND is_lemma
                """
            ).fetchone()[0]

            all_morphs = am_db.con.execute(
                """
                SELECT COUNT(*)
                FROM Morphs
                WHERE highest_learning_interval > 0
                """
            ).fetchone()[0]
            am_db.con.close()
        except sqlite3.OperationalError:
            # database schema has changed
            return

        self.unique_morphs = f"U: {all_unique_morphs}"
        self.all_morphs = f"A: {all_morphs}"
