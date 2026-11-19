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
            # Same system font as the clock, date and weather overlays.
            self.fonts[key] = pygame.font.SysFont(None, key[0], bold=bold)
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

    def metrics(self, screen_w, screen_h, count, scale=100):
        try:
            scale = float(scale) / 100.0
        except (TypeError, ValueError):
            scale = 1.0
        if scale <= 0:
            scale = 1.0
        scale = min(2.0, max(0.5, scale))
        margin = max(14, int(min(screen_w, screen_h) * 0.028))
        base = int(min(screen_w, screen_h) * 0.14 * scale)
        slot = min(int(150 * scale), max(int(36 * scale), base))
        avail = max(80, screen_w - margin * 2)
        floor = max(28, int(36 * scale))
        # Just enough space for the labels to stay separate. The column used to
        # be much wider than the icon, which left a large empty gap.
        gap = max(8, int(round(10 * scale)))
        while count and slot > floor:
            icon_h = int(slot * 0.60)
            date_size = max(20, int(icon_h * 0.48))
            col_w = max(int(icon_h * 0.72), int(date_size * 3.4))
            outer_w = col_w * count + gap * (count - 1)
            if outer_w <= avail:
                return margin, slot, gap, icon_h
            slot -= 4
        return margin, floor, gap, int(floor * 0.60)

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

    def tracked_width(self, text, size):
        size = max(12, int(size))
        gap = max(1, size // 9)
        font = self.font(size, False)
        return sum(font.size(char)[0] for char in text) + gap * max(0, len(text) - 1)

    def group_surface(self, bins, slot, gap, tile_h):
        icon_h = max(28, int(slot * 0.60))
        icon_w = max(16, int(icon_h * 0.72))
        label_size = max(14, int(icon_h * 0.32))
        date_size = max(20, int(icon_h * 0.48))
        label_h = self.font(label_size).get_height()
        date_h = self.font(date_size).get_height()
        stack_gap = max(1, int(icon_h * 0.04))
        # The wheel sits near the bottom of the icon box, so the next line
        # starts just under that instead of in a tall empty band.
        label_y = int(icon_h * 0.92) + stack_gap
        date_y = label_y + label_h + stack_gap
        content_h = date_y + date_h
        columns = []
        for item in bins:
            label = item.get('label') or item['colour'].upper()
            when = str(item.get('when') or '')
            col_w = max(icon_w, self.tracked_width(label, label_size), self.font(date_size).size(when)[0]) + 4
            columns.append((item, label, when, col_w))
        width = sum(col_w for _, _, _, col_w in columns) + gap * (len(columns) - 1)
        surface = pygame.Surface((max(1, width), content_h), pygame.SRCALPHA)
        x = 0
        for item, label, when, col_w in columns:
            self.icon(surface, (x + (col_w - icon_w) // 2, 0, icon_w, icon_h), COLOURS[item['colour']])
            self.tracked(surface, label, (x, label_y, col_w, label_h), label_size, MUTED)
            self.text(surface, when, (x, date_y, col_w, date_h), date_size, INK, False)
            x += col_w + gap
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
        try:
            icon_scale = float(view.get('icon_scale', 100)) / 100.0
        except (TypeError, ValueError):
            icon_scale = 1.0
        if icon_scale <= 0:
            icon_scale = 1.0
        icon_scale = min(2.0, max(0.5, icon_scale))
        # Same backing as the clock, date and weather: a black rectangle at alpha 100.
        pad = max(4, int(round(8 * icon_scale)))
        rects = []
        for position in order:
            bins = grouped[position]
            margin, slot, gap, tile_h = self.metrics(logical_w, logical_h, len(bins), view.get('icon_scale', 100))
            layer = self.group_surface(bins, slot, gap, tile_h)
            outer = pygame.Rect(0, 0, layer.get_width() + pad * 2, layer.get_height() + pad * 2)
            outer = self.place(logical_w, logical_h, outer, position, margin)
            content_scaled = (max(1, int(round(layer.get_width() * correction_h))),
                              max(1, int(round(layer.get_height() * correction_v))))
            if content_scaled != layer.get_size():
                layer = pygame.transform.scale(layer, content_scaled)
            box = pygame.Rect(
                (int(round(outer.x * correction_h)), int(round(outer.y * correction_v))),
                (max(1, int(round(outer.width * correction_h))), max(1, int(round(outer.height * correction_v)))),
            )
            background = pygame.Surface(box.size)
            background.set_alpha(100)
            background.fill((0, 0, 0))
            screen.blit(background, box.topleft)
            screen.blit(layer, (int(round((outer.x + pad) * correction_h)), int(round((outer.y + pad) * correction_v))))
            rects.append(box)
        return rects
