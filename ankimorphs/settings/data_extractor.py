from __future__ import annotations

from abc import abstractmethod

from ankimorphs.settings.data_provider import DataProvider


class DataExtractor:
    """
    This class is needed to avoid cyclical imports while still
    allowing static type checking and linting.
    """

    def __init__(self) -> None:
        self.data_provider: DataProvider | None = None

    @abstractmethod
    def add_data_provider(self, data_provider: DataProvider) -> None:
        raise NotImplementedError
