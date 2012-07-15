import java.awt.Polygon;
import java.awt.Shape;

/**
 * Represents a diamond shape.
 */
public class Diamond {
  private final int x;
  private final int y;
  private final int width;
  private final int height;

  public Diamond(int x, int y, int width, int height) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
  }

  private int[] getXCoordinates() {
    return new int[] { x, x + width / 2, x + width, x + width / 2 };
  }

  private int[] getYCoordinates() {
    return new int[] { y + height / 2, y, y + height / 2, y + height };
  }

  public Shape getShape() {
    return new Polygon(getXCoordinates(), getYCoordinates(), 4);
  }
}
