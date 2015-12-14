# Run a complete cycle of physical bqtau card generation, previewing results.
set -e
javac *.java
mkdir cards
java BQCardGenerator cards
open cards/bqcard_0.png
