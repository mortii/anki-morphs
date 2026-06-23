from __future__ import annotations

import gc
import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from test.fake_configs import default_config_dict
from test.test_globals import (
    PATH_CARD_COLLECTIONS,
    PATH_FAKE_MORPHEMIZERS,
    PATH_TESTS_DATA_DBS,
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
from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.extra_settings import ankimorphs_extra_settings
from ankimorphs.generators import (
    generators_output_dialog,
    generators_utils,
    generators_window,
    priority_file_generator,
    readability_report_generator,
    study_plan_generator,
)
from ankimorphs.morphemizers import camel_wrapper, spacy_wrapper
from ankimorphs.progression import progression_window
from ankimorphs.recalc import anki_data_utils, caching, recalc_main


class FakeEnvironmentParams:
    def __init__(  # pylint:disable=too-many-arguments
        self,
        initial_col: str | None = None,
        result_col: str | None = None,
        config: dict[str, Any] | None = None,
        am_db: str | None = None,
        priority_files_dir: str | None = None,
        known_morphs_dir: str | None = None,
    ):
        self.initial_col = initial_col
        self.result_col = result_col
        self.config = config
        self.am_db = am_db
        self.priority_files_dir = priority_files_dir
        self.known_morphs_dir = known_morphs_dir


class FakeEnvironment:

    def __init__(  # pylint:disable=too-many-arguments
        self,
        mock_mw: mock.Mock,
        mock_db: AnkiMorphsDB,
        config: dict[str, Any],
        priority_files_dir: str,
        known_morphs_dir: str,
        initial_collection: Collection,
        result_collection: Collection,
    ) -> None:
        self.mock_mw = mock_mw
        self.mock_db = mock_db
        self.config = config
        self.priority_files_dir = priority_files_dir
        self.known_morphs_dir = known_morphs_dir
        self.initial_collection = initial_collection
        self.result_collection = result_collection


@pytest.fixture(scope="function")
def fake_environment_fixture(  # pylint:disable=too-many-locals
    request: SubRequest,
    tmp_path: Path,  # pytest fixture that creates temp dir, persists for 3 invocations.
) -> Iterator[FakeEnvironment | None]:
    # Sending arguments to a fixture requires a somewhat hacky
    # approach of using the "request" fixture as an input, which
    # will then contain the parameters

    # fmt: off
    try:
        params: FakeEnvironmentParams = request.param
    except AttributeError:
        params = FakeEnvironmentParams()

    _initial_col_name: str = params.initial_col or "ignore_names_txt_collection"
    _result_col_name: str = params.result_col or _initial_col_name
    _config_data: dict[str, Any] = params.config or default_config_dict
    _am_db_name: str = params.am_db or "empty_skeleton.db"
    _priority_files_dir: str = params.priority_files_dir or "correct_outputs"
    _known_morphs_dir: str = params.known_morphs_dir or "known-morphs-valid"

    assert isinstance(_initial_col_name, str)
    assert isinstance(_result_col_name, str)
    assert isinstance(_config_data, dict)
    assert isinstance(_am_db_name, str)
    assert isinstance(_priority_files_dir, str)
    assert isinstance(_known_morphs_dir, str)


    path_original_initial_col = Path(PATH_CARD_COLLECTIONS, f"{_initial_col_name}.anki2")
    path_duplicate_initial_col = tmp_path / f"duplicate_pre_{_initial_col_name}.anki2"

    path_original_result_col = Path(PATH_CARD_COLLECTIONS, f"{_result_col_name}.anki2")
    path_duplicate_result_col = tmp_path / f"duplicate_post_{_result_col_name}.anki2"
    # # fmt: on

    test_db_original_path = Path(PATH_TESTS_DATA_DBS, _am_db_name)
    path_db_copy = tmp_path / "temp_copied.db"
    AnkiMorphsDB.test_db_path = path_db_copy

    shutil.copyfile(path_original_initial_col, path_duplicate_initial_col)
    shutil.copyfile(path_original_result_col, path_duplicate_result_col)
    shutil.copyfile(test_db_original_path, path_db_copy)

    mock_mw = create_mock_mw(path_duplicate_initial_col, _config_data)
    mw_patches = create_mw_patches(mock_mw)
    for mw_patch in mw_patches:
        mw_patch.start()

    # 'mw' has to be patched before we can before we can create db instances
    misc_patches = create_misc_patches(_priority_files_dir, _known_morphs_dir)
    for misc_patch in misc_patches:
        misc_patch.start()

    sys.path.append(str(PATH_FAKE_MORPHEMIZERS))
    mock_db = AnkiMorphsDB()

    try:
        try:
            fake_env = FakeEnvironment(
                mock_mw=mock_mw,
                mock_db=mock_db,
                config=_config_data,
                known_morphs_dir=_known_morphs_dir,
                priority_files_dir=_priority_files_dir,
                initial_collection=mock_mw.col,
                result_collection=Collection(str(path_duplicate_result_col)),
            )

        except anki.errors.DBError:
            fake_env = None

        yield fake_env

    finally:
        post_test_teardown(
            mock_db=mock_db,
            mock_mw=mock_mw,
            patches=mw_patches + misc_patches,
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


def create_misc_patches(_priority_files_dir: str, _known_morphs_dir: str) -> list[Any]:
    # fmt: off
    return [
        # tooltip tries to do gui stuff which breaks test
        mock.patch.object(reviewing_utils, "tooltip", mock.Mock(spec=aqt.utils.tooltip)),
        mock.patch.object(spacy_wrapper, "testing_environment", True),
        mock.patch.object(camel_wrapper, "testing_environment", True),
        mock.patch.object(ankimorphs_globals, "PRIORITY_FILES_DIR_NAME", _priority_files_dir),
        mock.patch.object(ankimorphs_globals, "KNOWN_MORPHS_DIR_NAME", _known_morphs_dir),
    ]
    # fmt: on


def post_test_teardown(
    mock_db: AnkiMorphsDB,
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
