from __future__ import annotations

import gc
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
    PATH_FAKE_MORPHEMIZERS,
    PATH_TEMP_CARD_COLLECTIONS,
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
from aqt.main import AnkiQt
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
from ankimorphs.extra_settings import ankimorphs_extra_settings
from ankimorphs.generators import (
    generators_output_dialog,
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
        actual_col: str | None = None,
        expected_col: str | None = None,
        config: dict[str, Any] | None = None,
        am_db: str | None = None,
        priority_files_dir: str | None = None,
        known_morphs_dir: str | None = None,
    ):
        self.actual_col = actual_col
        self.expected_col = expected_col
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
        actual_collection: Collection,
        expected_collection: Collection,
    ) -> None:
        self.mock_mw = mock_mw
        self.mock_db = mock_db
        self.config = config
        self.priority_files_dir = priority_files_dir
        self.known_morphs_dir = known_morphs_dir
        self.actual_collection = actual_collection
        self.expected_collection = expected_collection


@pytest.fixture(scope="function")
def fake_environment_fixture(  # pylint:disable=too-many-locals
    request: SubRequest,
) -> Iterator[FakeEnvironment | None]:
    # Sending arguments to a fixture requires a somewhat hacky
    # approach of using the "request" fixture as an input, which
    # will then contain the parameters

    # fmt: off
    try:
        _actual_col_name: str = request.param.actual_col or "ignore_names_txt_collection"
        _expected_col_name: str = request.param.expected_col or _actual_col_name
        _config_data: dict[str, Any] = request.param.config or default_config_dict
        _am_db_name: str = request.param.am_db or "empty_skeleton.db"
        _priority_files_dir: str = request.param.priority_files_dir or "correct_outputs"
        _known_morphs_dir: str = request.param.known_morphs_dir or "known-morphs-valid"

        assert isinstance(_actual_col_name, str)
        assert isinstance(_expected_col_name, str)
        assert isinstance(_config_data, dict)
        assert isinstance(_am_db_name, str)
        assert isinstance(_priority_files_dir, str)
        assert isinstance(_known_morphs_dir, str)

    except AttributeError as _error:
        print('Missing "@pytest.mark.parametrize"')
        raise _error

    path_original_actual_col = Path(PATH_CARD_COLLECTIONS, f"{_actual_col_name}.anki2")
    path_duplicate_actual_col = Path(PATH_TEMP_CARD_COLLECTIONS, f"duplicate_pre_{_actual_col_name}.anki2")

    path_original_expected_col = Path(PATH_CARD_COLLECTIONS, f"{_expected_col_name}.anki2")
    path_duplicate_expected_col = Path(PATH_TEMP_CARD_COLLECTIONS, f"duplicate_post_{_expected_col_name}.anki2")

    test_db_original_path = Path(PATH_TESTS_DATA_DBS, _am_db_name)
    # fmt: on

    # create destination dirs
    os.makedirs(PATH_TESTS_DATA_TESTS_OUTPUTS, exist_ok=True)
    os.makedirs(PATH_TEMP_CARD_COLLECTIONS, exist_ok=True)

    # If the file already exists, it will be replaced
    shutil.copyfile(path_original_actual_col, path_duplicate_actual_col)
    shutil.copyfile(path_original_expected_col, path_duplicate_expected_col)
    shutil.copyfile(test_db_original_path, PATH_DB_COPY)

    mock_mw = create_mock_mw(path_duplicate_actual_col, _config_data)
    mw_patches = create_mw_patches(mock_mw)
    for mw_patch in mw_patches:
        mw_patch.start()

    # 'mw' has to be patched before we can before we can create db instances
    am_db_patches = create_am_db_patches()
    for am_db_patch in am_db_patches:
        am_db_patch.start()

    misc_patches = create_misc_patches(_priority_files_dir, _known_morphs_dir)
    for misc_patch in misc_patches:
        misc_patch.start()

    sys.path.append(str(PATH_FAKE_MORPHEMIZERS))
    mock_db = FakeDB()

    try:
        try:
            fake_env = FakeEnvironment(
                mock_mw=mock_mw,
                mock_db=mock_db,
                config=_config_data,
                known_morphs_dir=_known_morphs_dir,
                priority_files_dir=_priority_files_dir,
                actual_collection=mock_mw.col,
                expected_collection=Collection(str(path_duplicate_expected_col)),
            )

        except anki.errors.DBError:
            fake_env = None

        yield fake_env

    finally:
        post_test_teardown(
            mock_db=mock_db,
            mock_mw=mock_mw,
            patches=mw_patches + am_db_patches + misc_patches,
        )


def create_mock_mw(
    path_duplicate_collection: Path, _config_data: dict[str, Any]
) -> mock.Mock:
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

    return mock_mw


def create_mw_patches(mock_mw: AnkiQt) -> list[Any]:
    return [
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
        mock.patch.object(ankimorphs_extra_settings, "mw", mock_mw),
        mock.patch.object(generators_output_dialog, "mw", mock_mw),
    ]


def create_am_db_patches() -> list[Any]:
    return [
        mock.patch.object(reviewing_utils, "AnkiMorphsDB", FakeDB),
        mock.patch.object(recalc_main, "AnkiMorphsDB", FakeDB),
        mock.patch.object(caching, "AnkiMorphsDB", FakeDB),
        mock.patch.object(readability_report_generator, "AnkiMorphsDB", FakeDB),
        mock.patch.object(study_plan_generator, "AnkiMorphsDB", FakeDB),
        mock.patch.object(progression_window, "AnkiMorphsDB", FakeDB),
        mock.patch.object(progression_utils, "AnkiMorphsDB", FakeDB),
        mock.patch.object(known_morphs_exporter, "AnkiMorphsDB", FakeDB),
    ]


def create_misc_patches(_priority_files_dir: str, _known_morphs_dir: str) -> list[Any]:
    # fmt: off
    return [
        # tooltip tries to do gui stuff which breaks test
        mock.patch.object(reviewing_utils, "tooltip", mock.Mock(spec=aqt.utils.tooltip)),
        mock.patch.object(spacy_wrapper, "testing_environment", True),
        mock.patch.object(ankimorphs_globals, "PRIORITY_FILES_DIR_NAME", _priority_files_dir),
        mock.patch.object(ankimorphs_globals, "KNOWN_MORPHS_DIR_NAME", _known_morphs_dir),
    ]
    # fmt: on


def post_test_teardown(
    mock_db: FakeDB,
    mock_mw: AnkiQt,
    patches: list[Any],
) -> None:
    mock_db.con.close()
    mock_mw.col.close()

    for patch in patches:
        patch.stop()

    # Windows can sometimes have lingering references so we force cleanup here
    gc.collect()

    sys.path.remove(str(PATH_FAKE_MORPHEMIZERS))

    Path.unlink(PATH_DB_COPY, missing_ok=True)
    shutil.rmtree(PATH_TEMP_CARD_COLLECTIONS, ignore_errors=True)
    shutil.rmtree(PATH_TESTS_DATA_TESTS_OUTPUTS, ignore_errors=True)
