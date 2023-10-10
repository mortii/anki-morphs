from aqt.utils import tooltip

from ankimorphs.ankimorphs_db import AnkiMorphsDB


def get_unique_morph_toolbar_stats() -> tuple[str, str]:
    am_db = AnkiMorphsDB()
    all_unique_morphs = am_db.con.execute(
        """
        SELECT COUNT(*)
        FROM Morph
        WHERE highest_learning_interval > 1 AND is_base
        """
    ).fetchone()[0]
    am_db.con.close()

    name = f"U: {all_unique_morphs}"
    details = "U = Known Unique Morphs"
    return name, details


def get_all_morph_toolbar_stats() -> tuple[str, str]:
    am_db = AnkiMorphsDB()
    all_morphs = am_db.con.execute(
        """
        SELECT COUNT(*)
        FROM Morph
        WHERE highest_learning_interval > 1
        """
    ).fetchone()[0]
    am_db.con.close()

    name = f"A: {all_morphs}"
    details = "A = All Known Morphs"
    return name, details


def on_morph_stats_clicked() -> None:
    tooltip("U = Known Unique Morphs<br>A = All Known Morphs")
