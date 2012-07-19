import math

def fmt_time(time):
  hours, remainder = divmod(int(time), 3600)
  minutes, seconds = divmod(remainder, 60)
  if hours:
    return '%dh %dm %01.02fs' % (hours, minutes, time - 3600 * hours - 60 * minutes)
  else:
    return '%dm %01.02fs' % (minutes, time - 3600 * hours - 60 * minutes)
