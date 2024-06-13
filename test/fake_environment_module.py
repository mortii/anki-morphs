from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from test.fake_db import FakeDB
from test.test_globals import (
    PATH_CARD_COLLECTIONS,
    PATH_DB_COPY,
    PATH_TESTS_DATA,
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
from aqt.reviewer import Reviewer

from ankimorphs import (
    ankimorphs_config,
    ankimorphs_db,
    name_file_utils,
    reviewing_utils,
)
from ankimorphs.generators import generators_window
from ankimorphs.morphemizers import spacy_wrapper
from ankimorphs.recalc import anki_data_utils, recalc_main


class FakeEnvironmentParams:
    def __init__(self, collection: str, config: dict[str, Any], am_db: str):
        self.collection = collection
        self.config = config
        self.am_db = am_db


class FakeEnvironment:

    def __init__(  # pylint:disable=too-many-arguments
        self,
        mock_mw: mock.Mock,
        mock_db: FakeDB,
        config: dict[str, Any],
        original_collection: Collection,
        modified_collection: Collection,
    ) -> None:
        self.mock_mw = mock_mw
        self.mock_db = mock_db
        self.config = config
        self.original_collection = original_collection
        self.modified_collection = modified_collection


@pytest.fixture(scope="function")
def fake_environment(  # pylint:disable=too-many-locals, too-many-statements
    request: SubRequest,
) -> Iterator[FakeEnvironment]:
    # Sending arguments to a fixture requires a somewhat hacky
    # approach of using the "request" fixture as an input, which
    # will then contain the parameters

    try:
        _collection_file_name: str = request.param.collection
        assert isinstance(_collection_file_name, str)

        _config_data: dict[str, Any] = request.param.config
        assert isinstance(_config_data, dict)

        _am_db_name: str = request.param.am_db
        assert isinstance(_am_db_name, str)

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
    mock_mw.pm.profileFolder.return_value = os.path.join("tests", "data")
    mock_mw.progress.want_cancel.return_value = False
    mock_mw.addonManager.getConfig.return_value = _config_data
    mock_mw.reviewer = Reviewer(mock_mw)
    mock_mw.reviewer._showQuestion = lambda: None

    patch_recalc_mw = mock.patch.object(recalc_main, "mw", mock_mw)
    patch_am_db_mw = mock.patch.object(ankimorphs_db, "mw", mock_mw)
    patch_config_mw = mock.patch.object(ankimorphs_config, "mw", mock_mw)
    patch_name_file_utils_mw = mock.patch.object(name_file_utils, "mw", mock_mw)
    patch_anki_data_utils_mw = mock.patch.object(anki_data_utils, "mw", mock_mw)
    patch_reviewing_mw = mock.patch.object(reviewing_utils, "mw", mock_mw)
    patch_gd_mw = mock.patch.object(generators_window, "mw", mock_mw)

    patch_recalc_mw.start()
    patch_am_db_mw.start()
    patch_config_mw.start()
    patch_name_file_utils_mw.start()
    patch_anki_data_utils_mw.start()
    patch_reviewing_mw.start()
    patch_gd_mw.start()

    # 'mw' has to be patched before we can before we can create a db instance
    patch_reviewing_am_db = mock.patch.object(reviewing_utils, "AnkiMorphsDB", FakeDB)
    patch_recalc_am_db = mock.patch.object(recalc_main, "AnkiMorphsDB", FakeDB)
    mock_db = FakeDB()

    # tooltip tries to do gui stuff which breaks test
    mock_tooltip = mock.Mock(spec=aqt.utils.tooltip)
    patch_tooltip = mock.patch.object(reviewing_utils, "tooltip", mock_tooltip)

    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    patch_reviewing_am_db.start()
    patch_recalc_am_db.start()
    patch_tooltip.start()

    patch_testing_variable.start()
    sys.path.append(str(fake_morphemizers_path))

    try:
        yield FakeEnvironment(
            mock_mw=mock_mw,
            mock_db=mock_db,
            config=_config_data,
            original_collection=Collection(str(path_original_collection)),
            modified_collection=mock_mw.col,
        )

    except anki.errors.DBError:
        yield None

    finally:
        mock_mw.col.close()
        mock_db.con.close()

        patch_recalc_mw.stop()
        patch_am_db_mw.stop()
        patch_config_mw.stop()
        patch_name_file_utils_mw.stop()
        patch_anki_data_utils_mw.stop()
        patch_reviewing_mw.stop()
        patch_gd_mw.stop()

        patch_reviewing_am_db.stop()
        patch_recalc_am_db.stop()
        patch_tooltip.stop()

        patch_testing_variable.stop()
        sys.path.remove(str(fake_morphemizers_path))

        Path.unlink(PATH_DB_COPY, missing_ok=True)
        Path.unlink(collection_path_duplicate, missing_ok=True)
        shutil.rmtree(path_original_collection_media, ignore_errors=True)
        shutil.rmtree(collection_path_duplicate_media, ignore_errors=True)
