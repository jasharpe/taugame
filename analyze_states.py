# Print interesting statistics from State records.

from collections import defaultdict
import json
import numpy as np

from state import *

NUM_PROP = 4

# Modify these to see different stats.
name = 'jsharpe'
game_type = 'i3tau'

session = get_session()
scores = (session.query(Score)
                 .filter(Score.players.any(name=name))
                 .filter_by(num_players=1,game_type=game_type)
                 .filter(Score.invalid == False))

def is_same_in(cards, i):
  return 1 == len(set(c[i] for c in cards))

def num_different(cards):
  # In a tau, determine the number of properties that differ.
  ret = 0
  for i in range(NUM_PROP):
    ret += not is_same_in(cards, i)
  return ret

def get_card_posn(card, board):
  idx = board.index(card)
  R = 3
  C = len(board) / R

  for r in range(R):
    for c in range(C):
      card_index = r + c * R
      if card_index == idx:
        return (r,c)

  assert False

STANDARD_SIZE = 12
def get_spacing(cards, board):
  posns = [get_card_posn(c, board) for c in cards]
  mnr = min(p[0] for p in posns)
  mxr = max(p[0] for p in posns)
  mnc = min(p[1] for p in posns)
  mxc = max(p[1] for p in posns)

  return (mxr-mnr+1) * (mxc-mnc+1)

def get_diff_vector(cards):
  return tuple([not is_same_in(cards,i) for i in range(NUM_PROP)])

# Find times by number of differing properties.
differ_stats = defaultdict(lambda: [])

# Find times by the area of the bounding box of the cards.
posn_stats = defaultdict(lambda: [])

# Find times by some property being the same across the 3 cards.
same_stats = defaultdict(lambda: [])

# Find times by which properties are different.
diffvec_stats = defaultdict(lambda: [])

print 'Processing scores...'
S = 0
for score in scores:
  S += 1
  game = score.game
  prev_time = 0.
  for state in game.states:
    cur_time = state.elapsed_time
    delta = cur_time - prev_time
    prev_time = cur_time

    cards = state.cards()
    board = state.board()
    differ_stats[num_different(cards)].append(delta)
    if len(board) == STANDARD_SIZE:
      posn_stats[get_spacing(cards, board)].append(delta)

    for i in range(NUM_PROP):
      if is_same_in(cards, i):
        same_stats[i].append(delta)

    diffvec_stats[get_diff_vector(cards)].append(delta)

print 'All done!'
print '(There were %d scores.)' % S
print

print 'Player: %s' % name
print 'Game type: %s' % game_type
print

def pr_deltas(deltas):
  print '  count: %d' % len(deltas)
  # To get something meaningful from the mean, the data will need to be cleaned.
  #print '  mean: %.3lf' % np.mean(deltas)
  print '  25%%:    %6.3lf' % np.percentile(deltas, 25.)
  print '  median: %6.3lf' % np.median(deltas)
  print '  75%%:    %6.3lf' % np.percentile(deltas, 75.)
  print

def pr_hr():
  print 60*'*'

pr_hr()
print '*** Number of differing properties'
for x in sorted(differ_stats):
  deltas = differ_stats[x]

  print '# differing properties = %d' % x
  pr_deltas(deltas)

pr_hr()
print '*** Area of card bounding box'
for a in sorted(posn_stats):
  deltas = posn_stats[a]

  print 'Bounding box area = %d' % a
  pr_deltas(deltas)

pr_hr()
print '*** Property that is the same'
PROP_NAMES = ['colour', 'number', 'fill', 'shape']
for i in sorted(same_stats):
  deltas = same_stats[i]

  print 'Has same property = %s' % PROP_NAMES[i]
  pr_deltas(deltas)

pr_hr()
print '*** Different-property vector'
for v in sorted(diffvec_stats, key=sum):
  deltas = diffvec_stats[v]

  print 'Different properties = %s' % ', '.join(PROP_NAMES[i] for i in range(NUM_PROP) if v[i])
  pr_deltas(deltas)
