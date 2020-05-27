import math
import time
from datetime import datetime

import trains.utils as utils

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

    def __init__(self, width, height, font, mode, draw_fn=None, interval=1.0, text=None, align="left", spacing=2):
        super(StaticText, self).__init__(width, height, draw_fn, interval)

        self.font = font
        self.align = align
        self.mode = mode
        self.spacing = spacing
        self.update_required = False

        self.update_text(text)

    def should_redraw(self):
        return self.update_required or self.renderedText != self.text

    def update_text(self, text):
        self.text = text

        self.text_image = Image.new(self.mode, self.size)

        size = self.font.getsize(self.text)
        xpos = utils.align(self.font, self.text, self.width, self.align)

        canvas = ImageDraw.Draw(self.text_image)
        canvas.text((xpos, 0), text=self.text, font=self.font, fill="yellow", align=self.align, spacing=self.spacing)

    def paste_into(self, image, xy):
        if not self.should_redraw():
            return
        
        self.update_required = False
        self.renderedText = self.text
        image.paste(self.text_image, xy)

# A message bar with an updating list of messages. Messages will scroll horizontally then
# scroll up to transition
class MessageBar(snapshot):
    def __init__(self, width, height, font, mode, draw_fn=None, interval=1.0, messages=[], align="left", hold_time=4, minimum_time=20):
        super(MessageBar, self).__init__(width, height, draw_fn, interval)
        self.messages = messages
        self.align = align
        self.hold_time = 4
        self.minimum_time = 20
        self.font = font
        self.debug = False

        self.current_image = MessageBarText(self.mode, self.font, height, align=align)
        self.next_image = MessageBarText(self.mode, self.font, height, scroll_in=True, align=align)

        # Initial state is to transition between lines
        self.reset()
    
    def reset(self):
        self.pointer = 0
        self.state = "transition"
        self.transition_time = time.monotonic

        next_message = ""
        if self.messages:
            next_message = self.messages[0]

        self.current_image.update_text("")
        self.next_image.update_text(next_message)
    
    def update_messages(self, messages=[]):
        if messages == self.messages:
            return
        
        self.messages = messages
        self.reset()


    def paste_into(self, image, xy):
        # This is our canvas to render on to
        im = Image.new(image.mode, self.size)

        transition = False

        # Handle vertical scroll
        if self.state == "transition":
            if not self.next_image.transition_complete():
                self.next_image.scroll_up()
            
            if not self.current_image.transition_complete():
                self.current_image.scroll_up()

            if self.next_image.transition_complete() and self.current_image.transition_complete():
                self.state = "holding"
                self.transition_time = time.monotonic()
                transition = True
        
        elif self.state == "holding":
            if time.monotonic() > self.transition_time + self.hold_time:
                self.state = "scrolling"
                self.transition_time = time.monotonic()

        elif self.state == "scrolling":
            if not self.current_image.scrolling_complete():
                self.current_image.scroll_left()
            elif time.monotonic() > self.transition_time + self.hold_time:
                self.transition_time = time.monotonic()
                if len(self.messages) > 1:
                    self.state = "transition"
                else:
                    self.current_image.scroll_x = 0
                    self.state = "holding"
            
        # render our canvas onto the backing image
        self.current_image.paste(im)
        self.next_image.paste(im)

        image.paste(im, xy)
        del im

        if transition:
            self.transition()

        self.last_updated = time.monotonic()
    
    def transition(self):
        # Reset our scrolling
        self.current_image.scroll_y = 0
        self.current_image.scroll_x = 0
        self.next_image.scroll_y = 0
        self.next_image.scroll_x = 0

        # Move the image and text
        self.current_image.image = self.next_image.image
        self.current_image.text = self.next_image.text

        # Get our next message
        self.pointer += 1
        if self.pointer >= len(self.messages):
            self.pointer = 0

        if not self.messages:
            message = ""
        else:
            message = self.messages[self.pointer]
        
        self.next_image.update_text(message)


class MessageBarText:
    def __init__(self, mode, font, height, scroll_in=False, text="", align="left"):
        self.text = text
        self.font = font
        self.mode = mode
        self.height = height
        self.scroll_in = scroll_in
        self.align = align
        self.debug = False

        self.scroll_y = 0
        self.render()
        
    def render(self):
        size = self.font.getsize(self.text)

        self.image = Image.new(self.mode, (size[0], self.height))
        canvas = ImageDraw.Draw(self.image)
        canvas.text((0, 0), text=self.text, font=self.font, fill="yellow")

        self.scroll_x = 0
        self.scroll_y = 0
    
    def update_text(self, text):
        if self.text == text:
            return
        
        self.text = text
        self.render()
    
    def scroll_up(self):
        self.scroll_y += 1
    
    def scroll_left(self):
        self.scroll_x += 1

    def transition_complete(self):
        return self.scroll_y == self.height
    
    def scrolling_complete(self):
        return self.scroll_x == self.image.width
    
    def paste(self, destination):
        destination_width = destination.size[0]

        # Y scrolling
        top = 0
        bottom = 0
        destination_y = 0
        if self.scroll_in:
            bottom = self.scroll_y
            destination_y = self.height - bottom
        else:
            top = self.scroll_y
            bottom = self.height

        # X Scrolling
        left = 0
        destination_x = 0
        if self.image.width > destination_width:
            # We need to scroll
            left = self.scroll_x
        else:
            # We don't need to scroll - we might need to align
            destination_x = utils.align(self.font, self.text, destination_width, self.align)
        
        right = left + destination_width
        right = max(right, self.image.width)

        # Nothing to render
        if top == bottom or left == right:
            return

        crop = self.image.crop((left, top, right, bottom))
        return destination.paste(crop, (destination_x, destination_y))

# Horizontally scrolling text
class ScrollingText(snapshot):
    xpos = 0
    text = None
    pause = 0
    renderedText = None

    def __init__(self, width, height, mode, font, text="", draw_fn=None, interval=1.0, pause = 0):
        super(ScrollingText, self).__init__(width, height, draw_fn, interval)
        self.font = font
        self.mode = mode
        self.starting_pause = pause
        self.update_text(text)
    
    def update_text(self, text):
        if text == self.renderedText:
            return

        self.renderedText = text
        xpos = 0
        pause = 0
        
        text_size = self.font.getsize(text)
        self.text = Image.new(self.mode, text_size)

        canvas = ImageDraw.Draw(self.text)
        canvas.text((0, 0), text=text, font=self.font, fill="yellow")

    def paste_into(self, image, xy):
        im = Image.new(image.mode, self.size)

        width = self.size[0]
        height = self.size[1]

        # Get our render width - This is for our scroll
        render_width = width - self.xpos

        # Initial X pos of text box to blit
        text_x_pos = 0

        if render_width > width:
            # We are rendering more than the viewport, we need to scroll the text
            # This is our text X pos
            text_x_pos = render_width - width;
            render_width = width
            if text_x_pos > self.text.width:
                # We have ran out of text. Scrolling is done, reset xPos
                self.xpos = 0
                text_x_pos = 0
                render_width = 0

        render_x_pos = self.xpos
        if render_x_pos < 0:
            render_x_pos = 0

        # Blit textCanvas onto draw
        if render_width > 0:
            im.paste(self.text.crop((text_x_pos, 0, text_x_pos + render_width, self.text.height)), (render_x_pos, 0))

        if self.xpos == 0 and self.pause < self.starting_pause:
            self.pause += 1
        else:
            self.pause = 0
            self.xpos -= 1

        image.paste(im, xy)
        del im

        self.last_updated = time.monotonic()
