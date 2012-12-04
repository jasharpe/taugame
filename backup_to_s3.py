import datetime, os

if __name__ == "__main__":
  cmd = "s3cmd put hello s3://taugame_backups/hello_%s 1>>backup.out 2>&1" % datetime.datetime.utcnow().strftime("%Y_%m_%d_%H_%M")
  os.system(cmd)
