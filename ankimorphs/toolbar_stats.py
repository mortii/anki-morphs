import sqlite3

from .ankimorphs_db import AnkiMorphsDB
from .config import AnkiMorphsConfig


class MorphToolbarStats:
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

        # this is only reached after the profile is loaded

        am_db.create_morph_table()
        am_config = AnkiMorphsConfig()
        learning_interval: int = 1  # seen morphs

        if am_config.recalc_toolbar_stats_use_known is True:
            learning_interval = am_config.recalc_interval_for_known

        try:
            all_unique_morphs = am_db.con.execute(
                """
                SELECT COUNT(*)
                FROM Morphs
                WHERE highest_learning_interval >= ? AND is_lemma
                """,
                (learning_interval,),
            ).fetchone()[0]

            all_morphs = am_db.con.execute(
                """
                SELECT COUNT(*)
                FROM Morphs
                WHERE highest_learning_interval >= ?
                """,
                (learning_interval,),
            ).fetchone()[0]
            am_db.con.close()
        except sqlite3.OperationalError:
            # database schema has changed
            return

        self.unique_morphs = f"U: {all_unique_morphs}"
        self.all_morphs = f"A: {all_morphs}"
