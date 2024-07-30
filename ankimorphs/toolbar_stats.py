import sqlite3

from .ankimorphs_config import AnkiMorphsConfig
from .ankimorphs_db import AnkiMorphsDB


class MorphToolbarStats:
    def __init__(self) -> None:
        self.lemmas = "L: ?"
        self.inflections = "I: ?"
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

        if am_config.toolbar_stats_use_known:
            learning_interval = am_config.interval_for_known_morphs

        try:
            known_lemmas = am_db.con.execute(
                """
                SELECT COUNT(DISTINCT lemma)
                FROM Morphs
                WHERE highest_inflection_learning_interval >= ?
                """,
                (learning_interval,),
            ).fetchone()[0]

            known_inflections = am_db.con.execute(
                """
                SELECT COUNT(*)
                FROM Morphs
                WHERE highest_inflection_learning_interval >= ?
                """,
                (learning_interval,),
            ).fetchone()[0]
            am_db.con.close()
        except sqlite3.OperationalError:
            # database schema has changed
            return

        self.lemmas = f"L: {known_lemmas}"
        self.inflections = f"I: {known_inflections}"
