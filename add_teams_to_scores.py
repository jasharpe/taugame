from db import get_session
from state import Score, Team, get_or_create_team

if __name__ == "__main__":
  session = get_session()
  for score in session.query(Score).filter(Score.team == None):
    score.team = get_or_create_team(session, score.players)
    session.add(score)
  session.commit()
