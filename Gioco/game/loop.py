import random

from combat.combat import CombatPhase
from core.constants import FPS, MOVE_DELAY
from core.enums import GameState
from items.item import ITEM_GEN

from .bootstrap import pygame


class GameLoopMixin:
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.tick += dt
            self.handle_events()
            if self.state == GameState.COMBAT and self.combat_state:
                self.combat_state.update(dt)
                cs = self.combat_state
                if cs.phase == CombatPhase.OUTRO and cs.outro_timer >= 0.8:
                    self._end_combat()
                elif cs.phase == CombatPhase.FLED:
                    self._end_combat()
                elif cs.phase == CombatPhase.DEFEAT:
                    self.handle_death()
            if self.state == GameState.PLAYING and self.player and self.player.alive:
                try:
                    stage_changed = self.player.update_age(dt)
                    if stage_changed:
                        self.journal_add(f"Nuova fase della vita: {stage_changed}", "level")
                    self.update_entities(dt)
                except Exception as e:
                    self.log(f"[ERR] {e}")
                if self.player.health <= 0:
                    self.player.alive = False
                    if not self.player.death_cause:
                        self.player.death_cause = "Causa sconosciuta"
            if self.magic_aura_timer > 0:
                self.magic_aura_timer -= dt
                if self.magic_aura_timer <= 0:
                    self.magic_aura_timer = 0
                    p2 = self.player
                    if p2 and self.magic_aura_has_power:
                        self.log("Maestro di Magia: \"C'e' della magia in te!\"")
                    elif p2:
                        self.log("Maestro di Magia: \"Mi spiace... non c'e' potere in te.\"")
            if self.state == GameState.PLAYING and self.player and not self.player.alive:
                self.handle_death()
            for ft in self.floating_texts:
                ft.update(dt)
            self.floating_texts = [ft for ft in self.floating_texts if ft.alive]
            if self.save_flash > 0:
                self.save_flash = max(0.0, self.save_flash - dt)
            if self.state == GameState.PLAYING and self.player and random.random() < 0.0005:
                p = self.player
                ix = p.x + random.randint(-15, 15)
                iy = p.y + random.randint(-15, 15)
                if self.world.is_passable(ix, iy):
                    drop = ITEM_GEN.generate_item()
                    drop.x, drop.y = ix, iy
                    self.items_on_ground.append(drop)
            if self.state == GameState.PLAYING and self.player and self.player.alive:
                keys = pygame.key.get_pressed()
                dx = (1 if keys[pygame.K_RIGHT] else 0) - (1 if keys[pygame.K_LEFT] else 0)
                dy = (1 if keys[pygame.K_DOWN] else 0) - (1 if keys[pygame.K_UP] else 0)
                if dx or dy:
                    self.move_timer += dt
                    if self.move_timer >= MOVE_DELAY:
                        self.move_timer = 0.0
                        self.try_move(dx, dy)
                else:
                    self.move_timer = MOVE_DELAY
            self.render()
        pygame.quit()
