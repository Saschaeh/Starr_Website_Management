"""Image processing utilities — resize, crop, B&W detection, overlay."""

import re

import numpy as np
from PIL import Image


def resize_and_crop(img, target_width, target_height):
    """Resize and center-crop image to target dimensions."""
    img_width, img_height = img.size
    target_ratio = target_width / target_height
    img_ratio = img_width / img_height

    if img_ratio > target_ratio:
        new_height = img_height
        new_width = int(img_height * target_ratio)
    else:
        new_width = img_width
        new_height = int(img_width / target_ratio)

    left = (img_width - new_width) // 2
    top = (img_height - new_height) // 2
    right = left + new_width
    bottom = top + new_height

    img = img.crop((left, top, right, bottom))
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return img


def fix_exif_orientation(img):
    """Apply EXIF orientation rotation if present."""
    try:
        exif = img._getexif()
        if exif and 274 in exif:
            orientation = exif[274]
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(-90, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        pass
    return img


def make_image_filename(restaurant_slug, field_name, width, height, ext, alt_text=''):
    """Generate WordPress-style SEO filename."""
    if alt_text and alt_text.strip():
        slug = re.sub(r'[^a-z0-9\s]', '', alt_text.strip().lower())
        words = slug.split()
        words = [w for w in words if w not in
                 ('a', 'an', 'the', 'of', 'in', 'on', 'at', 'to', 'and', 'with', 'for', 'is', 'by')]
        slug = '_'.join(words[:6])
        return f"{restaurant_slug}_{field_name}_{slug}_{width}x{height}.{ext}"
    return f"{restaurant_slug}_{field_name}_{width}x{height}.{ext}"


def is_black_and_white(img, threshold=0.1):
    """Check if image is predominantly black and white."""
    arr = np.array(img.convert('RGB'), dtype=np.int16)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    limit = threshold * 255
    bw_mask = (np.abs(r - g) < limit) & (np.abs(g - b) < limit)
    return bw_mask.mean() > 0.8


def apply_black_overlay(img, opacity_percent):
    """Apply a semi-transparent black overlay to image."""
    img_rgba = img.convert('RGBA')
    overlay = Image.new('RGBA', img_rgba.size, (0, 0, 0, int(255 * opacity_percent / 100)))
    return Image.alpha_composite(img_rgba, overlay).convert('RGB')
