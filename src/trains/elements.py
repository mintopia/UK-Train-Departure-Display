import math
import time
from datetime import datetime
from pprint import pprint

import trains.utils as utils
from trains.config import Config

from luma.core.virtual import hotspot, snapshot
from PIL import Image, ImageDraw

# A standard display clock
class Clock(snapshot):
    def __init__(self, width, height, fonts, draw_fn=None, interval=1.0):
        super(Clock, self).__init__(width, height, draw_fn, interval)

        self.fonts = fonts

    def update(self, draw):
        time = datetime.now().time()
        hour, minute, seconds = str(time).split('.')[0].split(':')
        hourmin = "{0}:{1}".format(hour, minute)
        seconds = ":{0}".format(seconds)
        
        w1, h1 = draw.textsize(hourmin, self.fonts["boldlarge"])
        w2, h2 = draw.textsize(":00", self.fonts["boldtall"])

        margin = (self.width - w1 - w2) / 2

        draw.text((margin, 0), text=hourmin, font=self.fonts["boldlarge"], fill="yellow")
        draw.text((margin + w1, 5), text=seconds, font=self.fonts["boldtall"], fill="yellow")

# Static text that does not re-render unless asked for
class StaticText(snapshot):
    renderedText = None
    text = None
    align = "left"
    rendered = None

    def __init__(self, width, height, font, mode, draw_fn=None, interval=1.0, text=None, align="left", spacing=2, vertical_align="top"):
        super(StaticText, self).__init__(width, height, draw_fn, interval)

        self.font = font
        self.align = align
        self.vertical_align = vertical_align
        self.mode = mode
        self.spacing = spacing
        self.update_required = False

        self.update_text(text)

    def should_redraw(self):
        # We re-render every minute
        if self.rendered and time.monotonic() - 60 > self.rendered:
            return True
        
        return self.update_required or self.renderedText != self.text

    def update_text(self, text):
        self.text = text

        self.text_image = Image.new(self.mode, self.size)

        size = self.font.getsize_multiline(self.text)

        xpos = 0
        if self.align == "right":
            xpos = self.width - size[0]
        elif self.align == "center":
            xpos = math.floor((self.width - size[0]) / 2)
        
        ypos = 0
        if self.vertical_align == "bottom":
            ypos = self.height - size[1]
        elif self.vertical_align == "middle":
            ypos = math.floor((self.height - size[1]) / 2)

        canvas = ImageDraw.Draw(self.text_image)
        canvas.text((xpos, ypos), text=self.text, font=self.font, fill="yellow", align=self.align, spacing=self.spacing)

        self.rendered = time.monotonic()

    def paste_into(self, image, xy):
        if not self.should_redraw():
            return
        
        self.update_required = False
        self.renderedText = self.text
        image.paste(self.text_image, xy)


class ScrollingText(snapshot):
    def __init__(self, width, height, font, mode, text="", draw_fn=None, interval=1.0, align="left"):
        super(ScrollingText, self).__init__(width, height, draw_fn, interval)
        self.font = font
        self.rendered_text = None
        self.mode = mode
        self.text = None
        self.align = align

        if text:
            self.update_text(text)
    
    def reset(self):
        if not self.text:
            return
        
        self.ypos = self.height
        self.top = 0
        self.bottom = 0
        self.left = 0
        self.right = min(self.width, self.text.width)
        self.last_updated = time.monotonic()
    
    def update_text(self, text):
        if text == self.rendered_text:
            return

        self.rendered_text = text
        
        text_size = self.font.getsize(text)

        if self.text:
            del self.text
        
        self.text = Image.new(self.mode, text_size)

        canvas = ImageDraw.Draw(self.text)
        canvas.text((0, 0), text=text, font=self.font, fill="yellow")

        self.xpos = 0
        if text_size[0] <= self.width:
            if self.align == "right":
                self.xpos = self.width - text_size[0]
            elif self.align == "center":
                self.xpos = math.floor((self.width - text_size[0]) / 2)

        self.reset()
    
    def paste_into(self, image, xy):
        pause = 0

        if self.text:
            im = Image.new(image.mode, self.size)

            if self.ypos <= 2 and self.ypos > 0:
                if self.text.width <= self.width:
                    # Our text fits in the viewport and we've finished scrolling
                    # we don't need to update for a minute
                    pause = 60
                else:
                    # Our text doesn't fit, but we want to scroll left in 2 seconds
                    pause = 2
            
            if self.left >= (self.right - 1):
                # We've finished scrolling left to right. We pause for 2 seconds
                pause = 2

            self.update_location()

            im.paste(self.text.crop((self.left, self.top, self.right, self.bottom)), (self.xpos, self.ypos))
            image.paste(im, xy)
            del im

        self.last_updated = time.monotonic() + pause
    
    def should_redraw(self):
        if not self.text:
            return False
        
        return super(ScrollingText, self).should_redraw()
    
    def update_location(self):
        if not self.text:
            return
        
        if self.bottom < self.height:
            # Y Scroll
            self.bottom += 2
            self.ypos -= 2

        elif self.text.width >= self.width:
            # Y scrolling
            self.left += 1
            if self.right < self.text.width:
                self.right += 1

            if self.right <= self.left:
                # Scroll finished
                self.reset()
        return
    
