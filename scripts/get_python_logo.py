import urllib.request
import re
import sys

def main():
    url = "https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg"
    print(f"Downloading official Python logo SVG from {url}...")
    try:
        response = urllib.request.urlopen(url)
        content = response.read().decode('utf-8')
        print("Download successful.")
    except Exception as e:
        print(f"Failed to download: {e}")
        sys.exit(1)
        
    # Find all path elements in the SVG
    paths = re.findall(r'<path[^>]*d="([^"]+)"[^>]*>', content)
    print(f"Found {len(paths)} paths in the SVG.")
    
    # In the standard Python logo, there are two main path segments:
    # One is the blue snake, one is the yellow snake.
    # Often, there are also class names or inline fills.
    # Let's inspect the paths and their parameters.
    # Let's print out the first few characters of each path to identify them.
    for i, d in enumerate(paths):
        print(f"Path {i}: d='{d[:100]}...'")
        
    # We will write the full SVG to a file so we can analyze it or use the paths directly.
    with open("python_original_logo.svg", "w") as f:
        f.write(content)
    print("Saved logo to python_original_logo.svg")

if __name__ == "__main__":
    main()
