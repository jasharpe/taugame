import logging
import random, itertools, time
from operator import mod

import fingeo

I3TAU_CALCULATION_LOGGING_THRESHOLD = 0.25

class InvalidGameType(Exception):
  pass

type_to_size_map = {
  '3tau': 3,
  'g3tau': 3,
  '6tau': 6,
  'i3tau': 3,
  'e3tau': 3,
  '4tau': 4,
  '3ptau': 3,
  'z3tau': 3,
  '4otau': 4,
  'n3tau': 3,
  'bqtau': 4,
}

type_to_min_board_size = {
  '3tau': 12,
  'g3tau': 12,
  '6tau': 12,
  'i3tau': 12,
  'e3tau': 12,
  '4tau': 12,
  '3ptau': 12,
  'z3tau': 12,
  '4otau': 9,
  'n3tau': 12,
  'bqtau': 12,
}

game_types = type_to_size_map.keys()

Z3TAU_COUNT = 6

def shuffled(xs):
  xs = list(xs)
  random.shuffle(xs)
  return xs

# Return value for submit_tau and submit_client_tau.
class SubmitTauResult(object):
  SUCCESS = 0
  INVALID = 1
  OLD_FOUND_PUZZLE = 2

  def __init__(self, status, index=None):
    self.status = status
    self.index = index

