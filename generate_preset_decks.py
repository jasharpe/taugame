from constants import GAME_TYPE_INFO
from db import get_session
from state import Score
from sqlalchemy import desc
import fingeo

def get_wrong_property(space, cards):
  s = space.sum_cards(cards)
  for (i, val) in enumerate(s):
    if val != 0:
      return i
  return -1

def main():
  print "# generated by generate_preset_decks.py"

  decks = {}
  tau_lists = {}
  target_lists = {}
  wrong_property_lists = {}
  seeds = {}

  for game_type in map(lambda x: x[0], GAME_TYPE_INFO):
    session = get_session()
    score = session.query(Score).filter_by(game_type=game_type).order_by(desc(Score.date)).first()
    try:
      deck = list(reversed(map(tuple, score.game.deck)))
    except:
      deck = []
    need_deck = not deck
    taus = []
    targets = []
    wrong_properties = []
    for state in score.game.states:
      space = fingeo.get_space(game_type)
      targets.append(space.sum_cards(state.cards))
      wrong_properties.append(get_wrong_property(space, state.cards))
      taus.append(state.cards)
      if need_deck:
        for card in state.board:
          if card and not tuple(card) in deck:
            deck.append(tuple(card))
        
    decks[game_type] = list(reversed(deck))
    tau_lists[game_type] = taus
    target_lists[game_type] = list(reversed(targets))
    wrong_property_lists[game_type] = list(reversed(wrong_properties))
    seeds[game_type] = score.game.seed
  print "PRESET_DECKS = {"
  for (game_type, deck) in decks.items():
    print "'%s' : %s," % (game_type, str(deck))
  print "}"
  print "PRESET_TAUS = {"
  for (game_type, taus) in tau_lists.items():
    print "'%s' : %s," % (game_type, str(taus))
  print "}"
  print "PRESET_TARGETS = {"
  for (game_type, targets) in target_lists.items():
    print "'%s' : %s," % (game_type, str(targets or None))
  print "}"
  print "PRESET_WRONG_PROPERTIES = {"
  for (game_type, wrong_properties) in wrong_property_lists.items():
    print "'%s' : %s," % (game_type, str(wrong_properties or None))
  print "}"
  print "PRESET_SEEDS = {"
  for (game_type, seed) in seeds.items():
    print "'%s' : %d," % (game_type, seed)
  print "}"

if __name__ == "__main__":
  main()
