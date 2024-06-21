from __future__ import annotations

from abc import ABC, abstractmethod


class DataSubscriber(ABC):
    """
    This class is needed to avoid cyclical imports while still
    allowing static type checking and linting.
    """

    @abstractmethod
    def update(self, selected_note_types: list[str]) -> None:
        raise NotImplementedError
