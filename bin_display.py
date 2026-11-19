"""Small bin cards drawn on top of the photo, using the example layout."""
import pygame

COLOURS = {'red': (214, 72, 78), 'yellow': (224, 176, 48), 'green': (46, 158, 96)}
INK = (255, 255, 255)
MUTED = (236, 240, 244)
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
        shadows = [font.render(char, True, (0, 0, 0)) for char in text]
        if not glyphs:
            return
        width = sum(glyph.get_width() for glyph in glyphs) + gap * (len(glyphs) - 1)
        x = rect.centerx - width // 2
        y = rect.centery - glyphs[0].get_height() // 2
        for shadow, glyph in zip(shadows, glyphs):
            screen.blit(shadow, (x + 1, y + 1))
            screen.blit(glyph, (x, y))
            x += glyph.get_width() + gap

    def text(self, screen, text, rect, size, colour=INK, bold=True):
        rect = pygame.Rect(rect)
        size = max(12, int(size))
        while size > 12 and self.font(size, bold).size(str(text))[0] > rect.width:
            size -= 1
        font = self.font(size, bold)
        surface = font.render(str(text), True, colour)
        shadow = font.render(str(text), True, (0, 0, 0))
        target = surface.get_rect(center=rect.center)
        screen.blit(shadow, target.move(1, 1))
        screen.blit(surface, target)

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
        slot = min(150, max(72, int(min(screen_w, screen_h) * 0.14)))
        avail = max(120, screen_w - margin * 2)
        while count and slot > 64:
            gap = max(8, slot // 8)
            tile_h = int(slot * 1.15)
            outer_w = slot * count + gap * (count - 1)
            if outer_w <= avail:
                return margin, slot, gap, tile_h
            slot -= 4
        return margin, 64, 8, int(64 * 1.15)

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

    def group_surface(self, bins, slot, gap, tile_h):
        width = slot * len(bins) + gap * (len(bins) - 1)
        surface = pygame.Surface((width, tile_h), pygame.SRCALPHA)
        for index, item in enumerate(bins):
            tile = pygame.Rect(index * (slot + gap), 0, slot, tile_h)
            icon_h = int(tile.height * 0.52)
            icon_w = int(icon_h * 0.72)
            self.icon(surface, (tile.centerx - icon_w // 2, tile.y + tile.height * 0.02, icon_w, icon_h), COLOURS[item['colour']])
            self.tracked(surface, item.get('label') or item['colour'].upper(),
                         (tile.x + 2, tile.y + tile.height * 0.58, tile.width - 4, tile.height * 0.16),
                         max(12, slot * 0.14), MUTED)
            self.text(surface, item.get('when') or '',
                      (tile.x + 2, tile.y + tile.height * 0.74, tile.width - 4, tile.height * 0.22),
                      max(16, slot * 0.24), INK, True)
        return surface

    def draw(self, screen, view, correction_h=1.0, correction_v=1.0):
        items = [item for item in (view.get('bins') or []) if item.get('visible', True)]
        if not items:
            return []
        try:
            correction_h = float(correction_h)
            correction_v = float(correction_v)
        except (TypeError, ValueError):
            correction_h, correction_v = 1.0, 1.0
        if correction_h <= 0 or correction_v <= 0:
            correction_h, correction_v = 1.0, 1.0
        grouped = {}
        order = []
        for item in items:
            position = item.get('position') or 'top-center'
            if position not in grouped:
                order.append(position)
                grouped[position] = []
            grouped[position].append(item)
        width, height = screen.get_size()
        # Photos are laid out in corrected space, then stretched onto the
        # pixel buffer. Draw the icons the same way so the display does not
        # squash them relative to the picture.
        logical_w = max(1, int(round(width / correction_h)))
        logical_h = max(1, int(round(height / correction_v)))
        rects = []
        for position in order:
            bins = grouped[position]
            margin, slot, gap, tile_h = self.metrics(logical_w, logical_h, len(bins))
            outer = pygame.Rect(0, 0, slot * len(bins) + gap * (len(bins) - 1), tile_h)
            outer = self.place(logical_w, logical_h, outer, position, margin)
            layer = self.group_surface(bins, slot, gap, tile_h)
            scaled = (max(1, int(round(layer.get_width() * correction_h))),
                      max(1, int(round(layer.get_height() * correction_v))))
            if scaled != layer.get_size():
                layer = pygame.transform.scale(layer, scaled)
            dest = (int(round(outer.x * correction_h)), int(round(outer.y * correction_v)))
            screen.blit(layer, dest)
            rects.append(pygame.Rect(dest, layer.get_size()))
        return rects
