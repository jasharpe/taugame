# Run a complete cycle of physical bqtau card generation, previewing results.
set -e
javac *.java
rm -rf cards
mkdir cards
java BQCardGenerator cards/bqcard
open cards/bqcard_0.png
