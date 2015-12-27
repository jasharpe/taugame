from db import get_session
from state import Name
import json
import hashlib

def main():
  s = get_session()
  print ", ".join(['"' + hashlib.sha224(name.email).hexdigest() + '"' for name in s.query(Name)])

  """
  for score in s.query(Score):
    if not score.player_scores().keys():
      player_scores = {}
      for state in score.game.states:
        if state.player.name in player_scores:
          player_scores[state.player.name] += 1
        else:
          player_scores[state.player.name] = 1
      score.player_scores_json = json.dumps(player_scores)
      s.add(score)
  s.commit()
  """

if __name__ == "__main__":
  main()
