# Finite geometry routines for dealing with the spaces
# F_3^4 (standard tau) and P_5 F_2 (projective tau).

import itertools

def all_vectors(p, n):
  return list(itertools.product(*[range(p) for i in range(n)]))

class Space(object):
  def sum_cards(self, cards):
    return tuple([sum(zipped) % self.p for zipped in zip(*cards)])

  def negate(self, card):
    # Note that in Python, the % operator always returns a non-negative number.
    return tuple(map(lambda x: (-x) % self.p, card))

  def negasum(self, a, b):
    return self.negate(self.sum_cards([a,b]))

# The space F_3^4.
class AffineSpace(Space):
  def __init__(self):
    self.p = 3

  def all_points(self):
    return all_vectors(3, 4)

  def to_client_card(self, point):
    if point is not None and len(point) != 4:
      raise ValueError('Point length is %d (expected 4)' % len(point))

    return point

  def from_client_card(self, card):
    if card is not None and len(card) != 4:
      raise ValueError('Card length is %d (should be 4)' % len(card))

    return card

# The space P_5 F_2.
class ProjectiveSpace(Space):
  def __init__(self):
    self.p = 2

  def all_points(self):
    return filter(any, all_vectors(2, 6))

  def to_client_card(self, point):
    if point is not None and len(point) != 6:
      raise ValueError('Point length is %d (should be 6)' % len(point))

    if point is None:
      return None
    return tuple([(2*point[2*i] + point[2*i+1]) for i in range(3)])

  def from_client_card(self, card):
    if card is not None and len(card) != 3:
      raise ValueError('Card length is %d (should be 3)' % len(card))

    if card is None:
      return None
    point = []
    for v in card:
      point.append(v // 2)
      point.append(v % 2)
    return tuple(point)
