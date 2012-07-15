# To aid with game design, determine the expected number of taus present
# for given rules and board size.

from scipy.misc import comb

# k = board size
def expected_3taus(k):
  # For any three cards on the board, they form a 3tau with probability 1/79,
  # since after fixing 2 cards, there is a unique third.
  return comb(k, 3) / 79.

def expected_bqtaus(k):
  # After fixing 3 cards, there is a unique fourth.
  return comb(k, 4) / 61.
