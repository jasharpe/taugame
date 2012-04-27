import math

def fmt_time(time):
  seconds = int(math.floor(time))
  minutes = seconds / 60
  remainder = time - minutes * 60
  return "%dm %01.02fs" % (minutes, remainder)
