from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from test.fake_configs import default_config_dict
from test.fake_db import FakeDB
from test.test_globals import (
    PATH_CARD_COLLECTIONS,
    PATH_DB_COPY,
    PATH_TESTS_DATA,
    PATH_TESTS_DATA_DBS,
    PATH_TESTS_DATA_TESTS_OUTPUTS,
)
from typing import Any
from unittest import mock

import anki
import aqt
import pytest
from _pytest.fixtures import SubRequest
from anki.collection import Collection
from aqt import setupLangAndBackend
from aqt.reviewer import Reviewer

from ankimorphs import (
    ankimorphs_config,
    ankimorphs_db,
    ankimorphs_globals,
    known_morphs_exporter,
    name_file_utils,
    progress_utils,
    reviewing_utils,
)
from ankimorphs.generators import generators_utils, generators_window
from ankimorphs.morphemizers import spacy_wrapper
from ankimorphs.recalc import (
    anki_data_utils,
    caching,
    morph_priority_utils,
    recalc_main,
)


class FakeEnvironmentParams:
    def __init__(  # pylint:disable=too-many-arguments
        self,
        collection: str | None = None,
        config: dict[str, Any] | None = None,
        am_db: str | None = None,
        frequency_files_dir: str | None = None,
        known_morphs_dir: str | None = None,
    ):
        self.collection = collection
        self.config = config
        self.am_db = am_db
        self.frequency_files_dir = frequency_files_dir
        self.known_morphs_dir = known_morphs_dir


class FakeEnvironment:

    def __init__(  # pylint:disable=too-many-arguments
        self,
        mock_mw: mock.Mock,
        mock_db: FakeDB,
        config: dict[str, Any],
        frequency_files_dir: str,
        known_morphs_dir: str,
        original_collection: Collection,
        modified_collection: Collection,
    ) -> None:
        self.mock_mw = mock_mw
        self.mock_db = mock_db
        self.config = config
        self.frequency_files_dir = frequency_files_dir
        self.known_morphs_dir = known_morphs_dir
        self.original_collection = original_collection
        self.modified_collection = modified_collection


