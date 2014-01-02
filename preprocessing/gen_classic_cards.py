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
COLOUR_BLIND_COLOURS = [(2, 35, 219), (150, 150, 26), (40, 40, 40)]

VERTICAL_OFFSETS = {
  1: [0],
  2: [18, -18],
  3: [37, 0, -37],
}

SHAPES_DIR = "rawshapes"

def make_file(shape, shading):
  if shading == "shaded":
    shading = "empty"
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

def add_lines(img, scale, colour, shape):
  new_data = []
  cols_one = set()
  cols_two = set()
  cols_three = set()
  width, height = img.size
  if scale == 1:
    threshold = 4 if shape == "diamond" else 3
  else:
    threshold = 4 if shape == "diamond" else 2
  good_cols = set([0])
  for i, pixel in enumerate(img.getdata()):
    col = i % width
    diff = (abs(pixel[0] - colour[0]) + abs(pixel[1] - colour[1]) + abs(pixel[2] - colour[2]))
    is_black = diff < (100 if scale == 1 else 270)
    if not col in cols_one and is_black:
      cols_one.add(col)
    elif col in cols_one and not col in cols_two and not is_black:
      cols_two.add(col)
    elif col in cols_one and col in cols_two and not col in cols_three and is_black:
      cols_three.add(col)
    if col in cols_two and not col in cols_three and (col % (3 if scale == 1 else 2)) in good_cols and not col < threshold and not col > width - threshold:
      new_data.append(colour)
    else:
      new_data.append(pixel)
  img.putdata(new_data)
  return img

def gen_cards(colours, scale, dest_file):
  canvas = Image.new("RGBA", (int(round(81 * WIDTH * scale)), int(round(HEIGHT * scale))), (255, 255, 255, 0))
  card_number = 0
  start = time.time()
  img_cache = {}
  coloured_img_cache = {}
  for shape in ["diamond", "oval", "peanut"]:
    for shading in ["empty", "shaded", "solid"]:
      for number in [1, 2, 3]:
        for colour in colours:
          shape_key = (shape, shading)
          shape_file = make_file(shape, shading)
          if (shape_key, colour) in coloured_img_cache:
            img = coloured_img_cache[(shape_key, colour)]
          else:
            if shape_key in img_cache:
              img = img_cache[shape_key]
            else:
              img = Image.open(os.path.join(SHAPES_DIR, shape_file))
              img = img.rotate(90)
              img_cache[shape_key] = img
            img = recolour(img, colour)
            (orig_width, orig_height) = img.size
            scale_factor = int(round(SHAPE_HEIGHT * scale)) / orig_height
            img = img.resize((int(round(scale_factor * orig_width)),
              int(round(scale_factor * orig_height))),
              Image.ANTIALIAS)
            if shading == "shaded":
              img = add_lines(img, scale, colour, shape)
            coloured_img_cache[(shape_key, colour)] = img

          card_offset = card_number * int(round(WIDTH * scale))
          middle = card_offset + int(round(WIDTH * scale)) / 2
          img_width, img_height = img.size
          left = int(round(middle - img_width / 2))
          right = int(round(middle + img_width / 2))
          v_middle = int(round(HEIGHT * scale)) / 2
          upper = int(round(v_middle - img_height / 2))
          lower = int(round(v_middle + img_height / 2))
          for vertical_offset in VERTICAL_OFFSETS[number]:
            scaled_v_offset = int(round(vertical_offset * scale))
            box = (left, upper + scaled_v_offset, right, lower + scaled_v_offset)
            canvas.paste(img, box)

          card_number += 1
  print "Time: " + str(time.time() - start)
  canvas.show()
  canvas.save(dest_file)

def main(reg_dest_file, small_dest_file, colour_blind_dest_file, small_colour_blind_dest_file):
  gen_cards(COLOURS, 1, reg_dest_file)
  gen_cards(COLOURS, 0.5, small_dest_file)
  gen_cards(COLOUR_BLIND_COLOURS, 1, colour_blind_dest_file)
  gen_cards(COLOUR_BLIND_COLOURS, 0.5, small_colour_blind_dest_file)

if __name__ == "__main__":
  main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
