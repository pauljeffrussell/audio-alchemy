import os
from PIL import Image, ImageDraw, ImageOps

def round_corners(image_path, output_path, radius):
    # Open the image
    image = Image.open(image_path).convert("RGBA")

    # Create a mask for rounded corners
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)

    # Draw a rounded rectangle
    draw.rounded_rectangle(
        [(0, 0), image.size], radius=radius, fill=255
    )

    # Apply the mask to the image
    rounded_image = ImageOps.fit(image, mask.size)
    rounded_image.putalpha(mask)

    # Save the result
    rounded_image.save(output_path, format="PNG")


def process_directory(input_dir, output_dir, radius):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Iterate over all the files in the input directory
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            print(f"Processing {filename}...")

            # Round the corners of the image and save it to the output directory
            round_corners(input_path, output_path, radius)

    print("Processing complete.")

import os
from PIL import Image, ImageDraw, ImageOps

def get_image_dpi(image_path):
    # Open the image and get its DPI
    image = Image.open(image_path)
    dpi = image.info.get('dpi', (72, 72))  # Default to 72 DPI if not available
    return dpi[0]  # Usually DPI is the same for both width and height

def round_corners(image_path, output_path, radius_in_inches):
    # Open the image
    image = Image.open(image_path).convert("RGBA")
    
    # Get the DPI of the image
    dpi = get_image_dpi(image_path)
    
    # Calculate the radius in pixels
    radius_in_pixels = int(radius_in_inches * dpi)

    # Create a mask for rounded corners
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)

    # Draw a rounded rectangle with the calculated radius
    draw.rounded_rectangle(
        [(0, 0), image.size], radius=radius_in_pixels, fill=255
    )

    # Apply the mask to the image
    rounded_image = ImageOps.fit(image, mask.size)
    rounded_image.putalpha(mask)

    # Save the result
    rounded_image.save(output_path, format="PNG")


def process_directory(input_dir, output_dir, radius_in_inches):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Iterate over all the files in the input directory
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            print(f"Processing {filename}...")

            # Round the corners of the image and save it to the output directory
            round_corners(input_path, output_path, radius_in_inches)

    print("Processing complete.")


# Example usage
input_directory = './cards/2025-06/60/'
output_directory = './cards/2025-06a-round/'
corner_radius_in_inches = 0.125  # Set the corner radius in inches

process_directory(input_directory, output_directory, corner_radius_in_inches)

