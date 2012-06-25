def oxford(strs, conjunction):
  if len(strs) == 0:
    return ""
  elif len(strs) == 1:
    return strs[0]
  elif len(strs) == 2:
    return (" %s " % (conjunction)).join(strs)
  else:
    not_last_strs = strs[:-1]
    last = strs[-1]
    return "%s, %s %s" % (", ".join(not_last_strs), conjunction, last)
