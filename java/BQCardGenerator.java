import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Rectangle;
import java.awt.RenderingHints;
import java.awt.Shape;
import java.awt.BasicStroke;
import java.awt.TexturePaint;
import java.awt.geom.Ellipse2D;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;

public class BQCardGenerator {
  static final double SCALE = 0.15;
  static final int WIDTH = (int) (825 * SCALE);
  static final int HEIGHT = (int) (1125 * SCALE);

  public static void main(String[] args) {
    if (args.length != 1) {
      throw new IllegalArgumentException(
          "Requires exactly one argument, the base path of result.");
    }

    //colour, number, shape
    int width = (int) (825 * SCALE);
    int height = (int) (1125 * SCALE);
    int i = 0;
    for (int colour = 0; colour < 4; colour++) {
      for (int number = 0; number < 4; number++) {
        for (int shape = 0; shape < 4; shape++) {
          File imageFile = new File(args[0] + "_" + i + "_small.png");

          BufferedImage bufferedImage = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
          Graphics2D graphics = bufferedImage.createGraphics();
          
          graphics.setBackground(new Color(0xEDEDED));
          graphics.clearRect(0, 0, width, height);

          graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

          int bonusLeft = (int) (60 * SCALE);
          int bonusTop = (int) (81 * SCALE);
          drawCard(graphics, -bonusLeft, -bonusTop, width + 2*bonusLeft, height+2*bonusTop, colour, number, shape);

          try {
            ImageIO.write(bufferedImage, "PNG", imageFile);
          } catch (Exception e) {
            throw new RuntimeException(e);
          }

          ++i;
        }
      }
    }
  }

  private static void drawCard(Graphics2D graphics, int xBase,
      int yBase, int width, int height, int colour, int number,
      int shape) {
    // draw card
    graphics.setColor(new Color(0xFFFFFF));
    graphics.fillRoundRect(0, 0, WIDTH, HEIGHT, 20, 20);

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
    int half_shape_width = (int) (118 * SCALE);
    int shape_width = (int) (236 * SCALE);
    for (int i = 0; i < number + 1; i++) {
      if (shape == 0) {
        shapes.add(new Ellipse2D.Double(xs[i] - half_shape_width, ys[i] - half_shape_width, shape_width, shape_width));  
      } else if (shape == 1) {
        shapes.add(new Rectangle(xs[i] - half_shape_width, ys[i] - half_shape_width, shape_width, shape_width));
      } else if (shape == 2) {
        shapes.add(new Triangle(xs[i] - half_shape_width, ys[i] - half_shape_width, shape_width, shape_width).getShape());
      } else {
        shapes.add(new Diamond(xs[i] - half_shape_width, ys[i] - half_shape_width, shape_width, shape_width).getShape());
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
