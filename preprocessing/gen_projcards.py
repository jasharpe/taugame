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
  (42, 30),
  (12, 70),
]

symbols = [
  [
    u'\u265F', # pawn
    u'\u265D', # bishop
    u'\u265E', # knight
  ],
  [
    u'\u265C', # rook
    u'\u265B', # queen
    u'\u265A', # king
  ],
  [
    u'\u2663', # club
    u'\u2665', # heart
    u'\u2666', # diamond
  ],
]

pygame.font.init()
symbol_fonts = [
  pygame.font.SysFont('arialunicodems', 36),
  pygame.font.SysFont('arialunicodems', 36),
  pygame.font.Font('/Users/malcolmsharpe/Library/Fonts/Batang.ttf', 36),
]

s = pygame.Surface((CARD_WIDTH * CARD_COUNT, CARD_HEIGHT), pygame.SRCALPHA)

def putsymbol(font, ch, coords):
  t = font.render(ch, True, (0,0,0))
  s.blit(t, coords)

for i in range(CARD_COUNT):
  vec = i+1
  card = [vec & 3, (vec >> 2) & 3, (vec >> 4) & 3]

  x_offset = i * CARD_WIDTH

  for j in range(len(card)):
    if card[j]:
      x = x_offset + symbol_coords[j][0]
      y = symbol_coords[j][1]
      putsymbol(symbol_fonts[j], symbols[j][card[j]-1], (x,y))

pygame.image.save(s, '../static/projcards.png')
