import sys

def main():
    # Paths from python-original.svg
    blue_snake_d = "M63.391 1.988c-4.222.02-8.252.379-11.8 1.007-10.45 1.846-12.346 5.71-12.346 12.837v9.411h24.693v3.137H29.977c-7.176 0-13.46 4.313-15.426 12.521-2.268 9.405-2.368 15.275 0 25.096 1.755 7.311 5.947 12.519 13.124 12.519h8.491V67.234c0-8.151 7.051-15.34 15.426-15.34h24.665c6.866 0 12.346-5.654 12.346-12.548V15.833c0-6.693-5.646-11.72-12.346-12.837-4.244-.706-8.645-1.027-12.866-1.008zM50.037 9.557c2.55 0 4.634 2.117 4.634 4.721 0 2.593-2.083 4.69-4.634 4.69-2.56 0-4.633-2.097-4.633-4.69-.001-2.604 2.073-4.721 4.633-4.721z"
    yellow_snake_d = "M91.682 28.38v10.966c0 8.5-7.208 15.655-15.426 15.655H51.591c-6.756 0-12.346 5.783-12.346 12.549v23.515c0 6.691 5.818 10.628 12.346 12.547 7.816 2.297 15.312 2.713 24.665 0 6.216-1.801 12.346-5.423 12.346-12.547v-9.412H63.938v-3.138h37.012c7.176 0 9.852-5.005 12.348-12.519 2.578-7.735 2.467-15.174 0-25.096-1.774-7.145-5.161-12.521-12.348-12.521h-9.268zM77.809 87.927c2.561 0 4.634 2.097 4.634 4.692 0 2.602-2.074 4.719-4.634 4.719-2.55 0-4.633-2.117-4.633-4.719 0-2.595 2.083-4.692 4.633-4.692z"

    # We center the combined logo (spanning roughly X: 14 to 114, Y: 1.9 to 114)
    # The bounds are: width = 100, height = 112.
    # Scaled by 1.25, the width is 125px, height is 140px.
    # Center X in 128 viewport is ~64. Scaled by 1.25, center X is 80px.
    # Target center X is 256. Translation X = 256 - 80 = 176px.
    # Center Y of paths (including 10.26 translation) is ~68px.
    # Scaled by 1.25, center Y is 85px.
    # Target center Y in droplet is ~345px. Translation Y = 345 - 85 = 260px.

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="dropGrad" gradientUnits="userSpaceOnUse" x1="256" y1="472" x2="256" y2="132">
      <stop offset="0%" stop-color="#20D5DF"/>
      <stop offset="52%" stop-color="#3C79EE"/>
      <stop offset="100%" stop-color="#5C3FD6"/>
    </linearGradient>
    <linearGradient id="snakeBlueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8fd3ff"/>
      <stop offset="100%" stop-color="#306998"/>
    </linearGradient>
    <linearGradient id="snakeYellowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FFD43B"/>
      <stop offset="100%" stop-color="#FFE873"/>
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
    
    <!-- Official interlocked snakes centered inside -->
    <g transform="translate(176 250) scale(1.25)">
       <path fill="url(#snakeBlueGrad)" transform="translate(0 10.26)" d="{blue_snake_d}" />
       <path fill="url(#snakeYellowGrad)" transform="translate(0 10.26)" d="{yellow_snake_d}" />
    </g>
  </g>
</svg>"""

    with open("docs/assets/icon_two_snakes.svg", "w") as f:
        f.write(svg_content)
    print("icon_two_snakes.svg written successfully.")

if __name__ == "__main__":
    main()
