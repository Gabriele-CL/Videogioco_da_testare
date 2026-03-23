# =============================================================================
# core/enums.py
# =============================================================================
from enum import Enum, auto

class GameState(Enum):
    SPLASH          = auto()   # Schermata iniziale "Premi un tasto"
    MAIN_MENU       = auto()   # Menu principale (Nuova/Continua/Opzioni)
    OPTIONS         = auto()   # Schermata opzioni (nera per ora)
    MENU_NAME       = auto()   # Inserimento nome
    INTRO_WELCOME   = auto()   # "Benvenuto <nome>"
    INTRO_ADVENTURE = auto()   # "La tua avventura sta per avere inizio"
    INTRO_DESTINY   = auto()   # "Il destino è nelle tue mani..."
    ESSENZA         = auto()   # Schermata distribuzione punti ESSENZA
    ESSENZA_CONFIRM = auto()   # "Sei sicuro delle tue scelte?"
    PLAYING         = auto()
    INVENTORY       = auto()
    MERCHANT        = auto()
    DIALOG          = auto()
    QUEST_LOG       = auto()
    JOURNAL         = auto()
    PAUSE           = auto()
    DEAD            = auto()
    MAGIC_ASK       = auto()   # Dialogo SI/NO maestro di magia
    COMBAT          = auto()



class LifeStage(Enum):
    CHILD = "Child"
    TEEN  = "Teen"
    ADULT = "Adult"
    ELDER = "Elder"