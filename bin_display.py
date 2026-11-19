"""Small bin cards drawn on top of the photo, using the example layout."""
import pygame

COLOURS = {'red': (214, 72, 78), 'yellow': (224, 176, 48), 'green': (46, 158, 96)}
INK = (23, 28, 36)
MUTED = (107, 114, 128)
PANEL = (243, 244, 246)
CARD = (255, 255, 255)
WHEEL = (42, 46, 54)


def shade(colour, amount):
    return tuple(max(0, min(255, channel + amount)) for channel in colour)


class BinCalendarRenderer:
    def __init__(self):
        self.fonts = {}

    def font(self, size, bold=False):
        key = (max(12, int(size)), bold)
        if key not in self.fonts:
            if len(self.fonts) >= 32:
                self.fonts.clear()
            font = pygame.font.Font(None, key[0])
            font.set_bold(bold)
            self.fonts[key] = font
        return self.fonts[key]

    def tracked(self, screen, text, rect, size, colour):
        rect = pygame.Rect(rect)
        size = max(12, int(size))
        gap = max(1, size // 9)
        while size > 12:
            font = self.font(size, False)
            width = sum(font.size(char)[0] for char in text) + gap * max(0, len(text) - 1)
            if width <= rect.width:
                break
            size -= 1
            gap = max(1, size // 9)
        font = self.font(size, False)
        glyphs = [font.render(char, True, colour) for char in text]
        if not glyphs:
            return
        width = sum(glyph.get_width() for glyph in glyphs) + gap * (len(glyphs) - 1)
        x = rect.centerx - width // 2
        y = rect.centery - glyphs[0].get_height() // 2
        for glyph in glyphs:
            screen.blit(glyph, (x, y))
            x += glyph.get_width() + gap

    def text(self, screen, text, rect, size, colour=INK, bold=True):
        rect = pygame.Rect(rect)
        size = max(12, int(size))
        while size > 12 and self.font(size, bold).size(str(text))[0] > rect.width:
            size -= 1
        font = self.font(size, bold)
        surface = font.render(str(text), True, colour)
        screen.blit(surface, surface.get_rect(center=rect.center))

    def icon(self, screen, rect, colour):
        x, y, w, h = rect
        dark = shade(colour, -45)
        radius = max(2, int(w * 0.08))
        pygame.draw.rect(screen, colour, (x + w * 0.30, y + h * 0.02, w * 0.40, h * 0.11), border_radius=radius)
        pygame.draw.rect(screen, colour, (x + w * 0.08, y + h * 0.14, w * 0.84, h * 0.13), border_radius=max(2, int(w * 0.06)))
        pygame.draw.rect(screen, colour, (x + w * 0.16, y + h * 0.25, w * 0.68, h * 0.58), border_radius=radius)
        for fraction in (0.34, 0.50, 0.66):
            pygame.draw.line(screen, dark, (x + w * fraction, y + h * 0.38), (x + w * fraction, y + h * 0.72), max(2, int(w * 0.045)))
        wheel = max(3, int(w * 0.09))
        for fraction in (0.30, 0.70):
            pygame.draw.circle(screen, WHEEL, (int(x + w * fraction), int(y + h * 0.90)), wheel)

    def metrics(self, screen_w, screen_h, count):
        margin = max(14, int(min(screen_w, screen_h) * 0.028))
        slot = min(168, max(78, int(min(screen_w, screen_h) * 0.15)))
        avail = max(120, screen_w - margin * 2)
        while count and slot > 68:
            gap = max(8, slot // 10)
            pad = max(12, slot // 7)
            header = max(22, int(slot * 0.28))
            tile_h = int(slot * 1.22)
            outer_w = pad * 2 + slot * count + gap * (count - 1)
            if outer_w <= avail:
                return margin, slot, gap, pad, header, tile_h
            slot -= 4
        gap = 8
        pad = 12
        header = 22
        return margin, 68, gap, pad, header, int(68 * 1.22)

    def place(self, screen_w, screen_h, card, position, margin):
        if position == 'center':
            vertical, horizontal = 'middle', 'center'
        else:
            vertical, horizontal = position.split('-')
        if horizontal == 'left':
            x = margin
        elif horizontal == 'right':
            x = screen_w - card.width - margin
        else:
            x = (screen_w - card.width) // 2
        if vertical == 'top':
            y = margin
        elif vertical == 'bottom':
            y = screen_h - card.height - margin
        else:
            y = (screen_h - card.height) // 2
        card.topleft = (x, y)
        screen_rect = pygame.Rect(0, 0, screen_w, screen_h)
        if not screen_rect.contains(card):
            card.clamp_ip(screen_rect)
        return card

    def panel(self, screen, rect):
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        radius = max(8, min(rect.width, rect.height) // 8)
        pygame.draw.rect(shadow, (0, 0, 0, 60), shadow.get_rect(), border_radius=radius)
        screen.blit(shadow, (rect.x, rect.y + max(3, rect.height // 40)))
        pygame.draw.rect(screen, PANEL, rect, border_radius=radius)
        return radius

    def draw(self, screen, view):
        items = [item for item in (view.get('bins') or []) if item.get('visible', True)]
        if not items:
            return []
        grouped = {}
        order = []
        for item in items:
            position = item.get('position') or 'top-center'
            if position not in grouped:
                order.append(position)
                grouped[position] = []
            grouped[position].append(item)
        width, height = screen.get_size()
        rects = []
        for position in order:
            bins = grouped[position]
            margin, slot, gap, pad, header, tile_h = self.metrics(width, height, len(bins))
            outer = pygame.Rect(0, 0, pad * 2 + slot * len(bins) + gap * (len(bins) - 1), pad * 2 + header + tile_h)
            outer = self.place(width, height, outer, position, margin)
            self.panel(screen, outer)
            self.text(screen, 'BIN COLLECTION', (outer.x + pad, outer.y + pad * 0.35, outer.width - pad * 2, header * 0.85),
                      max(16, header * 0.72), INK, True)
            for index, item in enumerate(bins):
                tile = pygame.Rect(outer.x + pad + index * (slot + gap), outer.y + pad + header, slot, tile_h)
                pygame.draw.rect(screen, CARD, tile, border_radius=max(6, slot // 10))
                icon_h = int(tile.height * 0.46)
                icon_w = int(icon_h * 0.72)
                self.icon(screen, (tile.centerx - icon_w // 2, tile.y + tile.height * 0.06, icon_w, icon_h), COLOURS[item['colour']])
                self.tracked(screen, item.get('label') or item['colour'].upper(),
                             (tile.x + 4, tile.y + tile.height * 0.58, tile.width - 8, tile.height * 0.16),
                             max(12, slot * 0.13), MUTED)
                self.text(screen, item.get('when') or '',
                          (tile.x + 4, tile.y + tile.height * 0.74, tile.width - 8, tile.height * 0.22),
                          max(16, slot * 0.22), INK, True)
            rects.append(outer)
        return rects
