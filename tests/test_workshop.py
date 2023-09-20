from unittest import mock

import pytest
from PyQt6.QtWidgets import QApplication

from ankimorphs import preferences
from tests.fake_preferences import get_fake_preferences


# def test_mock_patch():
#
#     mock_mw = mock.MagicMock(spec=preferences.mw)
#
#     print(f"preferences.mw1: {preferences.mw}")
#
#
#     my_context = mock.patch.object(preferences, 'mw', mock_mw)
#
#     print(f"preferences.mw2: {preferences.mw}")
#
#     with my_context:
#         print(f"preferences.mw3: {preferences.mw}")
#
#     print(f"preferences.mw4: {preferences.mw}")
#
#
#     assert False
#
# @pytest.fixture
# def setup_mock2():
#     mock_mw = mock.MagicMock(spec=preferences.mw)
#     mock_mw.col.get_config.return_value = get_fake_preferences()
#
#     print(f"preferences.mw1: {preferences.mw}")
#
#     # Replace the objects in the preferences module
#     ptach1 = mock.patch.object(preferences, 'mw', mock_mw)
#     ptach1.start()
#
#     print(f"preferences. yield: {preferences.mw}")
#
#     yield
#
#     ptach1.stop()
#
#     print(f"preferences post yield: {preferences.mw}")
#
#
# def test_start(setup_mock2):
#     print(f"preferences.test: {preferences.mw}")
#
#
# def test_start2():
#     print(f"preferences.test2: {preferences.mw}")
