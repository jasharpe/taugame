# Run a complete cycle of bqtau card generation, previewing results.
set -e
javac *.java
java BQSpriteGenerator ../static/bqcards.png 0
open ../static/bqcards.png
java BQSpriteGenerator ../static/bqcards@2x.png 1
open ../static/bqcards@2x.png
