# To aid with game design, determine the expected number of taus present
# for given rules and board size.

from scipy.misc import comb

fns = []
def usefn(f):
  fns.append(f)
  return f

# k = board size
@usefn
def expected_3taus(k):
  # For any three cards on the board, they form a 3tau with probability 1/79,
  # since after fixing 2 cards, there is a unique third.
  return comb(k, 3) / 79.

@usefn
def expected_3ptaus(k):
  return comb(k, 3) / 61.

@usefn
def expected_bqtaus(k):
  # After fixing 3 cards, there is a unique fourth.
  return comb(k, 4) / 61.

@usefn
def expected_basic_3taus(k):
  return comb(k, 3) / 25.

@usefn
def expected_basic_3ptaus(k):
  return comb(k, 3) / 29.

@usefn
def expected_basic_bqtaus(k):
  return comb(k, 4) / 29.

for f in fns:
  print '%s(12) = %d' % (f.__name__, f(12))
