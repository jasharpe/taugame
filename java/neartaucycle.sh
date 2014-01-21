# Run a complete cycle of bqtau card generation, previewing results.
set -e
javac *.java
java NearTauSpriteGenerator ../static/neartau.png NOTRETINA
open ../static/neartau.png
java NearTauSpriteGenerator ../static/neartau@2x.png RETINA
open ../static/neartau@2x.png
