import java.awt.*;
import java.awt.event.*;
import java.awt.geom.*;
import java.awt.font.*;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Rectangle;
import java.awt.RenderingHints;
import java.awt.Shape;
import java.awt.TexturePaint;
import java.awt.geom.Ellipse2D;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;

public class NearTauSpriteGenerator {
  public static void main(String[] args) {
    if (args.length != 2) {
      throw new IllegalArgumentException(
          "Requires exactly two arguments, a file name of result, and RETINA|NOTRETINA.");
    }

    File imageFile = new File(args[0]);
    boolean retina = args[1].equals("RETINA");

    int width = 80;
    int height = 120;

    if (retina) {
      width *= 2;
      height *= 2;
    }

    int totalWidth = width * 4;
    int totalHeight = height;

    BufferedImage bufferedImage = new BufferedImage(totalWidth, totalHeight, BufferedImage.TYPE_INT_ARGB);
    Graphics2D graphics = bufferedImage.createGraphics();

    graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

  // draw 4 cards, one with all three shapes, one with all three colours, one with all three shadings, and one with three numbers
  for (int xBase = 0; xBase < 4; xBase++) {
    drawCard(graphics, retina, xBase, 0, width, height);
  }

  try {
    ImageIO.write(bufferedImage, "PNG", imageFile);
  } catch (Exception e) {
    throw new RuntimeException(e);
  }
}

private static void drawCard(Graphics2D graphics, boolean retina, int xBase,
    int yBase, int width, int height) {
  // get shape positions
  int[] xs;
  int[] ys;
  xs = new int[] {
    xBase*width + width / 3,
    xBase*width + width / 2,
    xBase*width + width - width / 3
  };
  ys = new int[] {
    yBase + height / 2 + width / 6,
    yBase + height / 2 - width / 6,
    yBase + height / 2 + width / 6
  };

    List<Shape> shapes = new ArrayList<Shape>();
    int number1 = 10;
    int number2 = 20;
    
    if (retina) {
      number1 *= 2;
      number2 *= 2;
    }

  // each card has 3 symbols
  if (xBase == 0) {
    // this is colour; do them all in squares
    graphics.setPaint(Color.RED);
    graphics.fill(new Rectangle(xs[0] - number1, ys[0] - number1, number2, number2));
    graphics.setPaint(Color.GREEN);
    graphics.fill(new Rectangle(xs[1] - number1, ys[1] - number1, number2, number2));
    graphics.setPaint(Color.BLUE);
    graphics.fill(new Rectangle(xs[2] - number1, ys[2] - number1, number2, number2));
  }
  if (xBase == 1) {
    // this is number; do 1,2,3
    int[] numbers = {2,1,3};
    for (int i = 0; i < 3; i++) {
      FontRenderContext frc = graphics.getFontRenderContext();
      int size = 26;
      if (retina) {
        size *= 2;
      }
      Font f = new Font("Times", Font.BOLD, size);
      String s = new String("" + numbers[i]);
      TextLayout tl = new TextLayout(s, f, frc);
      graphics.setPaint(Color.BLACK);
      int x_offset = 6;
      int y_offset = 9;
      if (retina) {
        x_offset *= 2;
        y_offset *= 2;
      }
      tl.draw(graphics, xs[i] - x_offset, ys[i] + y_offset);
    }
  }
  if (xBase == 2) {
    // this is shadings; do them all in circles
    graphics.draw(new Ellipse2D.Double(xs[0] - number1, ys[0] - number1, number2, number2));

    TexturePaint texture = null;
    if (retina) {
      BufferedImage textureImage = new BufferedImage(1, 4, BufferedImage.TYPE_INT_ARGB);
      textureImage.setRGB(0, 0, Color.BLACK.getRGB());
      textureImage.setRGB(0, 3, Color.BLACK.getRGB());
      texture = new TexturePaint(textureImage, new Rectangle(0, 1, 1, 4));      
    } else {
      BufferedImage textureImage = new BufferedImage(1, 2, BufferedImage.TYPE_INT_ARGB);
      textureImage.setRGB(0, 1, Color.BLACK.getRGB());
      texture = new TexturePaint(textureImage, new Rectangle(0, 1, 1, 2));
    }
    graphics.setPaint(texture);
    graphics.fill(new Ellipse2D.Double(xs[1] - number1, ys[1] - number1, number2, number2));
    graphics.setPaint(Color.BLACK);
    graphics.fill(new Ellipse2D.Double(xs[2] - number1, ys[2] - number1, number2, number2));
  }
  if (xBase == 3) {
    // this is shapes; one of each
    graphics.fill(new Triangle(xs[1] - number1, ys[1] - number1, number2, number2).getShape());
    graphics.fill(new Ellipse2D.Double(xs[0] - number1, ys[0] - number1, number2, number2));
    graphics.fill(new Rectangle(xs[2] - number1, ys[2] - number1, number2, number2));
  }
  }
}
