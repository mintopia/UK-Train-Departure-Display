def wordwrap(font, width, input):
    words = input.split()
    lines = []
    line = ""

    while words:
        word = words.pop(0)
        newline = line + " " + word
        if font.getsize(newline.strip())[0] > width:
            # Text is too wide, wrap
            if line:
                # We have a full line
                lines.append(line)
                line = word
            else:
                # Line was empty, let's just overflow
                lines.append(newline)
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