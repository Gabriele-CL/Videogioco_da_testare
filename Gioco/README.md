# RogueLife - Eldoria Chronicles

Gioco roguelike ASCII in Python con mappa procedurale, NPC, combattimento a turni e salvataggio su JSON.

## Requisiti

- Python 3.10+ consigliato
- Dipendenze Python:
  - `pygame`

## Installazione

```bash
python -m pip install -r requirements.txt
```

## Avvio

```bash
python main.py
```

## Salvataggi

- Save principale: `savegame.json`
- Storico morti: `dead_characters.json`

## Note

- Il progetto usa una generazione mondo deterministica via seed.
- Dopo il caricamento, le strutture runtime della città (mura/edifici) vengono ricostruite per mantenere coerenti le AI NPC.
