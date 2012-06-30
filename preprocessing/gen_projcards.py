# Generate Projective Set card images.
# Requires some specific fonts, so it will need customization depending on what
# fonts are available.
import pygame
import pygame.font
import pygame.image

CARD_WIDTH = 80
CARD_HEIGHT = 120
CARD_COUNT = 63

symbol_coords = [
  (8, 0),
  (42, 32),
  (12, 70),
]

symbols = [
  [
    u'\u265D', # bishop
    u'\u265E', # knight
    u'\u265C', # rook
  ],
  [
    u'\u00A5', # yen
    u'\u00A3', # pound
    u'\u0024', # dollar
  ],
  [
    u'\u2663', # club
    u'\u2665', # heart
    u'\u2666', # diamond
  ],
]

def to_rgb_tuple(hex_colour):
  n = int(hex_colour[1:], 16)
  return (n // (256*256), (n//256)%256, n%256)

colours = map(to_rgb_tuple, [
  '#000000',
  '#000000',
  '#000000',
])

pygame.font.init()
symbol_fonts = [
  pygame.font.SysFont('arialunicodems', 36),
  pygame.font.SysFont('arialunicodems', 36, bold=True),
  pygame.font.Font('/Users/malcolmsharpe/Library/Fonts/Batang.ttf', 36),
]

s = pygame.Surface((CARD_WIDTH * CARD_COUNT, CARD_HEIGHT), pygame.SRCALPHA)

def putsymbol(font, ch, coords, colour):
  t = font.render(ch, True, colour)
  s.blit(t, coords)

for i in range(CARD_COUNT):
  vec = i+1
  card = [vec & 3, (vec >> 2) & 3, (vec >> 4) & 3]

  x_offset = i * CARD_WIDTH

  for j in range(len(card)):
    if card[j]:
      x = x_offset + symbol_coords[j][0]
      y = symbol_coords[j][1]
      putsymbol(symbol_fonts[j], symbols[j][card[j]-1], (x,y), colours[j])

pygame.image.save(s, '../static/projcards.png')
