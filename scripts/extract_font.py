import urllib.request
import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

def main():
    font_url = "https://github.com/google/fonts/raw/main/ofl/quicksand/static/Quicksand-Bold.ttf"
    local_font_path = "Quicksand-Bold.ttf"
    
    print(f"Downloading font...")
    try:
        urllib.request.urlretrieve(font_url, local_font_path)
    except Exception:
        font_url = "https://github.com/google/fonts/raw/main/ofl/quicksand/Quicksand%5Bwght%5D.ttf"
        try:
            urllib.request.urlretrieve(font_url, local_font_path)
        except Exception as err:
            print(f"Download failed: {err}")
            sys.exit(1)
            
    try:
        font = TTFont(local_font_path)
    except Exception as e:
        print(f"Failed to parse font: {e}")
        sys.exit(1)
        
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    
    if 'fvar' in font:
        from fontTools.varLib.instancer import instantiateVariableFont
        font = instantiateVariableFont(font, {"wght": 700})
        glyph_set = font.getGlyphSet()
        cmap = font.getBestCmap()
        
    units_per_em = font['head'].unitsPerEm
    hmtx = font['hmtx']
    
    word = "pyyunoheat"
    svg_paths = []
    current_x = 0.0
    
    for char in word:
        glyph_name = cmap.get(ord(char))
        if not glyph_name:
            continue
            
        pen = SVGPathPen(glyph_set)
        glyph = glyph_set[char] if char in glyph_set else glyph_set[glyph_name]
        glyph.draw(pen)
        path_d = pen.getCommands()
        
        advance_width, lsb = hmtx[glyph_name]
        
        if path_d:
            svg_paths.append({
                "char": char,
                "d": path_d,
                "x": current_x,
                "width": advance_width
            })
            
        current_x += advance_width
        
    # Scale factor for full-bleed and large text
    scale_factor = 0.45
    text_start_x = 444.11
    text_baseline_y = 370.0
    
    # Calculate total width of the text
    total_text_width_units = current_x
    total_text_width_px = total_text_width_units * scale_factor
    
    # Calculate viewport width (start offset + text width + right padding)
    right_padding = 60.0
    viewport_width = int(text_start_x + total_text_width_px + right_padding)
    viewport_height = 512
    
    print(f"Text width: {total_text_width_px:.2f}px")
    print(f"Viewport dimensions: {viewport_width}x{viewport_height}")
    
    # Generate the SVG string
    svg_content = []
    svg_content.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{viewport_width}" height="{viewport_height}" viewBox="0 0 {viewport_width} {viewport_height}">')
    svg_content.append('  <defs>')
    svg_content.append('    <linearGradient id="dropGrad" gradientUnits="userSpaceOnUse" x1="256" y1="472" x2="256" y2="132">')
    svg_content.append('      <stop offset="0%" stop-color="#20D5DF"/>')
    svg_content.append('      <stop offset="52%" stop-color="#3C79EE"/>')
    svg_content.append('      <stop offset="100%" stop-color="#5C3FD6"/>')
    svg_content.append('    </linearGradient>')
    svg_content.append('    <linearGradient id="snakeBlueGrad" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg_content.append('      <stop offset="0%" stop-color="#8fd3ff"/>')
    svg_content.append('      <stop offset="100%" stop-color="#306998"/>')
    svg_content.append('    </linearGradient>')
    svg_content.append('    <linearGradient id="snakeYellowGrad" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg_content.append('      <stop offset="0%" stop-color="#FFD43B"/>')
    svg_content.append('      <stop offset="100%" stop-color="#FFE873"/>')
    svg_content.append('    </linearGradient>')
    svg_content.append('  </defs>')
    
    # Icon group (untouched)
    svg_content.append('  <g id="icon">')
    svg_content.append('    <g stroke="#F4C3B0" stroke-width="26" stroke-linecap="round" fill="none">')
    svg_content.append('      <line x1="139" y1="121" x2="113" y2="89"/>')
    svg_content.append('      <line x1="256" y1="78"  x2="256" y2="40"/>')
    svg_content.append('      <line x1="373" y1="121" x2="399" y2="89"/>')
    svg_content.append('    </g>')
    svg_content.append('    <path fill="url(#dropGrad)" d="M 276 132 C 280 168, 296 194, 314 220 C 344 262, 372 306, 372 360 C 372 425, 320 472, 256 472 C 192 472, 140 425, 140 360 C 140 296, 180 248, 214 208 C 240 178, 262 156, 276 132 Z"/>')
    blue_snake_d = "M63.391 1.988c-4.222.02-8.252.379-11.8 1.007-10.45 1.846-12.346 5.71-12.346 12.837v9.411h24.693v3.137H29.977c-7.176 0-13.46 4.313-15.426 12.521-2.268 9.405-2.368 15.275 0 25.096 1.755 7.311 5.947 12.519 13.124 12.519h8.491V67.234c0-8.151 7.051-15.34 15.426-15.34h24.665c6.866 0 12.346-5.654 12.346-12.548V15.833c0-6.693-5.646-11.72-12.346-12.837-4.244-.706-8.645-1.027-12.866-1.008zM50.037 9.557c2.55 0 4.634 2.117 4.634 4.721 0 2.593-2.083 4.69-4.634 4.69-2.56 0-4.633-2.097-4.633-4.69-.001-2.604 2.073-4.721 4.633-4.721z"
    yellow_snake_d = "M91.682 28.38v10.966c0 8.5-7.208 15.655-15.426 15.655H51.591c-6.756 0-12.346 5.783-12.346 12.549v23.515c0 6.691 5.818 10.628 12.346 12.547 7.816 2.297 15.312 2.713 24.665 0 6.216-1.801 12.346-5.423 12.346-12.547v-9.412H63.938v-3.138h37.012c7.176 0 9.852-5.005 12.348-12.519 2.578-7.735 2.467-15.174 0-25.096-1.774-7.145-5.161-12.521-12.348-12.521h-9.268zM77.809 87.927c2.561 0 4.634 2.097 4.634 4.692 0 2.602-2.074 4.719-4.634 4.719-2.55 0-4.633-2.117-4.633-4.719 0-2.595 2.083-4.692 4.633-4.692z"
    svg_content.append('    <g transform="translate(176 260) scale(1.25)">')
    svg_content.append(f'       <path fill="url(#snakeBlueGrad)" transform="translate(0 10.26)" d="{blue_snake_d}" />')
    svg_content.append(f'       <path fill="url(#snakeYellowGrad)" transform="translate(0 10.26)" d="{yellow_snake_d}" />')
    svg_content.append('    </g>')
    svg_content.append('  </g>')
    
    # Wordmark group
    svg_content.append(f'  <!-- wordmark: Quicksand Bold, outlined to paths (no font dependency) -->')
    svg_content.append(f'  <g transform="translate({text_start_x} {text_baseline_y})">')
    
    for idx, item in enumerate(svg_paths):
        x_pos = item['x'] * scale_factor
        fill_color = "#FFD43B" if idx < 2 else "#363086"
        svg_content.append(f'    <!-- {item["char"]} -->')
        svg_content.append(f'    <path fill="{fill_color}" transform="translate({x_pos:.2f} 0) scale({scale_factor:.6f} -{scale_factor:.6f})" d="{item["d"]}" />')
        
    svg_content.append('  </g>')
    svg_content.append('</svg>')
    
    # Write to target logo file
    output_path = "/home/paddez/dev/pyyunoheat/docs/assets/logo.svg"
    with open(output_path, "w") as f:
        f.write("\n".join(svg_content) + "\n")
        
    print(f"Successfully generated logo.svg at {output_path}")
    
    if os.path.exists(local_font_path):
        os.remove(local_font_path)

if __name__ == "__main__":
    main()
