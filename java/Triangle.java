import java.awt.Polygon;
import java.awt.Shape;

/**
 * Represents an equilateral triangle.
 */
public class Triangle {
  private final int x;
  private final int y;
  private final int width;
  private final int height;

  public Triangle(int x, int y, int width, int height) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
  }

  private int[] getXCoordinates() {
    return new int[] { x, x + width / 2, x + width };
  }

  private int[] getYCoordinates() {
    return new int[] { y + height, y, y + height };
  }

  public Shape getShape() {
    return new Polygon(getXCoordinates(), getYCoordinates(), 3);
  }
}
