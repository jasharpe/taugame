# Run a complete cycle of bqtau card generation, previewing results.
set -e
javac *.java
java BQSpriteGenerator ../static/bqcards.png
open ../static/bqcards.png
