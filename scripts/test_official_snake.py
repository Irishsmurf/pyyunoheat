import sys

def main():
    # Yellow snake path directly from python-original.svg
    yellow_snake_d = "M91.682 28.38v10.966c0 8.5-7.208 15.655-15.426 15.655H51.591c-6.756 0-12.346 5.783-12.346 12.549v23.515c0 6.691 5.818 10.628 12.346 12.547 7.816 2.297 15.312 2.713 24.665 0 6.216-1.801 12.346-5.423 12.346-12.547v-9.412H63.938v-3.138h37.012c7.176 0 9.852-5.005 12.348-12.519 2.578-7.735 2.467-15.174 0-25.096-1.774-7.145-5.161-12.521-12.348-12.521h-9.268zM77.809 87.927c2.561 0 4.634 2.097 4.634 4.692 0 2.602-2.074 4.719-4.634 4.719-2.55 0-4.633-2.117-4.633-4.719 0-2.595 2.083-4.692 4.633-4.692z"

    # SVG layout
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="dropGrad" gradientUnits="userSpaceOnUse" x1="256" y1="472" x2="256" y2="132">
      <stop offset="0%" stop-color="#20D5DF"/>
      <stop offset="52%" stop-color="#3C79EE"/>
      <stop offset="100%" stop-color="#5C3FD6"/>
    </linearGradient>
  </defs>
  <g id="icon">
    <g stroke="#F4C3B0" stroke-width="26" stroke-linecap="round" fill="none">
      <line x1="139" y1="121" x2="113" y2="89"/>
      <line x1="256" y1="78"  x2="256" y2="40"/>
      <line x1="373" y1="121" x2="399" y2="89"/>
    </g>
    <!-- Outer droplet -->
    <path fill="url(#dropGrad)" d="M 276 132 C 280 168, 296 194, 314 220 C 344 262, 372 306, 372 360 C 372 425, 320 472, 256 472 C 192 472, 140 425, 140 360 C 140 296, 180 248, 214 208 C 240 178, 262 156, 276 132 Z"/>
    
    <!-- Official Yellow Python Snake Mascot scaled/centered to fit inside -->
    <g transform="translate(150.85 265.62) scale(1.5)">
       <path fill="#FFD43B" transform="translate(0 10.26)" d="{yellow_snake_d}" />
    </g>
  </g>
</svg>"""

    with open("docs/assets/icon_official_test.svg", "w") as f:
        f.write(svg_content)
    print("icon_official_test.svg written successfully.")

if __name__ == "__main__":
    main()
