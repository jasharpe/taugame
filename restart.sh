kill $(ps -eF | grep 'python tau.py' | grep -v 'grep' | perl -wlne 'print $1 if /(\d+)/'); git pull && ./make_cpp.sh && (nohup python tau.py >> log.out 2>>log.err &)