class NextService(snapshot):
    def __init__(self, font, mode, data=None):
        super(NextService, self).__init__(256, 12, None, 0.04)

        self.font = font
        self.mode = mode

        self.rendered_data = None
        self.text = None

        if data:
            self.update_data(data)
    
    def reset(self):
        if not self.text:
            return
        
        self.ypos = self.height
        self.bottom = 0
        self.last_updated = time.monotonic()
    
    def update_data(self, data):
        if data == self.rendered_data:
            return

        self.rendered_data = data

        if self.text:
            del self.text
        
        self.text = Image.new(self.mode, self.size)
        canvas = ImageDraw.Draw(self.text)
        render_departure(canvas, self.font, 1, data)

        self.reset()
    
    def paste_into(self, image, xy):
        pause = 0

        if self.text:
            im = Image.new(image.mode, self.size)

            if self.bottom < self.height:
                # Y Scroll
                self.bottom += 2
                self.ypos -= 2
            else:
                # Pause rendering for a minute
                pause = 60

            im.paste(self.text.crop((0, 0, self.text.width, self.bottom)), (0, self.ypos))
            image.paste(im, xy)
            del im

        self.last_updated = time.monotonic() + pause
    
    def should_redraw(self):
        if not self.text:
            return False
        
        return super(NextService, self).should_redraw()

class RemainingServices(snapshot):
    def __init__(self, font, mode, data=None):
        super(RemainingServices, self).__init__(256, 12, None, 0.04)

        self.font = font
        self.mode = mode

        self.rendered_data = None
        self.text = None

        if data:
            self.update_data(data)
    
    def reset(self):
        if not self.text:
            return
        
        self.ypos = self.height
        self.bottom = 0
        self.top = 0
        self.ystart = 0

        self.last_updated = time.monotonic()
    
    def update_data(self, data):
        if data == self.rendered_data:
            return

        self.rendered_data = data
        if not data:
            return

        if self.text:
            del self.text
        
        self.text = Image.new(self.mode, (self.width, (len(data) + 2) * 12))
        canvas = ImageDraw.Draw(self.text)

        i = 1
        for departure in data:
            render_departure(canvas, self.font, i + 1, departure, ypos=12 * i)
            i += 1
        
        # Render last item again for easier scrolling
        render_departure(canvas, self.font, 2, data[0], 12 * i)

        self.reset()
    
    def paste_into(self, image, xy):
        pause = 0

        if self.text:
            im = Image.new(image.mode, self.size)

            self.update_location()
            if self.top > 0 and self.top % 12 == 0:
                pause = 5

            im.paste(self.text.crop((0, self.top, self.text.width, self.bottom)), (0, self.ypos))
            image.paste(im, xy)
            del im

            if self.bottom >= self.text.height:
                # We've hit the bottom
                self.top = 12
                self.bottom = 24

        self.last_updated = time.monotonic() + pause
    
    def should_redraw(self):
        if not self.text:
            return False
        
        return super(RemainingServices, self).should_redraw()
    
    def update_location(self):
        if not self.text:
            return
        
        if self.ypos > 0:
            # We're scrolling up our initial scroll
            self.ypos -= 2
            self.bottom += 2
        else:
            self.top += 2
            self.bottom += 2


def render_departure(canvas, font, order=1, departure=None, ypos=0):
    if not departure:
        return
    
    # Order: Left
    canvas.text((0, ypos), text=utils.ordinal(order), font=font, fill="yellow")

    # Scheduled: Center
    align = utils.align(font, departure["scheduled"], 28, "center")
    canvas.text((17 + align, ypos), text=departure["scheduled"], font=font, fill="yellow")

    # Headcode: Optional
    xpos = 0
    if Config.get("settings.layout.headcodes"):
        xpos += 27
        align = utils.align(font, departure["headcode"], 27, "center")
        canvas.text((45 + align, ypos), text=departure["headcode"], font=font, fill="yellow")

    # Platform: Center
    align = utils.align(font, departure["platform"], 19, "center")
    canvas.text((45 + align + xpos, ypos), text=departure["platform"], font=font, fill="yellow")

    # Destination: Left
    canvas.text((64 + xpos, ypos), text=departure["destination"]["abbr_name"], font=font, fill="yellow")

    # Status: Right
    align = utils.align(font, departure["status"], 40, "right")
    canvas.text((216 + align, ypos), text=departure["status"], font=font, fill="yellow")
    
