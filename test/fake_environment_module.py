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
    morph_priority_utils,
    name_file_utils,
    progress_utils,
    reviewing_utils,
)
from ankimorphs.generators import (
    generators_utils,
    generators_window,
    priority_file_generator,
    readability_report_generator,
    study_plan_generator,
)
from ankimorphs.morphemizers import spacy_wrapper
from ankimorphs.progression import progression_utils, progression_window
from ankimorphs.recalc import anki_data_utils, caching, recalc_main


class FakeEnvironmentParams:
    def __init__(  # pylint:disable=too-many-arguments
        self,
        collection: str | None = None,
        config: dict[str, Any] | None = None,
        am_db: str | None = None,
        priority_files_dir: str | None = None,
        known_morphs_dir: str | None = None,
    ):
        self.collection = collection
        self.config = config
        self.am_db = am_db
        self.priority_files_dir = priority_files_dir
        self.known_morphs_dir = known_morphs_dir


class FakeEnvironment:

    def __init__(  # pylint:disable=too-many-arguments
        self,
        mock_mw: mock.Mock,
        mock_db: FakeDB,
        config: dict[str, Any],
        priority_files_dir: str,
        known_morphs_dir: str,
        original_collection: Collection,
        modified_collection: Collection,
    ) -> None:
        self.mock_mw = mock_mw
        self.mock_db = mock_db
        self.config = config
        self.priority_files_dir = priority_files_dir
        self.known_morphs_dir = known_morphs_dir
        self.original_collection = original_collection
        self.modified_collection = modified_collection


@pytest.fixture(scope="function")
def fake_environment_fixture(  # pylint:disable=too-many-locals, too-many-statements, too-many-branches
    request: SubRequest,
) -> Iterator[FakeEnvironment | None]:
    # Sending arguments to a fixture requires a somewhat hacky
    # approach of using the "request" fixture as an input, which
    # will then contain the parameters

    try:
        _collection_file_name: str = request.param.collection
        if _collection_file_name is None:
            # note: this collection is chosen as the default because
            # of its small size.
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

        _priority_files_dir: str | None = request.param.priority_files_dir
        if _priority_files_dir is None:
            _priority_files_dir = "correct_outputs"
        assert isinstance(_priority_files_dir, str)

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
    path_duplicate_collection = Path(
        PATH_CARD_COLLECTIONS, f"duplicate_{_collection_file_name}.anki2"
    )
    collection_path_duplicate_media = Path(
        PATH_CARD_COLLECTIONS, f"duplicate_{_collection_file_name}.media"
    )
    fake_morphemizers_path = Path(PATH_TESTS_DATA, "morphemizers")
    test_db_original_path = Path(PATH_TESTS_DATA_DBS, _am_db_name)

    # If the destination already exists, it will be replaced
    shutil.copyfile(path_original_collection, path_duplicate_collection)
    shutil.copyfile(test_db_original_path, PATH_DB_COPY)

    mock_mw = mock.Mock(spec=aqt.mw)
    mock_mw.col = Collection(str(path_duplicate_collection))
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )
    mock_mw.pm.profileFolder.return_value = os.path.join("test", "data")
    mock_mw.progress.want_cancel.return_value = False
    mock_mw.addonManager.getConfig.return_value = _config_data
    mock_mw.reviewer = Reviewer(mock_mw)
    mock_mw.reviewer._showQuestion = lambda: None

    mw_patches = [
        mock.patch.object(recalc_main, "mw", mock_mw),
        mock.patch.object(caching, "mw", mock_mw),
        mock.patch.object(progress_utils, "mw", mock_mw),
        mock.patch.object(ankimorphs_db, "mw", mock_mw),
        mock.patch.object(ankimorphs_config, "mw", mock_mw),
        mock.patch.object(name_file_utils, "mw", mock_mw),
        mock.patch.object(anki_data_utils, "mw", mock_mw),
        mock.patch.object(reviewing_utils, "mw", mock_mw),
        mock.patch.object(generators_window, "mw", mock_mw),
        mock.patch.object(progression_window, "mw", mock_mw),
        mock.patch.object(readability_report_generator, "mw", mock_mw),
        mock.patch.object(generators_utils, "mw", mock_mw),
        mock.patch.object(priority_file_generator, "mw", mock_mw),
        mock.patch.object(study_plan_generator, "mw", mock_mw),
        mock.patch.object(morph_priority_utils, "mw", mock_mw),
        mock.patch.object(known_morphs_exporter, "mw", mock_mw),
    ]

    for mw_patch in mw_patches:
        mw_patch.start()

    # 'mw' has to be patched before we can before we can create a db instance
    am_db_patches = [
        mock.patch.object(reviewing_utils, "AnkiMorphsDB", FakeDB),
        mock.patch.object(recalc_main, "AnkiMorphsDB", FakeDB),
        mock.patch.object(caching, "AnkiMorphsDB", FakeDB),
        mock.patch.object(readability_report_generator, "AnkiMorphsDB", FakeDB),
        mock.patch.object(study_plan_generator, "AnkiMorphsDB", FakeDB),
        mock.patch.object(progression_window, "AnkiMorphsDB", FakeDB),
        mock.patch.object(progression_utils, "AnkiMorphsDB", FakeDB),
        mock.patch.object(known_morphs_exporter, "AnkiMorphsDB", FakeDB),
    ]

    for am_db_patch in am_db_patches:
        am_db_patch.start()

    mock_db = FakeDB()

    # tooltip tries to do gui stuff which breaks test
    mock_tooltip = mock.Mock(spec=aqt.utils.tooltip)

    misc_patches: list[Any] = [
        mock.patch.object(reviewing_utils, "tooltip", mock_tooltip),
        mock.patch.object(spacy_wrapper, "testing_environment", True),
        mock.patch.object(
            ankimorphs_globals, "PRIORITY_FILES_DIR_NAME", _priority_files_dir
        ),
        mock.patch.object(
            ankimorphs_globals, "KNOWN_MORPHS_DIR_NAME", _known_morphs_dir
        ),
    ]

    for misc_patch in misc_patches:
        misc_patch.start()

    sys.path.append(str(fake_morphemizers_path))

    try:
        yield FakeEnvironment(
            mock_mw=mock_mw,
            mock_db=mock_db,
            config=_config_data,
            known_morphs_dir=_known_morphs_dir,
            priority_files_dir=_priority_files_dir,
            original_collection=Collection(str(path_original_collection)),
            modified_collection=mock_mw.col,
        )

    except anki.errors.DBError:
        yield None

    mock_mw.col.close()
    mock_db.con.close()

    for mw_patch in mw_patches:
        mw_patch.stop()

    for am_db_patch in am_db_patches:
        am_db_patch.stop()

    for misc_patch in misc_patches:
        misc_patch.stop()

    sys.path.remove(str(fake_morphemizers_path))

    Path.unlink(PATH_DB_COPY, missing_ok=True)
    Path.unlink(path_duplicate_collection, missing_ok=True)
    shutil.rmtree(path_original_collection_media, ignore_errors=True)
    shutil.rmtree(collection_path_duplicate_media, ignore_errors=True)

    if PATH_TESTS_DATA_TESTS_OUTPUTS.exists():
        for file in PATH_TESTS_DATA_TESTS_OUTPUTS.iterdir():
            if file.is_file():
                file.unlink()
