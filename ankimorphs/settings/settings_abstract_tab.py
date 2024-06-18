from __future__ import annotations

import pprint
from abc import ABC, abstractmethod

from aqt.qt import QDialog  # pylint:disable=no-name-in-module

from ..ankimorphs_config import AnkiMorphsConfig
from ..ui.settings_dialog_ui import Ui_SettingsDialog


class AbstractSettingsTab(ABC):
    def __init__(
        self,
        parent: QDialog,
        ui: Ui_SettingsDialog,
        config: AnkiMorphsConfig,
        default_config: AnkiMorphsConfig,
    ):
        self._parent = parent
        self.ui = ui
        self._config = config
        self._default_config = default_config
        self._previous_state: dict[str, str | int | bool | object] | None = None

        # subclasses should now run:
        # 1. self.populate()
        # 2. self.setup_buttons()
        # 3. self._previous_state = self.settings_to_dict()

    @abstractmethod
    def populate(self) -> None:
        pass

    @abstractmethod
    def setup_buttons(self) -> None:
        pass

    @abstractmethod
    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        pass

    @abstractmethod
    def restore_to_config_state(self) -> None:
        pass

    @abstractmethod
    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        pass

    def contains_unsaved_changes(self) -> bool:
        assert self._previous_state is not None

        current_state = self.settings_to_dict()
        print("current_state")
        pprint.pp(current_state)

        print("_initial_state")
        pprint.pp(self._previous_state)

        if current_state != self._previous_state:
            print("NOT the same")
            return True

        print("the same")
        return False
