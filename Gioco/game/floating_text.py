class FloatingText:
    def __init__(self, text, x, y, color, duration=1.2):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.duration = duration
        self.age = 0.0
        self.alive = True

    def update(self, dt):
        self.age += dt
        self.y -= 30 * dt
        if self.age >= self.duration:
            self.alive = False

    def draw(self, screen, font):
        if self.alive:
            alpha = int(255 * (1 - self.age / self.duration))
            surf = font.render(self.text, True, self.color)
            surf.set_alpha(alpha)
            screen.blit(surf, (int(self.x), int(self.y)))
