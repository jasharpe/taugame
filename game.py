import logging
import random, itertools, time
from operator import mod

I3TAU_CALCULATION_LOGGING_THRESHOLD = 0.25

class InvalidGameType(Exception):
  pass

game_types = ['3tau', 'g3tau', '6tau', 'i3tau', 'e3tau', '4tau']

type_to_size_map = {
  '3tau': 3,
  'g3tau': 3,
  '6tau': 6,
  'i3tau': 3,
  'e3tau': 3,
  '4tau': 4,
}

def shuffled(xs):
  xs = list(xs)
  random.shuffle(xs)
  return xs

class Game(object):
  def __init__(self, type, quick=False):
    self.type = type
    try:
      self.size = type_to_size_map[type]
    except KeyError:
      raise InvalidGameType()
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
      # Play the game nearly to completion.
      while self.deck:
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
    while len(filter(None, self.board)) < self.min_number or (self.no_subset_is_tau(filter(None, self.board), self.size) and self.type not in ['g3tau', '4tau']):
      if not self.deck:
        break
      to_add = self.size
      add_indices = []
      for i in range(0, len(self.board)):
        if to_add > 0 and self.board[i] is None:
          add_indices.append(i)
          to_add -= 1

      while to_add > 0:
        self.board.append(None)
        add_indices.append(len(self.board) - 1)
        to_add -= 1

      if self.type == 'i3tau':
        # Try to do an Insane 3 Tau deal (i.e. only one tau is present after
        # dealing.) If it fails, fall back to normal behaviour.
        init_time = time.time()
        i3tau_new_cards = self.find_i3tau_new_cards()
        calculation_time = time.time() - init_time
        if calculation_time > I3TAU_CALCULATION_LOGGING_THRESHOLD:
          logging.warning('Took %.03f seconds to deal 3 new cards for Insane 3 Tau',
              calculation_time)

        if i3tau_new_cards is not None:
          # We need to randomize the order of the new cards.
          # To see why, observe that:
          # - After a tau is found in a board that has only one, any tau in
          #   the next board must involve the new cards.
          # - Because of the ordering of the values yielded by
          #   itertools.combinations, we select the lexicographically earliest
          #   index tuple that works.
          # This means that the probability that a new card is involved in the
          # tau might depend on its corresponding position in the index tuple.
          # Randomizing the order avoids this issue.
          i3tau_new_cards = shuffled(i3tau_new_cards)

          for i, card in zip(add_indices, i3tau_new_cards):
            self.deck.remove(card)
            self.board[i] = card
          add_indices = []

      if self.type == 'e3tau':
        # Do an Easy 3 Tau deal. That means to try to create a large number of
        # taus after dealing.
        init_time = time.time()

        for i in add_indices:
          card = self.find_e3tau_new_card()
          self.deck.remove(card)
          self.board[i] = card
        add_indices = []

        logging.warning('Took %.03f seconds to deal 3 new cards for Easy 3 Tau',
            time.time() - init_time)

      for i in add_indices:
        if not self.deck:
          break
        self.board[i] = self.deck.pop()


    # compute a new target tau for Generalized 3 Tau and 4 Tau
    if self.type in ['g3tau', '4tau']:
      self.target_tau = self.get_random_target(self.board)

    # add Nones at the end as necessary
    while len(self.board) < self.min_number:
      self.board.append(None)

    # For Insane 3 Tau and Easy 3 Tau, the initial positions of cards must be
    # randomized, because the first 3 dealt cards always form a Tau.
    if self.type in ['i3tau', 'e3tau'] and len(filter(None, self.board)) + len(self.deck) == 3**4:
      random.shuffle(self.board)

  def get_random_target(self, board):
      no_nones = filter(None, board)
      if len(no_nones) < self.size:
        return []
      else:
        all_card_subsets = [card_subset for card_subset in itertools.combinations(no_nones, self.size)]
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
        self.target_tau = None
        self.ended = True
      return True
    else:
      return False

  def sum_cards(self, cards):
    return [sum(zipped) % 3 for zipped in zip(*cards)]

  def negate(self, card):
    # Note that in Python, the % operator always returns a non-negative number.
    return map(lambda x: (-x)%3, card)

  def negasum(self, a, b):
    return self.negate(self.sum_cards([a,b]))

  def is_tau_basic(self, cards):
    return not any(self.sum_cards(cards))

  def is_tau(self, cards):
    if len(cards) == 3 and self.type in ["3tau", "6tau", "i3tau", "e3tau"]:
      return self.is_tau_basic(cards)
    elif len(cards) == 3 and self.type in ["g3tau"]:
      return self.sum_cards(cards) == self.target_tau
    elif len(cards) == 4 and self.type in ['4tau']:
      return self.sum_cards(cards) == self.target_tau
    elif len(cards) == 6:
      return self.is_tau_basic(cards) and self.no_subset_is_tau(cards, 3)
    raise Exception("Cards %s are not valid for this game type: %s" % (cards, self.type))

  def count_tau_subsets(self, cards, subset_size):
    count = 0
    for card_subset in itertools.combinations(cards, subset_size):
      if self.is_tau(card_subset):
        count += 1
    return count

  def no_subset_is_tau(self, cards, subset_size):
    return not self.count_tau_subsets(cards, subset_size)

  def find_i3tau_new_cards(self):
    # When this routine fails to find suitable new cards, returns None.
    # This is faster than a straightforward itertools.combination approach,
    # because if the first or second card we pick causes the board to have
    # more than a single set, then we don't iterate through choices of a
    # third card. (The straightforward approach was tested and found to be
    # too slow.)
    i3tau_new_cards = None
    candidate_board = filter(None, self.board)

    def rec(start, to_add):
      if to_add == 0:
        return self.count_tau_subsets(candidate_board, self.size) == 1

      for i in range(start, len(self.deck)):
        candidate_board.append(self.deck[i])
        if self.count_tau_subsets(candidate_board, self.size) <= 1:
          if rec(i+1, to_add-1):
            return True
        candidate_board.pop()

    if not rec(0, self.size):
      return None

    return candidate_board[-self.size:]

  def find_e3tau_new_card(self):
    # Find the earliest card that maximizes the number of taus present.
    # The deck must be non-empty when calling this routine.

    # Note: The routine here is optimized a bit because originally I
    # was seeing deal times as much as ~200ms on my laptop, which could
    # be steep if several people are playing games at once.
    # In the optimize form, dealing time is around ~1ms.
    assert self.deck

    # Figure out how many taus are completed by each card.
    existing_cards = filter(None, self.board)
    completion_map = {}
    for a,b in itertools.combinations(existing_cards, 2):
      key = tuple(self.negasum(a,b))
      completion_map[key] = 1 + completion_map.get(key, 0)

    # Find the card that completes the most taus.
    best = -1
    best_card = None
    for card in self.deck:
      cur = completion_map.get(tuple(card), 0)

      # Assertion commented out for speed.
      #assert (cur + self.count_tau_subsets(existing_cards, self.size)
      #        == self.count_tau_subsets(existing_cards + [card], self.size))

      if cur > best:
        best = cur
        best_card = card

    assert best_card is not None
    return best_card

def create_deck():
  deck = list(itertools.product(*[range(0, 3) for i in range(0, 4)]))
  random.shuffle(deck)
  return deck
