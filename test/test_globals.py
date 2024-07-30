from pathlib import Path

PATH_TESTS_DATA = Path(Path(__file__).parent, "data")
PATH_TESTS_DATA_CORRECT_OUTPUTS = Path(PATH_TESTS_DATA, "correct_outputs")
PATH_TESTS_DATA_TESTS_OUTPUTS = Path(PATH_TESTS_DATA, "tests_outputs")
PATH_TESTS_DATA_DBS = Path(PATH_TESTS_DATA, "am_dbs")
PATH_DB_COPY = Path(PATH_TESTS_DATA_DBS, "temp_copied.db")
PATH_CARD_COLLECTIONS = Path(PATH_TESTS_DATA, "card_collections")
