import argparse
import os
import cv2
from PIL import Image

# Constants
DPI = 300  # Dots per inch

# Mockup list: only filenames, not hardcoded frames
MOCKUPS = {
    "vertical": [
        "mockup_vertical_small.jpeg",
        "mockup_vertical_large.jpeg"
    ],
    "horizontal": [
        "mockup_horizontal_large.png"
    ]
}

def detect_frame_area(image_path):
    """Auto-detect the largest white frame in the mockup using OpenCV."""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Threshold to find white areas
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError(f"No contours found in image {image_path}")

    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)

    return x, y, w, h
def overlay_in_frame(mockup_path, frame_coords, foreground_path, output_path, margin_inch=0):
    """Overlay the foreground inside the detected frame area."""
    bg = Image.open(mockup_path).convert("RGBA")
    fg = Image.open(foreground_path).convert("RGBA")

    x, y, w, h = frame_coords
    margin_px = int(margin_inch * DPI)

    frame_x = x + margin_px
    frame_y = y + margin_px
    frame_w = w - 2 * margin_px
    frame_h = h - 2 * margin_px

    if frame_w <= 0 or frame_h <= 0:
        raise ValueError("Margin too large compared to frame size!")

    fg.thumbnail((frame_w, frame_h), Image.Resampling.LANCZOS)

    fg_w, fg_h = fg.size
    pos_x = frame_x + (frame_w - fg_w) // 2
    pos_y = frame_y + (frame_h - fg_h) // 2

    bg.paste(fg, (pos_x, pos_y), fg)
    bg.save(output_path)

def find_best_mockup(orientation, art_width_in, art_height_in):
    """Choose the mockup whose detected frame aspect ratio is closest to art."""
    candidates = MOCKUPS.get(orientation, [])
    if not candidates:
        raise ValueError(f"No mockups available for orientation '{orientation}'")

    best = None
    smallest_diff = float('inf')

    for mockup_path in candidates:
        x, y, w, h = detect_frame_area(mockup_path)
        frame_ratio = w / h
        art_ratio = art_width_in / art_height_in

        diff = abs(frame_ratio - art_ratio)
        if diff < smallest_diff:
            best = {
                "mockup_path": mockup_path,
                "frame_coords": (x, y, w, h)
            }
            smallest_diff = diff

    if best is None:
        raise ValueError("No suitable mockup found.")

    return best

def main():
    parser = argparse.ArgumentParser(description="Auto-detect frame mockup generator using OpenCV.")
    parser.add_argument("foreground", help="Path to the transparent PNG image")
    parser.add_argument("output", help="Path for the output image")
    args = parser.parse_args()

    # Hardcoded margin
    margin_inch = 0.01

    # Automatically get size in inches from image pixels
    with Image.open(args.foreground) as img:
        width_px, height_px = img.size
        ppi = 96  # adjust if needed
        width_in = width_px / ppi
        height_in = height_px / ppi
        print(f"Detected size: {width_px}x{height_px} pixels → {width_in:.2f}x{height_in:.2f} inches")

    # Automatically detect orientation
    orientation = "vertical" if height_in >= width_in else "horizontal"
    print(f"Detected orientation: {orientation}")

    # Select best mockup
    best_mockup = find_best_mockup(orientation, width_in, height_in)
    frame_x, frame_y, frame_w, frame_h = best_mockup["frame_coords"]
    print(f"Detected frame: x={frame_x}, y={frame_y}, width={frame_w}, height={frame_h}")
    print(f"Selected mockup: {best_mockup['mockup_path']}")

    # Overlay with hardcoded margin
    overlay_in_frame(best_mockup["mockup_path"], best_mockup["frame_coords"], args.foreground, args.output, margin_inch=margin_inch)

if __name__ == "__main__":
    main()