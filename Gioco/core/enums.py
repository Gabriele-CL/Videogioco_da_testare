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
    PAUSE           = auto()
    DEAD            = auto()
    COMBAT          = auto()

class CharClass(Enum):
    WARRIOR = "Warrior"
    ROGUE   = "Rogue"
    MAGE    = "Mage"
    RANGER  = "Ranger"
    PALADIN = "Paladin"

CLASS_DESC = {
    CharClass.WARRIOR: "+30% HP | +20% ATK | Stile: mischia pesante",
    CharClass.ROGUE:   "+30% Stamina | -20% HP | Crit x1.5 | Stile: furtivo",
    CharClass.MAGE:    "-30% HP | Magie potenti | Stile: distanza",
    CharClass.RANGER:  "-10% HP | Bilanciato | Stile: esplorazione",
    CharClass.PALADIN: "+20% HP | +10% DEF | Rigenerazione | Stile: tank",
}

class LifeStage(Enum):
    CHILD = "Child"
    TEEN  = "Teen"
    ADULT = "Adult"
    ELDER = "Elder"
