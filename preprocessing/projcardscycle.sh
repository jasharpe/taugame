# Run a complete cycle of projective tau card generation, previewing results.
set -e
python gen_projcards.py ../static/projcards.png NOTRETINA
open ../static/projcards.png
python gen_projcards.py ../static/projcards@2x.png RETINA
open ../static/projcards@2x.png
