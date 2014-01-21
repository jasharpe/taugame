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

public class BQSpriteGenerator {
  private static final boolean LARGE = true;

  public static void main(String[] args) {
    if (args.length != 2) {
      throw new IllegalArgumentException(
          "Requires exactly two arguments, a file name of result, and whether to make a 2x (retina) image.");
    }

    File imageFile = new File(args[0]);
    boolean retina = args[1].equals("1");

    int width = 80;
    int height = 120;
    if (!LARGE) {
      width = 40;
      height = 60;
    } else if (retina) {
      width = 160;
      height = 240;
    }
    int totalWidth = width * 64;
    int totalHeight = height;

    BufferedImage bufferedImage = new BufferedImage(totalWidth, totalHeight, BufferedImage.TYPE_INT_ARGB);
    Graphics2D graphics = bufferedImage.createGraphics();

    graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

    //colour, number, shape
    for (int colour = 0; colour < 4; colour++) {
      for (int number = 0; number < 4; number++) {
        for (int shape = 0; shape < 4; shape++) {
          int xBase = (colour + 4 * number + 16 * shape) * width;
          int yBase = 0;
          drawCard(graphics, retina, xBase, yBase, width, height, colour, number, shape);
        }
      }
    }

    try {
      ImageIO.write(bufferedImage, "PNG", imageFile);
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
  }

  private static void drawCard(Graphics2D graphics, boolean retina, int xBase,
      int yBase, int width, int height, int colour, int number,
      int shape) {
    // get shape positions
    int[] xs;
    int[] ys;
    if (number == 0) {
      xs = new int[] { xBase + width / 2 };
      ys = new int[] { yBase + height / 2 };
    } else if (number == 1) {
      xs = new int[] {
        xBase + width / 3,
        xBase + width - width / 3 };
      ys = new int[] {
        yBase + height / 2,
        yBase + height / 2 };
    } else if (number == 2) {
      xs = new int[] {
        xBase + width / 3,
              xBase + width / 2,
              xBase + width - width / 3 };
      ys = new int[] {
        yBase + height / 2 - width / 6,
              yBase + height / 2 + width / 6,
              yBase + height / 2 - width / 6 };
    } else {
      xs = new int[] {
        xBase + width / 3,
        xBase + width / 3,
        xBase + width - width / 3,
        xBase + width - width / 3 };
      ys = new int[] {
        yBase + height/2 - (width+5) / 6,
        yBase + height/2 + (width+5) / 6,
        yBase + height/2 - (width+5) / 6,
        yBase + height/2 + (width+5) / 6 };
    }

    List<Shape> shapes = new ArrayList<Shape>();
    int number1 = 10;
    int number2 = 20;
    if (!LARGE) {
      number1 = 5;
      number2 = 10;
    } else if (retina) {
      number1 = 20;
      number2 = 40;
    }
    for (int i = 0; i < number + 1; i++) {
      if (shape == 0) {
        shapes.add(new Ellipse2D.Double(xs[i] - number1, ys[i] - number1, number2, number2));  
      } else if (shape == 1) {
        shapes.add(new Rectangle(xs[i] - number1, ys[i] - number1, number2, number2));
      } else if (shape == 2) {
        shapes.add(new Triangle(xs[i] - number1, ys[i] - number1, number2, number2).getShape());
      } else {
        shapes.add(new Diamond(xs[i] - number1, ys[i] - number1, number2, number2).getShape());
      }
    }

    Color color;
    if (colour == 0) {
      color = new Color(0xDF004F);
    } else if (colour == 1) {
      color = new Color(0xFFBA00);
    } else if (colour == 2) {
      color = new Color(0x1826B0);
    } else {
      color = new Color(0x74E600);
    }

    graphics.setPaint(color);
    for (Shape aShape : shapes) {
      graphics.fill(aShape);
    }
  }
}