class Game(object):
  def __init__(self, type, quick=False):
    self.type = type
    try:
      self.size = type_to_size_map[type]
    except KeyError:
      raise InvalidGameType()
    if self.type == '3ptau':
      self.space = fingeo.ProjectiveSpace()
    elif self.type == 'bqtau':
      self.space = fingeo.BooleanSpace()
    else:
      self.space = fingeo.AffineSpace()
    self.min_number = type_to_min_board_size[self.type]
    self.scores = {}
    self.deck = shuffled(self.space.all_points())
    self.board = []
    self.boards = []
    self.taus = []
    self.target_tau = None
    # A number between 0 and 3 indicating the wrong property
    # in n3tau.
    self.wrong_property = None
    self.compress_and_fill_board()
    self.started = False
    self.start_time = 0
    self.most_recent_start_time = 0
    self.previous_time = 0
    self.ended = False
    self.player_ranks = {}
    self.paused = False

    if quick:
      # Play the game nearly to completion.
      if self.type == 'z3tau':
        tau_count = self.count_taus()
        while len(self.taus) < tau_count-1:
          self.take_tau()
      else:
        while self.deck:
          self.take_tau()

  def take_tau(self):
    self.submit_tau(self.get_hint(), "dummy")

  def start(self):
    self.start_time = time.time()
    self.most_recent_start_time = self.start_time
    self.started = True

  def is_pausable(self):
    return self.started and not self.ended

  def pause(self):
    self.previous_time += time.time() - self.most_recent_start_time
    self.paused = True

  def unpause(self):
    self.most_recent_start_time = time.time()
    self.paused = False

  def remove_cards(self, cards):
    for i in range(0, len(self.board)):
      if self.board[i] in cards:
        self.board[i] = None

  def compress_and_fill_board(self):
    # Puzzle 3 Tau only deals once and requires Z3TAU_COUNT taus exactly.
    if self.type == 'z3tau' and not self.board:
      while Z3TAU_COUNT != self.count_tau_subsets(self.deck[-self.min_number:], self.size):
        random.shuffle(self.deck)

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
    while len(filter(None, self.board)) < self.min_number or (self.type not in ['g3tau', '4tau'] and self.no_subset_is_tau(filter(None, self.board), self.size)):
      if not self.deck:
        break
      num_cards_on_board = len(filter(None, self.board))
      if num_cards_on_board > self.min_number - 3 and num_cards_on_board < self.min_number:
        to_add = self.min_number - num_cards_on_board
      else:
        to_add = 3
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
    elif self.type in ['n3tau']:
      self.wrong_property = self.get_wrong_property(self.board)

    # add Nones at the end as necessary
    while len(self.board) < self.min_number:
      self.board.append(None)

    # For Insane 3 Tau and Easy 3 Tau, the initial positions of cards must be
    # randomized, because the first 3 dealt cards always form a Tau.
    if self.type in ['i3tau', 'e3tau'] and len(filter(None, self.board)) + len(self.deck) == 3**4:
      random.shuffle(self.board)

  def get_wrong_property(self, board):
    no_nones = filter(None, board)
    if len(no_nones) < self.size:
      return None
    counts = []
    for i in xrange(0, 4):
      count = self.count_tau_subsets(no_nones, 3, wrong_property=i)
      if count > 0:
        counts.append((i, count))
    if not counts:
      return None
    return random.choice(counts)[0]

  def get_random_target(self, board):
      no_nones = filter(None, board)
      if len(no_nones) < self.size:
        return []
      else:
        all_card_subsets = [card_subset for card_subset in itertools.combinations(no_nones, self.size)]
        return self.space.sum_cards(all_card_subsets[random.randint(0, len(all_card_subsets) - 1)])

  def is_over(self):
    if self.type == 'z3tau':
      return len(self.taus) == self.count_taus()
    else:
      return len(self.deck) == 0 and self.no_subset_is_tau(filter(None, self.board), self.size)

  def get_all_taus(self, wrong_property=None):
    taus = []
    for card_subset in itertools.combinations(filter(None, self.board), self.size):
      if self.is_tau(card_subset, wrong_property=wrong_property):
        taus.append(card_subset)
    return taus

  def count_taus(self):
    return len(self.get_all_taus(wrong_property=self.wrong_property))

  def get_hint(self):
    for cards in self.get_all_taus(wrong_property=self.wrong_property):
      if self.type != 'z3tau' or self.old_found_puzzle_tau_index(cards) is None:
        return cards
    return []

  def board_contains(self, cards):
    return not any([not card in self.board for card in cards])

  def get_actual_total_time(self):
    return time.time() - self.start_time

  def get_total_time(self):
    if self.paused:
      return self.previous_time
    else:
      return time.time() - self.most_recent_start_time + self.previous_time

  def submit_tau(self, cards, player):
    if not self.ended and len(cards) == self.size and self.board_contains(cards) and self.is_tau(cards, wrong_property=self.wrong_property):
      if self.type == 'z3tau':
        index = self.old_found_puzzle_tau_index(cards)
        if index is not None:
          return SubmitTauResult(SubmitTauResult.OLD_FOUND_PUZZLE, index=index)

      if not player in self.scores:
        self.scores[player] = []
      self.scores[player].append(cards)
      self.boards.append(list(self.board))
      self.taus.append((self.get_total_time(), self.count_taus(), player, cards))

      if self.type != 'z3tau':
        self.remove_cards(cards)
        self.compress_and_fill_board()

      if self.is_over():
        self.total_time = self.get_total_time()
        self.target_tau = None
        self.ended = True
      return SubmitTauResult(SubmitTauResult.SUCCESS)
    else:
      return SubmitTauResult(SubmitTauResult.INVALID)

  def old_found_puzzle_tau_index(self, cards):
    cards = frozenset(cards)
    found = map(frozenset, self.get_found_puzzle_taus())
    
    try:
      return found.index(cards)
    except ValueError:
      return None

  def get_found_puzzle_taus(self):
    if self.type != 'z3tau':
      return None
    return [cards for (time, num_taus, player, cards) in self.taus]

  def get_client_found_puzzle_taus(self):
    server_taus = self.get_found_puzzle_taus()
    if server_taus is None:
      return None
    return [map(self.space.to_client_card, cards) for cards in server_taus]

  def is_tau_basic(self, cards):
    return not any(self.space.sum_cards(cards))

  def is_n3tau(self, cards, wrong_property):
    correct_properties = map(lambda x: 1 if x else 0, self.space.sum_cards(cards))
    if wrong_property is not None:
      return sum(correct_properties) == 1 and correct_properties[wrong_property] == 1
    else:
      return sum(correct_properties) == 1

  def is_tau(self, cards, wrong_property=None):
    if len(cards) == 3 and self.type in ["3tau", "6tau", "i3tau", "e3tau", "3ptau", "z3tau"]:
      return self.is_tau_basic(cards)
    if len(cards) == 3 and self.type in ["n3tau"]:
      return self.is_n3tau(cards, wrong_property)
    elif len(cards) == 3 and self.type in ["g3tau"]:
      return self.space.sum_cards(cards) == self.target_tau
    elif len(cards) == 4 and self.type in ['4tau']:
      return self.space.sum_cards(cards) == self.target_tau
    elif len(cards) == 4 and self.type in ['4otau']:
      for i in xrange(1, 4):
        this_pair = [cards[0], cards[i]]
        that_pair = map(lambda j: cards[j], [j for j in xrange(1, 4) if not j in [0, i]])
        if self.space.sum_cards(this_pair) == self.space.sum_cards(that_pair):
          return True
      return False
    elif len(cards) == 4 and self.type in ['bqtau']:
      return self.is_tau_basic(cards)
    elif len(cards) == 6:
      return self.is_tau_basic(cards) and self.no_subset_is_tau(cards, 3)
    raise Exception("Cards %s are not valid for this game type: %s" % (cards, self.type))

  def count_tau_subsets(self, cards, subset_size, wrong_property=None):
    count = 0
    for card_subset in itertools.combinations(cards, subset_size):
      if self.is_tau(card_subset, wrong_property=wrong_property):
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
      key = tuple(self.space.negasum(a,b))
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

  def get_client_board(self):
    return map(self.space.to_client_card, self.board)

  def get_client_target_tau(self):
    return self.space.to_client_card(self.target_tau)

  def submit_client_tau(self, cards, player):
    server_cards = map(self.space.from_client_card, cards)
    return self.submit_tau(server_cards, player)

  def get_client_hint(self):
    server_tau = self.get_hint()
    return map(self.space.to_client_card, server_tau)
