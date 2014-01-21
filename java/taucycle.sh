# Run a complete cycle of bqtau card generation, previewing results.
set -e
javac *.java
java SpriteGenerator ../static/cards.png LARGE NOTRETINA
open ../static/cards.png
java SpriteGenerator ../static/cards@2x.png LARGE RETINA
open ../static/cards@2x.png
java SpriteGenerator ../static/smallcards.png SMALL NOTRETINA
open ../static/smallcards.png
java SpriteGenerator ../static/smallcards@2x.png SMALL RETINA
open ../static/smallcards@2x.png
