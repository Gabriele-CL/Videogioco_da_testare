from .base import GameBase
from .events import GameEventMixin
from .game import Game as LegacyGame
from .loop import GameLoopMixin
from .menus import GameMenuMixin
from .persistence import GamePersistenceMixin
from .rendering import GameRenderingMixin


class Game(
    GameLoopMixin,
    GameEventMixin,
    GameRenderingMixin,
    GameMenuMixin,
    GamePersistenceMixin,
    GameBase,
    LegacyGame,
):
    pass
