import os
import math
from PIL import Image, ImageDraw, ImageFilter

def generate_arc_reactor_icon(size: int, output_path: str):
    # Create high-res canvas with supersampling for crisp anti-aliasing
    scale = 2
    canvas_size = size * scale
    center = canvas_size // 2
    
    img = Image.new("RGBA", (canvas_size, canvas_size), (5, 11, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Outer subtle glow
    r_glow = int(center * 0.88)
    for i in range(15):
        alpha = int(25 * (1 - i / 15))
        r = r_glow + i * scale * 2
        draw.ellipse([center - r, center - r, center + r, center + r], outline=(0, 240, 255, alpha), width=scale * 2)
        
    # Outer ring
    r_outer = int(center * 0.82)
    draw.ellipse([center - r_outer, center - r_outer, center + r_outer, center + r_outer], outline=(0, 240, 255, 230), width=int(8 * scale))
    
    # Coils (10 reactor coil segments)
    num_coils = 10
    r_coil_inner = int(center * 0.58)
    r_coil_outer = int(center * 0.78)
    for i in range(num_coils):
        angle = (2 * math.pi / num_coils) * i
        # Segment bars
        x1 = center + r_coil_inner * math.cos(angle)
        y1 = center + r_coil_inner * math.sin(angle)
        x2 = center + r_coil_outer * math.cos(angle)
        y2 = center + r_coil_outer * math.sin(angle)
        draw.line([(x1, y1), (x2, y2)], fill=(255, 183, 3, 220), width=int(10 * scale))
        draw.line([(x1, y1), (x2, y2)], fill=(0, 240, 255, 255), width=int(4 * scale))
        
    # Middle ring
    r_mid = int(center * 0.55)
    draw.ellipse([center - r_mid, center - r_mid, center + r_mid, center + r_mid], outline=(0, 240, 255, 255), width=int(6 * scale))
    
    # Inner energy ring
    r_inner = int(center * 0.38)
    draw.ellipse([center - r_inner, center - r_inner, center + r_inner, center + r_inner], outline=(0, 240, 255, 200), fill=(10, 35, 60, 255), width=int(4 * scale))
    
    # Inner triangle core
    tri_r = int(center * 0.28)
    points = []
    for i in range(3):
        a = -math.pi / 2 + (2 * math.pi / 3) * i
        points.append((center + tri_r * math.cos(a), center + tri_r * math.sin(a)))
    draw.polygon(points, outline=(0, 240, 255, 255), width=int(5 * scale))
    
    # Core glowing center
    core_r = int(center * 0.14)
    draw.ellipse([center - core_r, center - core_r, center + core_r, center + core_r], fill=(255, 255, 255, 255))
    
    # Downscale with high quality Lanczos filter
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_img.save(output_path, "PNG")
    print(f"Generated {output_path} ({size}x{size})")

if __name__ == "__main__":
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    generate_arc_reactor_icon(192, os.path.join(static_dir, "icon-192.png"))
    generate_arc_reactor_icon(512, os.path.join(static_dir, "icon-512.png"))
    generate_arc_reactor_icon(180, os.path.join(static_dir, "apple-touch-icon.png"))
