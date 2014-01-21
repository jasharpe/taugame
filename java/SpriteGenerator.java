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

public class SpriteGenerator {
  public static void main(String[] args) {
    if (args.length != 3) {
      throw new IllegalArgumentException(
          "Requires exactly three arguments, a file name of result; LARGE for large cards, or SMALL for small cards; and RETINA for 2x (retina), or NOTRETINA for non-retina.");
    }

    File imageFile = new File(args[0]);
    boolean large = args[1].equals("LARGE");
    boolean retina = args[2].equals("RETINA");

    int width = 80;
    int height = 120;
    if (!large) {
      width = 40;
      height = 60;
    }
    
    if (retina) {
      width *= 2;
      height *= 2;
    }
    int totalWidth = width * 81;
    int totalHeight = height;

    BufferedImage bufferedImage = new BufferedImage(totalWidth, totalHeight, BufferedImage.TYPE_INT_ARGB);
    Graphics2D graphics = bufferedImage.createGraphics();

    graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

    //colour, number, fill, shape
    for (int colour = 0; colour < 3; colour++) {
      for (int number = 0; number < 3; number++) {
        for (int fill = 0; fill < 3; fill++) {
          for (int shape = 0; shape < 3; shape++) {
            int xBase = (colour + 3 * number + 9 * fill + 27 * shape) * width;
            int yBase = 0;
            drawCard(graphics, large, retina, xBase, yBase, width, height, colour, number, fill, shape);
          }
        }
      }
    }

    try {
      ImageIO.write(bufferedImage, "PNG", imageFile);
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
  }

  private static void drawCard(Graphics2D graphics, boolean large, boolean retina, int xBase,
      int yBase, int width, int height, int colour, int number,
      int fill, int shape) {
    boolean offset = (large && number != 2 & shape != 0);
    boolean circle_offset = (large && number != 2 & shape == 0) || (!large && number == 1);

    // get shape positions
    int[] xs;
    int[] ys;
    if (number == 0) {
      xs = new int[] { xBase + width / 2 };
      ys = new int[] { yBase + height / 2 };
    } else if (number == 1) {
      xs = new int[] {
        xBase + width / 2,
              xBase + width / 2 };
      ys = new int[] {
        yBase + height - height / 3,
              yBase + height / 3 };
      if (!large) {
        ys[1] += 1;
        ys[0] -= 1;
        if (retina) {
          ys[1] += 1;
          ys[0] -= 1;
        }
      }
    } else {
      xs = new int[] {
        xBase + width / 3,
              xBase + width / 2,
              xBase + width - width / 3 };
      ys = new int[] {
        yBase + height / 2 + width / 6,
              yBase + height / 2 - width / 6,
              yBase + height / 2 + width / 6 };
      if (!large) {
        ys[1] -= 1;
        if (retina) {
          ys[1] -= 1;
        }
      }
    }

    List<Shape> shapes = new ArrayList<Shape>();
    int number1 = 10;
    int number2 = 20;
    if (!large) {
      number1 = 5;
      number2 = 10;
    }   
    if (retina) {
      number1 *= 2;
      number2 *= 2;
    }

    for (int i = 0; i < number + 1; i++) {
      if (shape == 0) {
        shapes.add(new Ellipse2D.Double(xs[i] - number1, ys[i] - number1, number2, number2));  
      } else if (shape == 1) {
        shapes.add(new Rectangle(xs[i] - number1, ys[i] - number1, number2, number2));
      } else {
        shapes.add(new Triangle(xs[i] - number1, ys[i] - number1, number2, number2).getShape());
      }
    }

    Color color;
    if (colour == 0) {
      color = Color.RED;
    } else if (colour == 1) {
      color = Color.GREEN;
    } else {
      color = Color.BLUE;
    }

    TexturePaint texture = null;
    if (fill == 1) {
      if (retina) {
        BufferedImage textureImage = new BufferedImage(1, 4, BufferedImage.TYPE_INT_ARGB);
        if (circle_offset) {
          textureImage.setRGB(0, 0, color.getRGB());
          textureImage.setRGB(0, 3, color.getRGB());
        } else if (offset) {
          textureImage.setRGB(0, 1, color.getRGB());
          textureImage.setRGB(0, 2, color.getRGB());
        } else {
          textureImage.setRGB(0, 2, color.getRGB());
          textureImage.setRGB(0, 3, color.getRGB());
        }
        texture = new TexturePaint(textureImage, new Rectangle(0, 1, 1, 4));
      } else {
        BufferedImage textureImage = new BufferedImage(1, 2, BufferedImage.TYPE_INT_ARGB);
        textureImage.setRGB(0, 1, color.getRGB());
        texture = new TexturePaint(textureImage, new Rectangle(0, 1, 1, 2));
      }
      graphics.setPaint(texture);
    } else {
      graphics.setPaint(color);
    }

    for (Shape aShape : shapes) {
      if (fill == 0) {
        graphics.draw(aShape);
      } else if (fill == 1) {
        graphics.fill(aShape);
        /*graphics.setPaint(color);
          graphics.draw(aShape);
          graphics.setPaint(texture);*/
      } else {
        graphics.fill(aShape);
      }
    }
  }
}
