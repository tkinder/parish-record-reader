"""OpenCV preprocessing for photos of handwritten parish records.

Pipeline: decode -> page crop -> deskew -> resize -> CLAHE contrast.
Color is preserved by default because ink/stain discrimination helps
vision models; pass ``keep_color=False`` for a grayscale result.
Every step is conservative: a missed enhancement is better than
cropping away handwriting. Use ``benchmark_variants`` to compare raw
vs. preprocessed images per model before fixing a pipeline.
"""
from __future__ import annotations

import cv2
import numpy as np

# Fireworks and most vision APIs reject very large images; cap the
# longest side so full-resolution phone photos stay within limits.
MAX_IMAGE_DIMENSION = 2048


def _content_crop(gray: np.ndarray, padding: int = 24) -> np.ndarray:
    """Crop large near-white borders, keeping a safety margin."""
    _, mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(mask)
    if coords is None:
        return gray
    x, y, w, h = cv2.boundingRect(coords)
    height, width = gray.shape
    x0 = max(0, x - padding)
    y0 = max(0, y - padding)
    x1 = min(width, x + w + padding)
    y1 = min(height, y + h + padding)
    if x0 > 0.02 * width or y0 > 0.02 * height or x1 < 0.98 * width or y1 < 0.98 * height:
        return gray[y0:y1, x0:x1]
    return gray


def _page_crop(image: np.ndarray, padding: int = 24) -> np.ndarray:
    """Crop to the page when a darker table/background surrounds it.

    Finds the largest bright contour (the page) in HSV value space.
    Falls back to the near-white content crop when no plausible page
    contour exists, so a tight photo is never harmed.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # The page is usually the brighter region; if Otsu inverted it
    # (dark page), keep the mask whose border is mostly background.
    border_mean = float(
        np.mean(
            np.concatenate(
                [mask[0, :], mask[-1, :], mask[:, 0], mask[:, -1]]
            )
        )
    )
    if border_mean > 127:
        mask = cv2.bitwise_not(mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        area_ratio = cv2.contourArea(largest) / float(height * width)
        if 0.25 < area_ratio < 0.98:
            x, y, w, h = cv2.boundingRect(largest)
            x0 = max(0, x - padding)
            y0 = max(0, y - padding)
            x1 = min(width, x + w + padding)
            y1 = min(height, y + h + padding)
            if x1 - x0 > 50 and y1 - y0 > 50:
                return image[y0:y1, x0:x1]
    cropped_gray = _content_crop(gray, padding=padding)
    if cropped_gray.shape != gray.shape:
        # Map the grayscale crop box back onto the color image by
        # recomputing on luminance coordinates: re-derive the box.
        _, mask2 = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
        coords = cv2.findNonZero(mask2)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            x0 = max(0, x - padding)
            y0 = max(0, y - padding)
            x1 = min(width, x + w + padding)
            y1 = min(height, y + h + padding)
            return image[y0:y1, x0:x1]
    return image


def _deskew_angle(gray: np.ndarray) -> float:
    """Estimate page skew in degrees from text-line orientation.

    Uses Hough lines over edges restricted to the page interior so a
    table edge or stain cannot dominate the estimate the way a
    whole-image dark-pixel rectangle could. Falls back to the
    min-area-rectangle estimate when too few lines are found.
    """
    height, width = gray.shape
    # Interior crop (drop outer 5%) ignores page/table borders.
    y0, y1 = int(0.05 * height), int(0.95 * height)
    x0, x1 = int(0.05 * width), int(0.95 * width)
    interior = gray[y0:y1, x0:x1]
    edges = cv2.Canny(interior, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 720, threshold=120, minLineLength=80, maxLineGap=15
    )
    angles: list[float] = []
    if lines is not None:
        for x_a, y_a, x_b, y_b in lines.reshape(-1, 4):
            if x_a == x_b:
                continue
            angle = float(np.degrees(np.arctan2(y_b - y_a, x_b - x_a)))
            # Keep near-horizontal lines only.
            if abs(angle) <= 20:
                angles.append(angle)
    if len(angles) >= 8:
        angle = float(np.median(angles))
        return angle if abs(angle) <= 15.0 else 0.0

    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(mask)
    if coords is None or len(coords) < 100:
        return 0.0
    rect = cv2.minAreaRect(coords)
    angle = float(rect[-1])
    if angle < -45.0:
        angle = 90.0 + angle
    if abs(angle) > 15.0:
        return 0.0
    return angle


def _resize_to_limit(image: np.ndarray, max_dimension: int) -> np.ndarray:
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_dimension:
        return image
    scale = max_dimension / float(longest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def _enhance(image: np.ndarray, *, keep_color: bool) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    if not keep_color:
        gray = (
            image
            if image.ndim == 2
            else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        )
        return clahe.apply(gray)
    if image.ndim == 2:
        return clahe.apply(image)
    # Enhance luminance only so ink hue (faded ink vs. stain) survives.
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a_chan, b_chan = cv2.split(lab)
    enhanced = clahe.apply(lightness)
    return cv2.cvtColor(cv2.merge((enhanced, a_chan, b_chan)), cv2.COLOR_LAB2BGR)


def preprocess_image(
    image_bytes: bytes,
    *,
    keep_color: bool = True,
    max_dimension: int = MAX_IMAGE_DIMENSION,
) -> bytes:
    """Enhance a record photo and return PNG bytes."""
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode the uploaded image.")

    image = _page_crop(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    angle = _deskew_angle(gray)
    if abs(angle) > 0.2:
        height, width = image.shape[:2]
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
        image = cv2.warpAffine(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    image = _resize_to_limit(image, max_dimension)
    image = _enhance(image, keep_color=keep_color)

    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode the preprocessed image.")
    return encoded.tobytes()


def benchmark_variants(image_bytes: bytes) -> dict[str, bytes]:
    """Return {'raw_png', 'preprocessed_png'} for per-model A/B scoring.

    Benchmark raw vs. preprocessed with each candidate model (CER/WER)
    before locking the preprocessing pipeline for the demo.
    """
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode the uploaded image.")
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode the raw image.")
    return {
        "raw_png": encoded.tobytes(),
        "preprocessed_png": preprocess_image(image_bytes),
    }
