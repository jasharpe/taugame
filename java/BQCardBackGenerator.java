import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Rectangle;
import java.awt.RenderingHints;
import java.awt.Shape;
import java.awt.TexturePaint;
import java.awt.*;
import java.awt.geom.Ellipse2D;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;

public class BQCardBackGenerator {
  private static final int WIDTH = 825;
  private static final int HEIGHT = 1125;
  private static final double ANGLE = 0.2;

  public static void main(String[] args) {
    for (int color = 0; color < 4; color++) {
      File imageFile = new File(
          "rules_template_" + color + ".png");

      BufferedImage bufferedImage = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
      Graphics2D graphics = bufferedImage.createGraphics();

      graphics.setBackground(new Color(0xEDEDED));
      graphics.clearRect(0, 0, WIDTH, HEIGHT);

      graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

      drawRules(graphics, color);

      try {
        ImageIO.write(bufferedImage, "PNG", imageFile);
      } catch (Exception e) {
        throw new RuntimeException(e);
      }
    }

    if (true) return;

    // We like 0 2 3 1.
    for (int shape1 = 0; shape1 < 4; shape1++) {
      for (int shape2 = 0; shape2 < 4; shape2++) {
        if (shape2 == shape1) continue;
        for (int shape3 = 0; shape3 < 4; shape3++) {
          if (shape3 == shape2 || shape3 == shape1) continue;
          for (int shape4 = 0; shape4 < 4; shape4++) {
            if (shape4 == shape3 || shape4 == shape2 || shape4 == shape1) continue;

            File imageFile = new File(
                "bqtau_backs/bqtau_back_" + shape1 + "_" + shape2 + "_" + shape3 + "_" + shape4 + ".png");

            BufferedImage bufferedImage = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
            Graphics2D graphics = bufferedImage.createGraphics();

            graphics.setBackground(new Color(0xEDEDED));
            graphics.clearRect(0, 0, WIDTH, HEIGHT);

            graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            drawCard(graphics, shape1, shape2, shape3, shape4);

            try {
              ImageIO.write(bufferedImage, "PNG", imageFile);
            } catch (Exception e) {
              throw new RuntimeException(e);
            }
          }
        }
      }
    }
  }

  private static void drawRules(Graphics2D graphics, int colour) {
    int line_width = 10;
    int border_offset = 50;
    int border_radius = 20;

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
    /*int left_offset = border_offset;
    graphics.fillRect(left_offset, 150, WIDTH * 3 / 4 - left_offset, 100);*/
    int offset = border_offset;
    graphics.fillRect(offset, offset, WIDTH - 2 * offset, 100);

    graphics.setPaint(new Color(0x777777));
    graphics.setStroke(new BasicStroke(line_width));
    graphics.drawRect(border_offset, border_offset, WIDTH - 2 * border_offset, HEIGHT - 2 * border_offset);

  }

  private static void drawCard(Graphics2D graphics, int shape1, int shape2, int shape3, int shape4) {
    int line_width = 10;
    int border_offset = 50;
    int border_radius = 20;
    graphics.setPaint(new Color(0x777777));

    //graphics.setStroke(new BasicStroke(10));
    // Top line.
    //graphics.drawLine(border_offset, border_offset, WIDTH - border_offset, border_offset);
    /*graphics.fillRoundRect(
        border_offset, border_offset,
        WIDTH - 2 * border_offset, HEIGHT - 2 * border_offset,
        border_radius + 3, border_radius + 3);
    graphics.setPaint(new Color(0xEDEDED));
    graphics.fillRoundRect(
        border_offset + line_width, border_offset + line_width,
        WIDTH - 2 * border_offset - 2 * line_width, HEIGHT - 2 * border_offset - 2 * line_width,
        border_radius, border_radius);*/

    graphics.setStroke(new BasicStroke(10));
    /*int arc_offset = 5;
    graphics.drawLine(
        border_offset + arc_offset, border_offset + arc_offset,
        WIDTH - border_offset - arc_offset, border_offset + arc_offset);
    graphics.drawLine(
        WIDTH - border_offset - arc_offset, border_offset + arc_offset,
        WIDTH - border_offset - arc_offset, HEIGHT - border_offset - arc_offset);*/
    graphics.drawRect(border_offset, border_offset, WIDTH - 2 * border_offset, HEIGHT - 2 * border_offset);

    graphics.setPaint(new Color(0x555555));
    //graphics.setStroke(new BasicStroke(10));
    // Top line.
    //graphics.drawLine(border_offset, border_offset, WIDTH - border_offset, border_offset);
    //graphics.drawRoundRect(border_offset, border_offset, WIDTH - 2 * border_offset, HEIGHT - 2 * border_offset, 10, 10);

    int half_width = WIDTH / 2;
    int half_height = HEIGHT / 2;
    int offset = 120; // 130 for not rotated.
    drawShape(graphics, half_width - offset, half_height - offset, shape1, 0);
    drawShape(graphics, half_width - offset, half_height + offset, shape2, 1);
    drawShape(graphics, half_width + offset, half_height - offset, shape3, 3);
    drawShape(graphics, half_width + offset, half_height + offset, shape4, 2);
  }

  private static int rotateX(int x, int y) {
    return (int) (Math.cos(ANGLE) * (x - WIDTH / 2) - Math.sin(ANGLE) * (y - HEIGHT / 2) + (double) WIDTH / 2);
  }

  private static int rotateY(int x, int y) {
    return (int) (Math.sin(ANGLE) * (x - WIDTH / 2) + Math.cos(ANGLE) * (y - HEIGHT / 2) + (double) HEIGHT / 2);
  }

  private static void drawShape(Graphics2D graphics, int x, int y, int shape, int colour) {
    int rot_x = rotateX(x, y);
    int rot_y = rotateY(x, y);

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

    Shape aShape;
    int shape_width = 200;
    int half_shape_width = shape_width / 2;
    if (shape == 0) {
      aShape = new Ellipse2D.Double(rot_x - half_shape_width, rot_y - half_shape_width, shape_width, shape_width);  
    } else if (shape == 1) {
      aShape = new Rectangle(rot_x - half_shape_width, rot_y - half_shape_width, shape_width, shape_width);
    } else if (shape == 2) {
      aShape = new Triangle(rot_x - half_shape_width, rot_y - half_shape_width, shape_width, shape_width).getShape();
    } else {
      aShape = new Diamond(rot_x - half_shape_width, rot_y - half_shape_width, shape_width, shape_width).getShape();
    }
    
    graphics.setPaint(color);
    graphics.fill(aShape);
  }
}
