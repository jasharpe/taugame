import random, itertools, time
from operator import mod

class Game(object):
  def __init__(self, size, quick=False):
    self.size = size
    self.min_number = 12
    self.scores = {}
    self.deck = create_deck()
    self.board = []
    self.compress_and_fill_board()
    self.started = False
    self.start_time = 0
    self.ended = False

    if quick:
      for i in xrange(0, 23):
        self.submit_tau(self.get_tau(), "dummy")

  def start(self):
    self.start_time = time.time()
    self.started = True

  def remove_cards(self, cards):
    for i in range(0, len(self.board)):
      if self.board[i] in cards:
        self.board[i] = None

  def compress_and_fill_board(self):
    # fill in gaps
    if len(self.board) > self.min_number:
      gaps = []
      for i in range(0, len(self.board)):
        if i > self.min_number - 1 and self.board[i] and gaps:
          self.board[gaps.pop(0)] = self.board[i]
          self.board[i] = None
        if self.board[i] is None:
          gaps.append(i)

    # trim end of Nones
    while self.board and self.board[-1] is None:
      self.board.pop()

    # add new cards to fill in gaps
    while len(filter(None, self.board)) < self.min_number or no_subset_is_tau(filter(None, self.board), self.size):
      if not self.deck:
        break
      to_add = self.size
      for i in range(0, len(self.board)):
        if not self.deck:
          break
        if to_add > 0 and self.board[i] is None:
          self.board[i] = self.deck.pop()
          to_add -= 1

      for i in range(0, to_add):
        if not self.deck:
          break
        self.board.append(self.deck.pop())

    # add Nones at the end as necessary
    while len(self.board) < self.min_number:
      self.board.append(None)

  def is_over(self):
    return len(self.deck) == 0 and no_subset_is_tau(filter(None, self.board), self.size)

  def get_tau(self):
    for card_subset in itertools.combinations(filter(None, self.board), self.size):
      if is_tau(card_subset):
        return card_subset
    return []

  def board_contains(self, cards):
    return not any([not card in self.board for card in cards])

  def get_total_time(self):
    return time.time() - self.start_time

  def submit_tau(self, cards, player):
    if len(cards) == self.size and self.board_contains(cards) and is_tau(cards):
      self.remove_cards(cards)
      if not player in self.scores:
        self.scores[player] = []
      self.scores[player].append(cards)
      self.compress_and_fill_board()
      if self.is_over():
        self.total_time = self.get_total_time()
        self.ended = True
      return True
    else:
      return False

def create_deck():
  deck = list(itertools.product(*[range(0, 3) for i in range(0, 4)]))
  random.shuffle(deck)
  return deck

def is_tau(cards):
  is_tau_basic = not any(sum(zipped) % 3 for zipped in zip(*cards))
  if len(cards) == 3:
    return is_tau_basic
  elif len(cards) == 6:
    return is_tau_basic and no_subset_is_tau(cards, 3)

def no_subset_is_tau(cards, subset_size):
  for card_subset in itertools.combinations(cards, subset_size):
    if is_tau(card_subset):
      return False
  return True
