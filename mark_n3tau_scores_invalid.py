from state import Score
from db import get_session

if __name__ == "__main__":
  session = get_session()
  for score in session.query(Score).filter(Score.game_type == "n3tau"):
    score.invalid = True
    session.add(score)
  session.commit()
