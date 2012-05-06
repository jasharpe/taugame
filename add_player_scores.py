from db import get_session
from state import Score
import json

def main():
  s = get_session()
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

if __name__ == "__main__":
  main()
