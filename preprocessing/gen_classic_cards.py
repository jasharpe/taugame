from __future__ import division

import Image
import os
import sys
import numpy as np
import time

WIDTH = 80
HEIGHT = 120

SHAPE_HEIGHT = 30

COLOURS = [(219, 35, 2), (2, 170, 26), (80, 1, 128)]

VERTICAL_OFFSETS = {
  1: [0],
  2: [18, -18],
  3: [37, 0, -37],
}

SHAPES_DIR = "rawshapes"

def make_file(shape, shading):
  return "{}{}.png".format(shading, shape)

def recolour(img, colour):
  img = img.convert('RGBA')
  new_data = []
  for pixel in img.getdata():
    if pixel[0] == 0 and pixel[1] == 0 and pixel[2] == 0:
      new_data.append(colour)
    else:
      new_data.append((255, 255, 255, 0))
  img.putdata(new_data)
  return img

def main(dest_file):
  canvas = Image.new("RGBA", (81 * WIDTH, HEIGHT), (255, 255, 255, 0))
  card_number = 0
  start = time.time()
  img_cache = {}
  coloured_img_cache = {}
  for shape in ["diamond", "oval", "peanut"]:
    for shading in ["empty", "shaded", "solid"]:
      for number in [1, 2, 3]:
        for colour in COLOURS:
          shape_key = make_file(shape, shading)
          if (shape_key, colour) in coloured_img_cache:
            img = coloured_img_cache[(shape_key, colour)]
          else:
            if shape_key in img_cache:
              img = img_cache[shape_key]
            else:
              img = Image.open(os.path.join(SHAPES_DIR, shape_key))
              img = img.rotate(90)
              img_cache[shape_key] = img
            img = recolour(img, colour)
            (orig_width, orig_height) = img.size
            scale_factor = SHAPE_HEIGHT / orig_height
            img = img.resize((int(round(scale_factor * orig_width)),
              int(round(scale_factor * orig_height))),
              Image.ANTIALIAS)
            coloured_img_cache[(shape_key, colour)] = img

          card_offset = card_number * WIDTH
          middle = card_offset + WIDTH / 2
          img_width, img_height = img.size
          left = int(round(middle - img_width / 2))
          right = int(round(middle + img_width / 2))
          v_middle = HEIGHT / 2
          upper = int(round(v_middle - img_height / 2))
          lower = int(round(v_middle + img_height / 2))
          for vertical_offset in VERTICAL_OFFSETS[number]:
            box = (left, upper + vertical_offset, right, lower + vertical_offset)
            canvas.paste(img, box)

          card_number += 1
  print "Time: " + str(time.time() - start)
  canvas.show()
  canvas.save(dest_file)

if __name__ == "__main__":
  main(sys.argv[1])
