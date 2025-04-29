from flask import Flask, request, send_file
from rembg import remove
from PIL import Image
import os
import cv2
from io import BytesIO

app = Flask(__name__)

# --- Mockup constants ---
DPI = 300  # Dots per inch for margin calculation
MOCKUPS = {
    "vertical": [
        "static/mockups/mockup_vertical_small.jpeg",
        "static/mockups/mockup_vertical_large.jpeg"
    ],
    "horizontal": [
        "static/mockups/mockup_horizontal_large.png"
    ]
}

# --- Mockup functions ---
def detect_frame_area(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError(f"No contours found in image {image_path}")

    largest_contour = max(contours, key=cv2.contourArea)
    return cv2.boundingRect(largest_contour)  # x, y, w, h

def find_best_mockup(orientation, art_width_in, art_height_in):
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

def overlay_in_frame(mockup_path, frame_coords, foreground_image, margin_inch=0):
    """Overlay the foreground PIL Image inside the detected frame area."""
    bg = Image.open(mockup_path).convert("RGBA")
    fg = foreground_image.convert("RGBA")

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
    return bg

# --- Flask route ---
@app.route('/', methods=['POST'])
def process_art():
    if 'file' not in request.files:
        return 'No file uploaded', 400

    file = request.files['file']
    if file.filename == '':
        return 'No file selected', 400

    if file:
        input_image = Image.open(file.stream)

        # 1. Remove background
        transparent_image = remove(input_image, post_process_mask=True)

        # 2. Detect orientation
        width_px, height_px = transparent_image.size
        ppi = 96  # standard screen PPI
        width_in = width_px / ppi
        height_in = height_px / ppi

        orientation = "vertical" if height_in >= width_in else "horizontal"

        # 3. Find the best mockup
        best_mockup = find_best_mockup(orientation, width_in, height_in)

        # 4. Overlay
        final_image = overlay_in_frame(best_mockup["mockup_path"], best_mockup["frame_coords"], transparent_image, margin_inch=0.01)

        # 5. Return the final image
        img_io = BytesIO()
        final_image.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png', as_attachment=True, download_name='final_artwork.png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5100)