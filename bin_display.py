"""Bounded page rotation and a resolution-independent Pygame bin page."""
import datetime as dt
import threading

import pygame

from bin_calendar import BRISBANE

COLOURS = {'red': (239, 92, 103), 'yellow': (248, 201, 76), 'green': (73, 191, 142)}
WHITE = (239, 244, 250)
MUTED = (157, 174, 194)
BACKGROUND = (13, 23, 38)
PANEL = (23, 38, 57)


class BinPageCycle:
    def __init__(self):
        self.active = False
        self.until = 0
        self.next_page = None
        self.last_draw = 0
        self.interval = None
        self.pending = None
        self.lock = threading.Lock()

    def request(self, show=True):
        with self.lock:
            self.pending = bool(show)

    def tick(self, now, settings, ready, display_on=True):
        with self.lock:
            request, self.pending = self.pending, None
        previous = self.active
        if self.interval != settings.page_interval_seconds or self.next_page is None:
            self.interval = settings.page_interval_seconds
            self.next_page = now + self.interval
        if not settings.enabled or not display_on:
            self.active = False
            self.next_page = now + self.interval
        elif request is False:
            self.active = False
            self.next_page = now + self.interval
        elif request is True or (ready and not self.active and now >= self.next_page):
            self.active = True
            self.until = now + settings.page_duration_seconds
            self.next_page = now + self.interval
        elif self.active and now >= self.until:
            self.active = False
        redraw = previous != self.active or (self.active and now - self.last_draw >= settings.display_update_seconds)
        if request is True and self.active:
            redraw = True
        if redraw:
            self.last_draw = now
        return redraw


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

    def text(self, screen, text, rect, size, colour=WHITE, bold=False, align='left'):
        rect = pygame.Rect(rect)
        size = max(12, int(size))
        while size > 12 and self.font(size, bold).size(str(text))[0] > rect.width:
            size -= 1
        font = self.font(size, bold)
        if font.size(str(text))[0] > rect.width:
            text = str(text)
            while text and font.size(text + '...')[0] > rect.width:
                text = text[:-1]
            text += '...'
        surface = font.render(str(text), True, colour)
        target = surface.get_rect(centery=rect.centery)
        if align == 'right':
            target.right = rect.right
        elif align == 'center':
            target.centerx = rect.centerx
        else:
            target.left = rect.left
        screen.blit(surface, target)

    @staticmethod
    def icon(screen, rect, colour):
        rect = pygame.Rect(rect)
        x, y, w, h = rect
        body = pygame.Rect(x + w * .18, y + h * .19, w * .64, h * .65)
        pygame.draw.rect(screen, (57, 76, 98), body, border_radius=max(2, w // 12))
        pygame.draw.rect(screen, colour, (x + w * .12, y + h * .12, w * .76, h * .12), border_radius=max(2, w // 20))
        pygame.draw.rect(screen, colour, (x + w * .35, y + h * .07, w * .3, h * .07), border_radius=2)
        pygame.draw.line(screen, (99, 119, 141), (x + w * .38, y + h * .33), (x + w * .38, y + h * .71), max(1, w // 45))
        pygame.draw.line(screen, (99, 119, 141), (x + w * .62, y + h * .33), (x + w * .62, y + h * .71), max(1, w // 45))
        for fraction in (.31, .69):
            pygame.draw.circle(screen, (7, 14, 24), (int(x + w * fraction), int(y + h * .88)), max(3, int(w * .07)))

    def draw(self, screen, view, settings, now=None):
        w, h = screen.get_size()
        pad = max(12, int(w * .045))
        inner = w - pad * 2
        unit = min(w / 650, h / 800) if h > w else min(w / 1280, h / 720)
        now = (now or dt.datetime.now(BRISBANE)).astimezone(BRISBANE)
        screen.fill(BACKGROUND)
        self.text(screen, 'BIN COLLECTION', (pad, h * .035, inner * .65, h * .05), 32 * unit, bold=True)
        self.text(screen, now.strftime('%a %d %b %Y  %H:%M'), (w * .64, h * .04, w * .315, h * .04), 20 * unit, MUTED, align='right')
        self.text(screen, view.get('location') or 'Brisbane', (pad, h * .087, inner, h * .035), 19 * unit, MUTED)

        hero = pygame.Rect(pad, h * .15, inner, h * .41)
        pygame.draw.rect(screen, PANEL, hero, border_radius=max(8, int(18 * unit)))
        inset = max(12, int(inner * .025))
        event = view.get('next')
        if event:
            urgent = event['highlight'] and event['confirmed']
            accent = COLOURS['yellow'] if urgent else (91, 208, 191)
            relative = event['relative'] if event['confirmed'] else 'EXPECTED · ' + event['relative']
            self.text(screen, 'NEXT COLLECTION', (hero.x + inset, hero.y + inset, hero.w * .45, hero.h * .10), 18 * unit, MUTED, True)
            self.text(screen, relative, (hero.x + hero.w * .48, hero.y + inset, hero.w * .49 - inset, hero.h * .12), 27 * unit, accent, True, 'right')
            day = dt.date.fromisoformat(event['date'])
            self.text(screen, day.strftime('%A %d %B %Y'), (hero.x + inset, hero.y + hero.h * .18, hero.w - inset * 2, hero.h * .18), 44 * unit, bold=True)
            count = len(event['bins'])
            card_w = (hero.w - inset * 2) / max(1, count)
            for index, item in enumerate(event['bins']):
                x = hero.x + inset + index * card_w
                icon_h = min(hero.h * .41, card_w * .45)
                self.icon(screen, (x, hero.y + hero.h * .48, icon_h * .72, icon_h), COLOURS[item['colour']])
                label_x = x + icon_h * .85
                label_w = max(20, card_w - icon_h * .9 - 8)
                self.text(screen, item['colour'].upper() + ' BIN', (label_x, hero.y + hero.h * .5, label_w, hero.h * .12), 27 * unit, COLOURS[item['colour']], True)
                self.text(screen, item['name'], (label_x, hero.y + hero.h * .64, label_w, hero.h * .10), 21 * unit)
                self.text(screen, 'Council date' if item['confirmed'] else 'Regular-service estimate',
                          (label_x, hero.y + hero.h * .77, label_w, hero.h * .08), 15 * unit, MUTED)
        else:
            self.text(screen, 'BIN CALENDAR', (hero.x + inset, hero.y + hero.h * .16, hero.w - inset * 2, hero.h * .18), 40 * unit, bold=True)
            message = 'Fetching Council collection dates...' if view.get('enabled') else 'Configure the bin calendar in the web controls'
            if view.get('ready'):
                message = 'No verified upcoming dates — refresh Council data'
            self.text(screen, message, (hero.x + inset, hero.y + hero.h * .46, hero.w - inset * 2, hero.h * .18), 23 * unit, MUTED)

        weeks = view.get('weeks', [])
        top = h * .61
        available_h = h * .265
        row_h = available_h / max(1, len(weeks))
        for index, week in enumerate(weeks):
            y = top + index * row_h
            pygame.draw.line(screen, (42, 60, 81), (pad, int(y)), (w - pad, int(y)), 1)
            start, end = dt.date.fromisoformat(week['start']), dt.date.fromisoformat(week['end'])
            self.text(screen, week['label'], (pad, y + row_h * .12, inner * .25, row_h * .35), min(21 * unit, row_h * .35), MUTED, True)
            self.text(screen, start.strftime('%d %b') + ' – ' + end.strftime('%d %b'),
                      (pad, y + row_h * .51, inner * .25, row_h * .32), min(18 * unit, row_h * .3), MUTED)
            lines = week['events']
            x = pad + inner * .30
            if not lines:
                self.text(screen, 'Dates not yet published', (x, y + row_h * .15, inner * .69, row_h * .65), 20 * unit, MUTED)
            for subindex, upcoming in enumerate(lines):
                line_h = row_h * .84 / max(1, len(lines))
                line_y = y + row_h * .08 + subindex * line_h
                date_label = dt.date.fromisoformat(upcoming['date']).strftime('%a %d %b')
                self.text(screen, date_label, (x, line_y, inner * .19, line_h), min(23 * unit, line_h * .8), bold=True)
                bx = x + inner * .21
                for item in upcoming['bins']:
                    text = item['colour'].upper() + ('' if item['confirmed'] else ' (expected)')
                    slot_w = inner * .155
                    self.text(screen, text, (bx, line_y, slot_w, line_h), min(20 * unit, line_h * .8), COLOURS[item['colour']], True)
                    bx += slot_w

        status = 'OFFLINE · SHOWING CACHED DATES' if view.get('offline') else 'CACHED DATES ARE OLD' if view.get('stale') else 'COUNCIL DATA'
        fetched = view.get('fetched_at')
        if fetched:
            status += ' · Updated ' + dt.datetime.fromisoformat(fetched).astimezone(BRISBANE).strftime('%d %b %H:%M')
        self.text(screen, status, (pad, h * .9, inner, h * .035), 16 * unit,
                  COLOURS['yellow'] if view.get('offline') or view.get('stale') else MUTED)
        note = 'Expected dates follow the regular pattern; daily Council updates take priority.' if view.get('has_estimates') else 'Dates supplied by Brisbane City Council.'
        if h > w:
            self.text(screen, note, (pad, h * .94, inner, h * .025), 14 * unit, MUTED)
            self.text(screen, 'Brisbane City Council · CC BY 4.0', (pad, h * .972, inner, h * .02), 13 * unit, MUTED)
        else:
            self.text(screen, note, (pad, h * .94, inner * .65, h * .03), 14 * unit, MUTED)
            self.text(screen, 'Brisbane City Council · CC BY 4.0', (w * .68, h * .94, w * .275, h * .03), 13 * unit, MUTED, align='right')
