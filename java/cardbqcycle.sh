# Run a complete cycle of physical bqtau card generation, previewing results.
set -e
javac *.java
rm -rf small_cards
mkdir small_cards
java BQCardGenerator small_cards/bqcard
open small_cards/bqcard_0_small.png
