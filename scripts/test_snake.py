import sys

def main():
    # Style the inner droplet as a stylized yellow python snake
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
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
    
    <!-- Stylized Yellow Python Snake replacing the inner droplet -->
    <path fill="#FFD43B" fill-rule="evenodd" d="M 270 330 C 235 330, 220 345, 220 365 C 220 385, 235 395, 250 395 C 255 395, 260 400, 260 405 V 420 C 260 435, 275 448, 292 443 C 309 438, 309 415, 295 405 C 285 400, 280 390, 280 375 C 280 350, 295 330, 270 330 Z M 242 355 m -7 0 a 7 7 0 1 0 14 0 a 7 7 0 1 0 -14 0"/>
  </g>
</svg>"""

    with open("docs/assets/icon_test.svg", "w") as f:
        f.write(svg_content)
    print("icon_test.svg written successfully.")

if __name__ == "__main__":
    main()
