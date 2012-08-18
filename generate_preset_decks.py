from constants import GAME_TYPE_INFO
from db import get_session
from state import Score
import fingeo

def main():
  print "# generated by generate_preset_decks.py"

  decks = {}
  tau_lists = {}
  target_lists = {}

  for game_type in map(lambda x: x[0], GAME_TYPE_INFO):
    session = get_session()
    score = session.query(Score).filter_by(num_players=1,game_type=game_type).first()
    deck = []
    taus = []
    targets = []
    for state in score.game.states:
      space = fingeo.get_space(game_type)
      targets.append(space.sum_cards(state.cards))
      taus.append(state.cards)
      for tau in state.board:
        if tau and not tuple(tau) in deck:
          deck.append(tuple(tau))
    decks[game_type] = list(reversed(deck))
    tau_lists[game_type] = taus
    target_lists[game_type] = list(reversed(targets))
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

if __name__ == "__main__":
  main()