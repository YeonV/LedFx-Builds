"""
ANSI Art Album Art Renderer
Renders album artwork as ANSI colored text art in the terminal
"""

import os
from PIL import Image

def rgb_to_ansi(r, g, b):
    """Convert RGB values to ANSI 256-color code"""
    # Use 216-color cube (16-231)
    # Each component has 6 levels: 0, 95, 135, 175, 215, 255
    levels = [0, 95, 135, 175, 215, 255]
    
    def closest_level(value):
        return min(range(6), key=lambda i: abs(levels[i] - value))
    
    r_idx = closest_level(r)
    g_idx = closest_level(g)
    b_idx = closest_level(b)
    
    color_code = 16 + 36 * r_idx + 6 * g_idx + b_idx
    return color_code

def render_image_ansi(image_path, width=80):
    """Render an image as ANSI colored blocks in terminal"""
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    try:
        # Open and resize image
        img = Image.open(image_path)
        
        # Calculate height to maintain aspect ratio (characters are ~2x taller than wide)
        aspect_ratio = img.height / img.width
        height = int(width * aspect_ratio * 0.5)  # 0.5 to account for character aspect ratio
        
        # Resize image
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        img = img.convert('RGB')
        
        # Get pixel data
        pixels = img.load()
        
        print(f"\n{'='*width}")
        print(f"Album Art: {os.path.basename(image_path)}")
        print(f"{'='*width}\n")
        
        # Render each row
        for y in range(height):
            line = ""
            for x in range(width):
                r, g, b = pixels[x, y]
                color_code = rgb_to_ansi(r, g, b)
                # Use block character with background color
                line += f"\033[48;5;{color_code}m \033[0m"
            print(line)
        
        print(f"\n{'='*width}\n")
        
    except Exception as e:
        print(f"Error rendering image: {e}")
        import traceback
        traceback.print_exc()

def render_image_ascii(image_path, width=100):
    """Render an image as ASCII art (grayscale)"""
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    try:
        # ASCII characters from dark to light
        ascii_chars = " .:-=+*#%@"
        
        # Open and resize image
        img = Image.open(image_path)
        
        # Calculate height to maintain aspect ratio
        aspect_ratio = img.height / img.width
        height = int(width * aspect_ratio * 0.5)
        
        # Resize and convert to grayscale
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        img = img.convert('L')  # Grayscale
        
        # Get pixel data
        pixels = img.load()
        
        print(f"\n{'='*width}")
        print(f"Album Art (ASCII): {os.path.basename(image_path)}")
        print(f"{'='*width}\n")
        
        # Render each row
        for y in range(height):
            line = ""
            for x in range(width):
                brightness = pixels[x, y]
                char_idx = int((brightness / 255) * (len(ascii_chars) - 1))
                line += ascii_chars[char_idx]
            print(line)
        
        print(f"\n{'='*width}\n")
        
    except Exception as e:
        print(f"Error rendering ASCII art: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    image_path = r"C:\Users\Blade\AppData\Roaming\.ledfx\assets\current_album_art.jpg"
    
    print("=" * 80)
    print("LedFx Album Art Renderer")
    print("=" * 80)
    print()
    
    # Try ANSI colored version first (better quality)
    print("Rendering ANSI colored version...")
    render_image_ansi(image_path, width=60)
    
    # Uncomment to also show ASCII grayscale version
    # print("\nRendering ASCII grayscale version...")
    # render_image_ascii(image_path, width=100)

if __name__ == "__main__":
    main()
