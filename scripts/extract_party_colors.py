#!/usr/bin/env python3
"""
Extract dominant colors from party icon images and update party-data.json
This script runs ONCE to map party icons to their brand colors.
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

# Configuration
PARTY_DATA_FILE = "docs/data/party-data.json"
PARTY_ICONS_DIR = "docs/img"
OUTPUT_FILE = "docs/data/party-data.json"  # Overwrite the same file


def is_too_light_or_dark_or_gray(hex_color):
    """
    Check if a color is too close to white, black, or gray.
    Returns True if the color should be excluded.
    """
    # Remove # if present
    hex_color = hex_color.lstrip("#")

    # Convert to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # Calculate perceived brightness (human eye weights colors differently)
    # Using the formula: 0.299*R + 0.587*G + 0.114*B
    brightness = 0.299 * r + 0.587 * g + 0.114 * b

    # Also check saturation (colorfulness) to avoid grays
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    saturation = (max_val - min_val) / max_val if max_val > 0 else 0

    # Exclude colors that are:
    # - Too dark (< 60) or too light (> 235) - stricter threshold
    # - Too gray/unsaturated (< 0.15) - avoids white, gray, black, and washed-out colors
    return brightness < 60 or brightness > 235 or saturation < 0.15


def extract_color_from_image(image_path):
    """
    Extract the dominant color from an image file.
    Returns hex color string or None if extraction fails.
    """
    try:
        # Try to use PIL/Pillow for better color extraction
        from PIL import Image

        img = Image.open(image_path)

        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize to small size for faster processing
        # This also helps get the "main" color by averaging
        img_small = img.resize((50, 50), Image.Resampling.LANCZOS)

        # Get all pixels
        pixels = list(img_small.getdata())

        # Filter out colors that are too light or dark (white/black backgrounds)
        filtered_pixels = []
        for r, g, b in pixels:
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            if 50 <= brightness <= 245:  # Exclude very dark and very light
                filtered_pixels.append((r, g, b))

        # If no valid pixels found, use all pixels
        if not filtered_pixels:
            filtered_pixels = pixels

        # Count color occurrences (with some tolerance for similar colors)
        # Round RGB values to nearest 10 to group similar colors
        rounded_pixels = []
        for r, g, b in filtered_pixels:
            r = round(r / 10) * 10
            g = round(g / 10) * 10
            b = round(b / 10) * 10
            rounded_pixels.append((r, g, b))

        color_counter = Counter(rounded_pixels)

        # Get the most common color
        if color_counter:
            dominant_rgb = color_counter.most_common(1)[0][0]
            r, g, b = dominant_rgb

            # Clamp values to valid range
            r = max(0, min(255, int(r)))
            g = max(0, min(255, int(g)))
            b = max(0, min(255, int(b)))

            # Convert to hex
            hex_color = f"#{r:02X}{g:02X}{b:02X}"

            # Check if the result is too light or dark or gray
            if is_too_light_or_dark_or_gray(hex_color):
                # Try the second most common color
                if len(color_counter) > 1:
                    dominant_rgb = color_counter.most_common(2)[1][0]
                    r, g, b = dominant_rgb
                    r = max(0, min(255, int(r)))
                    g = max(0, min(255, int(g)))
                    b = max(0, min(255, int(b)))
                    hex_color = f"#{r:02X}{g:02X}{b:02X}"

                    # If still too light/dark/gray, return None
                    if is_too_light_or_dark_or_gray(hex_color):
                        return None

                return None

            return hex_color

        return None

    except ImportError:
        print("Warning: PIL/Pillow not installed. Install with: pip install Pillow")
        print("Falling back to basic color extraction...")
        return None
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None


def main():
    print("=" * 60)
    print("Party Color Extraction Tool")
    print("=" * 60)

    # Load existing party data
    if not os.path.exists(PARTY_DATA_FILE):
        print(f"Error: Party data file not found: {PARTY_DATA_FILE}")
        sys.exit(1)

    with open(PARTY_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    parties = data.get("parties", [])
    print(f"\nFound {len(parties)} parties in data file")

    # Count for stats
    updated_count = 0
    skipped_count = 0
    error_count = 0

    # Process each party
    for party in parties:
        party_code = party.get("code")
        party_name = party.get("name", "Unknown")

        if not party_code:
            continue

        # Look for the icon file
        # Try .webp first, then .png, then .jpg
        icon_filename = f"{party_code}.webp"
        icon_path = os.path.join(PARTY_ICONS_DIR, icon_filename)

        if not os.path.exists(icon_path):
            # Try PNG
            icon_filename = f"{party_code}.png"
            icon_path = os.path.join(PARTY_ICONS_DIR, icon_filename)

        if not os.path.exists(icon_path):
            # Try JPG
            icon_filename = f"{party_code}.jpg"
            icon_path = os.path.join(PARTY_ICONS_DIR, icon_filename)

        if not os.path.exists(icon_path):
            print(f"  ⚠️  {party_code} ({party_name}): No icon found")
            skipped_count += 1
            continue

        # Extract color
        extracted_color = extract_color_from_image(icon_path)

        if extracted_color:
            old_color = party.get("colorPrimary", "N/A")
            party["colorPrimary"] = extracted_color
            print(f"  ✓ {party_code} ({party_name}): {old_color} → {extracted_color}")
            updated_count += 1
        else:
            print(
                f"  ⚠️  {party_code} ({party_name}): Could not extract color (too light/dark or error)"
            )
            error_count += 1

    # Save updated data
    print(f"\n{'=' * 60}")
    print("Summary:")
    print(f"  Updated: {updated_count} parties")
    print(f"  Skipped: {skipped_count} parties (no icon)")
    print(f"  Errors:  {error_count} parties")
    print(f"{'=' * 60}")

    # Save to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Updated party data saved to: {OUTPUT_FILE}")
    print("\nYou can now commit this change and merge it to master.")


if __name__ == "__main__":
    main()
