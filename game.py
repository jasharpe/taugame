import random, itertools, time
from operator import mod

class Game(object):
  def __init__(self, type, size, quick=False):
    self.type = type
    self.size = size
    self.min_number = 12
    self.scores = {}
    self.deck = create_deck()
    self.board = []
    self.boards = []
    self.taus = []
    self.target_tau = None
    self.compress_and_fill_board()
    self.started = False
    self.start_time = 0
    self.ended = False
    self.player_ranks = {}

    if quick:
      for i in xrange(0, 23 if size == 3 else 12):
        self.take_tau()

  def take_tau(self):
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
    while len(filter(None, self.board)) < self.min_number or (self.no_subset_is_tau(filter(None, self.board), self.size) and self.type != "g3tau"):
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

    # compute a new target tau for Generalized 3 Tau
    if self.type == "g3tau":
      self.target_tau = self.get_random_target(self.board)

    # add Nones at the end as necessary
    while len(self.board) < self.min_number:
      self.board.append(None)

  def get_random_target(self, board):
      no_nones = filter(None, board)
      if len(no_nones) < 3:
        return []
      else:
        all_card_subsets = [card_subset for card_subset in itertools.combinations(no_nones, 3)]
        return self.sum_cards(all_card_subsets[random.randint(0, len(all_card_subsets) - 1)])

  def is_over(self):
    return len(self.deck) == 0 and self.no_subset_is_tau(filter(None, self.board), self.size)

  def get_all_taus(self):
    taus = []
    for card_subset in itertools.combinations(filter(None, self.board), self.size):
      if self.is_tau(card_subset):
        taus.append(card_subset)
    return taus

  def get_tau(self):
    for card_subset in itertools.combinations(filter(None, self.board), self.size):
      if self.is_tau(card_subset):
        return card_subset
    return []

  def board_contains(self, cards):
    return not any([not card in self.board for card in cards])

  def get_total_time(self):
    return time.time() - self.start_time

  def submit_tau(self, cards, player):
    if len(cards) == self.size and self.board_contains(cards) and self.is_tau(cards):
      if not player in self.scores:
        self.scores[player] = []
      self.scores[player].append(cards)
      self.boards.append(list(self.board))
      self.taus.append((self.get_total_time(), len(self.get_all_taus()), player, cards))
      self.remove_cards(cards)
      self.compress_and_fill_board()
      if self.is_over():
        self.total_time = self.get_total_time()
        self.ended = True
      return True
    else:
      return False

  def sum_cards(self, cards):
    return [sum(zipped) % 3 for zipped in zip(*cards)]

  def is_tau_basic(self, cards):
    return not any(self.sum_cards(cards))

  def is_tau(self, cards):
    if len(cards) == 3 and self.type in ["3tau", "6tau"]:
      return self.is_tau_basic(cards)
    elif len(cards) == 3 and self.type in ["g3tau"]:
      return self.sum_cards(cards) == self.target_tau
    elif len(cards) == 6:
      return self.is_tau_basic(cards) and self.no_subset_is_tau(cards, 3)
    raise Exception("Cards " + cards + " are not valid for this game type: " + self.type)

  def no_subset_is_tau(self, cards, subset_size):
    for card_subset in itertools.combinations(cards, subset_size):
      if self.is_tau(card_subset):
        return False
    return True

def create_deck():
  deck = list(itertools.product(*[range(0, 3) for i in range(0, 4)]))
  random.shuffle(deck)
  return deck
