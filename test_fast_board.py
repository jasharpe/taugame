from unittest import TestCase, main
from fast_board import Board

class TestBoard(TestCase):
  def test_taus(self):
    board = Board()
    self.assertEquals(0, board.taus_completer.count)

    board.push((0,0,0,0))
    self.assertEquals(0, board.taus_completer.count)

    card = (0,0,0,1)
    self.assertEquals(0, board.taus_completer.peek(card))
    board.push(card)
    self.assertEquals(0, board.taus_completer.count)

    card = (0,0,0,2)
    self.assertEquals(1, board.taus_completer.peek(card))
    board.push(card)
    self.assertEquals(1, board.taus_completer.count)

    card = (0,0,1,0)
    self.assertEquals(1, board.taus_completer.peek(card))
    board.push(card)
    self.assertEquals(1, board.taus_completer.count)

    card = (0,0,2,0)
    self.assertEquals(2, board.taus_completer.peek(card))
    board.push(card)
    self.assertEquals(2, board.taus_completer.count)

  def test_all_different(self):
    board = Board()
    board.push((0,0,0,0))
    board.push((0,0,0,1))
    board.push((0,0,0,2))
    self.assertEquals(0, board.all_different_completer.count)

    board.push((1,1,1,1))
    board.push((2,2,2,2))
    self.assertEquals(1, board.all_different_completer.count)

  def test_one_same(self):
    board = Board()
    board.push((0,0,0,0))
    board.push((0,0,0,1))
    board.push((0,0,0,2))
    self.assertEquals(0, board.one_same_completer.count)

    board.push((1,1,1,0))
    board.push((2,2,2,0))
    self.assertEquals(1, board.one_same_completer.count)

  def test_initial_9(self):
    board = Board()

    board.push((0,0,0,0))
    board.push((0,0,0,1))
    board.push((0,0,0,2))

    board.push((0,0,1,0))
    board.push((0,0,2,0))

    board.push((0,1,0,0))
    board.push((0,2,0,0))

    board.push((1,0,0,0))
    board.push((2,0,0,0))

    self.assertEquals(4, board.initial_9_completer.count)

    board.push((2,2,0,0))
    self.assertEquals(5, board.initial_9_completer.count)

    board.push((2,2,1,0))
    self.assertEquals(5, board.initial_9_completer.count)


if __name__ == '__main__':
  main()
