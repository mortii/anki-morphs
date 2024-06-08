from abc import ABC, abstractmethod


class AbstractSettingsTab(ABC):
    @abstractmethod
    def populate(self) -> None:
        pass

    @abstractmethod
    def restore_defaults(self, skip_confirmation: bool = False) -> None:
        pass
