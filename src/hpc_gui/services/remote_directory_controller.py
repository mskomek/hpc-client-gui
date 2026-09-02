"""Framework-neutral remote directory navigation and listing state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListingRequest:
    generation: int
    path: str


class RemoteDirectoryController:
    def __init__(self, initial_path: str = "/") -> None:
        self.current_path = self._normalize(initial_path)
        self.history: list[str] = []
        self.favorites: list[str] = []
        self._generation = 0

    @staticmethod
    def _normalize(path: str) -> str:
        return (str(path or "/").rstrip("/") or "/")

    def navigate(self, path: str) -> ListingRequest:
        target = self._normalize(path)
        if target != self.current_path:
            self.history.append(self.current_path)
            self.current_path = target
        self._generation += 1
        return ListingRequest(self._generation, target)

    def is_current(self, request: ListingRequest) -> bool:
        return request.generation == self._generation and request.path == self.current_path

    def toggle_favorite(self, path: str) -> bool:
        target = self._normalize(path)
        if target in self.favorites:
            self.favorites.remove(target)
            return False
        self.favorites.append(target)
        return True

    def back(self) -> ListingRequest | None:
        if not self.history:
            return None
        return self.navigate(self.history.pop())

