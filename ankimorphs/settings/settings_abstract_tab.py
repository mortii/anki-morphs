from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractSettingsTab(ABC):
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
    def settings_to_dict(self) -> dict[str, str | int | bool | object]:
        pass
