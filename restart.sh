kill $(ps -eF | grep 'python tau.py' | grep -v 'grep' | perl -wlne 'print $1 if /(\d+)/'); git pull && (nohup python tau.py &)
