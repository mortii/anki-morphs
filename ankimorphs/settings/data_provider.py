from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..settings.data_subscriber import DataSubscriber


class DataProvider(ABC):
    """
    This class is needed to avoid cyclical imports while still
    allowing static type checking and linting.
    """

    def __init__(self) -> None:
        self._subscriber: DataSubscriber | None = None

    def add_subscriber(self, subscriber: Any) -> None:
        self._subscriber = subscriber

    @abstractmethod
    def notify_subscribers(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_data(self) -> Any:
        raise NotImplementedError
