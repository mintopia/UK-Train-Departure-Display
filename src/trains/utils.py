import math

from trains.config import Config

try:
    import cv2
    import numpy
except ImportError:
    if Config.get("debug.dummy", False):
        print("Unable to load CV2 or numpy. Dummy mode will not render.")
    pass

def wordwrap(font, width, input):
    words = input.split()
    lines = []
    line = ""

    while words:
        word = words.pop(0)
        newline = line + " " + word
        if font.getsize_multiline(newline.strip())[0] > width:
            # Text is too wide, wrap
            if line:
                # We have a full line
                lines.append(line.strip())
                line = word
            else:
                # Line was empty, let's just overflow
                lines.append(newline.strip())
                line = ""
        else:
            line = newline

    if line:
        lines.append(line)
    return lines

def ordinal(number):
    number = int(number)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(number % 10, 4)]
    if 11 <= (number % 100) <= 13:
        suffix = 'th'
    return str(number) + suffix

def align(font, text, width, align="center"):
    text_width = font.getsize_multiline(text)[0]
    if align == "center":
        return max(math.floor((width - text_width) / 2), 0)
    elif align == "right":
        return max(width - text_width, 0)
    else:
        return 0

def display_image(name, image):
    if not numpy and cv2:
        return
    
    if not image.width or not image.height:
        return
    
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    np_image = numpy.array(image)
    np_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    np_image = cv2.resize(np_image, None, fx = 2, fy = 2, interpolation = cv2.INTER_AREA)
    cv2.imshow(name, np_image)
    cv2.waitKey(1)