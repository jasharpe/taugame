# A board class optimized for pushing and popping cards, reporting
# statistics quickly.
# Only works with 3 Tau-type modes.

from fingeo import AffineSpace

SPACE = AffineSpace()

class Completer(object):
  def __init__(self):
    self.lookup = SPACE.SIZE * [0]
    self.count = 0

  def update_count(self, card, delta):
    self.count += delta * self.lookup[SPACE.to_int(card)]

  def update_lookup(self, card, delta):
    self.lookup[SPACE.to_int(card)] += delta

  def peek(self, card):
    return self.count + self.lookup[SPACE.to_int(card)]

class Board(object):
  def __init__(self):
    self.cards = []

    self.taus_completer = Completer()
    self.all_different_completer = Completer()
    self.one_same_completer = Completer()
    self.initial_9_completer = Completer()

  def push(self, card):
    self.update(card, 1)
    self.cards.append(card)

  def pop(self):
    card = self.cards.pop()
    self.update(card, -1)

  def update(self, card, delta):
    card_int = SPACE.to_int(card)

    self.taus_completer.update_count(card, delta)
    self.all_different_completer.update_count(card, delta)
    self.one_same_completer.update_count(card, delta)
    self.initial_9_completer.update_count(card, delta)

    for c in self.cards:
      # Ensure that the cards are different. If this is true, it doesn't
      # matter which order we call update_count and update_lookup.
      assert c != card
      completer = SPACE.negasum(card, c)

      self.taus_completer.update_lookup(completer, delta)
      num_same = sum(card[i] == c[i] for i in range(SPACE.COORDS))
      if num_same == 0:
        self.all_different_completer.update_lookup(completer, delta)
      if num_same == 1:
        self.one_same_completer.update_lookup(completer, delta)
      if len(self.cards) < 9:
        self.initial_9_completer.update_lookup(completer, delta)