@pytest.fixture(scope="function")
def fake_environment_fixture(  # pylint:disable=too-many-locals, too-many-statements
    request: SubRequest,
) -> Iterator[FakeEnvironment | None]:
    # Sending arguments to a fixture requires a somewhat hacky
    # approach of using the "request" fixture as an input, which
    # will then contain the parameters

    try:
        _collection_file_name: str = request.param.collection
        if _collection_file_name is None:
            # this is a small collection, otherwise a completely arbitrary choice
            _collection_file_name = "ignore_names_txt_collection"
        assert isinstance(_collection_file_name, str)

        _config_data: dict[str, Any] = request.param.config
        if _config_data is None:
            _config_data = default_config_dict
        assert isinstance(_config_data, dict)

        _am_db_name: str | None = request.param.am_db
        if _am_db_name is None:
            _am_db_name = "empty_skeleton.db"
        assert isinstance(_am_db_name, str)

        _frequency_files_dir: str | None = request.param.frequency_files_dir
        if _frequency_files_dir is None:
            _frequency_files_dir = "correct_outputs"
        assert isinstance(_frequency_files_dir, str)

        _known_morphs_dir: str | None = request.param.known_morphs_dir
        if _known_morphs_dir is None:
            _known_morphs_dir = "known-morphs-valid"
        assert isinstance(_known_morphs_dir, str)

    except AttributeError as _error:
        print('Missing "@pytest.mark.parametrize"')
        raise _error

    path_original_collection = Path(
        PATH_CARD_COLLECTIONS, f"{_collection_file_name}.anki2"
    )
    path_original_collection_media = Path(
        PATH_CARD_COLLECTIONS, f"{_collection_file_name}.media"
    )
    collection_path_duplicate = Path(
        PATH_CARD_COLLECTIONS, f"duplicate_{_collection_file_name}.anki2"
    )
    collection_path_duplicate_media = Path(
        PATH_CARD_COLLECTIONS, f"duplicate_{_collection_file_name}.media"
    )
    fake_morphemizers_path = Path(PATH_TESTS_DATA, "morphemizers")
    test_db_original_path = Path(PATH_TESTS_DATA_DBS, _am_db_name)

    # If the destination already exists, it will be replaced
    shutil.copyfile(path_original_collection, collection_path_duplicate)
    shutil.copyfile(test_db_original_path, PATH_DB_COPY)

    mock_mw = mock.Mock(spec=aqt.mw)
    mock_mw.col = Collection(str(collection_path_duplicate))
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )
    mock_mw.pm.profileFolder.return_value = os.path.join("test", "data")
    mock_mw.progress.want_cancel.return_value = False
    mock_mw.addonManager.getConfig.return_value = _config_data
    mock_mw.reviewer = Reviewer(mock_mw)
    mock_mw.reviewer._showQuestion = lambda: None

    patch_recalc_mw = mock.patch.object(recalc_main, "mw", mock_mw)
    patch_caching_mw = mock.patch.object(caching, "mw", mock_mw)
    patch_progress_mw = mock.patch.object(progress_utils, "mw", mock_mw)
    patch_am_db_mw = mock.patch.object(ankimorphs_db, "mw", mock_mw)
    patch_config_mw = mock.patch.object(ankimorphs_config, "mw", mock_mw)
    patch_name_file_utils_mw = mock.patch.object(name_file_utils, "mw", mock_mw)
    patch_anki_data_utils_mw = mock.patch.object(anki_data_utils, "mw", mock_mw)
    patch_reviewing_mw = mock.patch.object(reviewing_utils, "mw", mock_mw)
    patch_gw_mw = mock.patch.object(generators_window, "mw", mock_mw)
    patch_morph_priority_mw = mock.patch.object(morph_priority_utils, "mw", mock_mw)
    patch_morphs_exporter_mw = mock.patch.object(known_morphs_exporter, "mw", mock_mw)

    patch_recalc_mw.start()
    patch_caching_mw.start()
    patch_progress_mw.start()
    patch_am_db_mw.start()
    patch_config_mw.start()
    patch_name_file_utils_mw.start()
    patch_anki_data_utils_mw.start()
    patch_reviewing_mw.start()
    patch_gw_mw.start()
    patch_morph_priority_mw.start()
    patch_morphs_exporter_mw.start()

    # 'mw' has to be patched before we can before we can create a db instance
    patch_reviewing_am_db = mock.patch.object(reviewing_utils, "AnkiMorphsDB", FakeDB)
    patch_recalc_am_db = mock.patch.object(recalc_main, "AnkiMorphsDB", FakeDB)
    patch_caching_am_db = mock.patch.object(caching, "AnkiMorphsDB", FakeDB)
    patch_generators_window_am_db = mock.patch.object(
        generators_window, "AnkiMorphsDB", FakeDB
    )
    patch_generators_utils_am_db = mock.patch.object(
        generators_utils, "AnkiMorphsDB", FakeDB
    )
    patch_morphs_exporter_am_db = mock.patch.object(
        known_morphs_exporter, "AnkiMorphsDB", FakeDB
    )

    mock_db = FakeDB()

    # tooltip tries to do gui stuff which breaks test
    mock_tooltip = mock.Mock(spec=aqt.utils.tooltip)
    patch_tooltip = mock.patch.object(reviewing_utils, "tooltip", mock_tooltip)

    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )
    patch_frequency_files_dir = mock.patch.object(
        ankimorphs_globals, "FREQUENCY_FILES_DIR_NAME", _frequency_files_dir
    )
    patch_known_morphs_dir = mock.patch.object(
        ankimorphs_globals, "KNOWN_MORPHS_DIR_NAME", _known_morphs_dir
    )

    patch_reviewing_am_db.start()
    patch_recalc_am_db.start()
    patch_caching_am_db.start()
    patch_generators_window_am_db.start()
    patch_generators_utils_am_db.start()
    patch_morphs_exporter_am_db.start()

    patch_tooltip.start()

    patch_testing_variable.start()
    patch_frequency_files_dir.start()
    patch_known_morphs_dir.start()
    sys.path.append(str(fake_morphemizers_path))

    try:
        yield FakeEnvironment(
            mock_mw=mock_mw,
            mock_db=mock_db,
            config=_config_data,
            known_morphs_dir=_known_morphs_dir,
            frequency_files_dir=_frequency_files_dir,
            original_collection=Collection(str(path_original_collection)),
            modified_collection=mock_mw.col,
        )

    except anki.errors.DBError:
        yield None

    mock_mw.col.close()
    mock_db.con.close()

    patch_recalc_mw.stop()
    patch_caching_mw.stop()
    patch_progress_mw.stop()
    patch_am_db_mw.stop()
    patch_config_mw.stop()
    patch_name_file_utils_mw.stop()
    patch_anki_data_utils_mw.stop()
    patch_reviewing_mw.stop()
    patch_gw_mw.stop()
    patch_morph_priority_mw.stop()
    patch_morphs_exporter_mw.stop()

    patch_reviewing_am_db.stop()
    patch_recalc_am_db.stop()
    patch_caching_am_db.stop()
    patch_generators_window_am_db.stop()
    patch_generators_utils_am_db.stop()
    patch_morphs_exporter_am_db.stop()
    patch_tooltip.stop()

    patch_testing_variable.stop()
    patch_frequency_files_dir.stop()
    patch_known_morphs_dir.stop()
    sys.path.remove(str(fake_morphemizers_path))

    Path.unlink(PATH_DB_COPY, missing_ok=True)
    Path.unlink(collection_path_duplicate, missing_ok=True)
    shutil.rmtree(path_original_collection_media, ignore_errors=True)
    shutil.rmtree(collection_path_duplicate_media, ignore_errors=True)

    for file in PATH_TESTS_DATA_TESTS_OUTPUTS.iterdir():
        if file.is_file():
            file.unlink()
