#!/usr/bin/env python3

import sys
import PIL.Image
import PIL.ImageChops


def trim_columns(img, threshold: int):
    'Remove continuous identical columns from the image.'
    img = img.transpose(PIL.Image.TRANSPOSE)
    pixels = bytes(img.getdata())
    new_columns = []
    for offset in range(0, len(pixels), img.width):
        column = pixels[offset:offset + img.width]
        if not new_columns or new_columns[-1] != column:
            same_columns = 0
        elif same_columns == threshold:
            continue
        else:
            same_columns += 1
        new_columns.append(column)

    img.putdata(b''.join(new_columns))
    img = img.transpose(PIL.Image.TRANSPOSE)
    return img.crop((0, 0, len(new_columns), img.height))


def join_img(head, *tail, vertical=False):
    'Stack multiple images into a single one, horizontally or vertically.'
    for img in tail:
        if vertical:
            offset = (0, head.height)
            new_size = max(head.width, img.width), head.height + img.height
        else:
            offset = (head.width, 0)
            new_size = head.width + img.width, max(head.height, img.height)
        head = head.crop((0, 0, *new_size))
        head.paste(img, offset)
    return head


def decompose(img):
    'Break down the image into parts.'
    components = {
        'header_left': (0, 0, 800, 240),
        'header_right': (img.width - 80, 0, img.width, 240),
        'body': (0, 240, img.width, img.height - 30),
        'body_left': (0, 240, 75, img.height - 30),
        'body_right': (75, 240, img.width, img.height - 30),
        'footer': (0, img.height - 30, img.width, img.height),
    }
    return type('parts', (), {k: img.crop(v) for k, v in components.items()})


def main(path):
    'Trim whitespaces in different parts of the image and join them back.'
    img = PIL.Image.open(path)
    parts = decompose(img)
    header = join_img(parts.header_left, parts.header_right, vertical=False)
    min_footer_width = PIL.ImageChops.invert(parts.footer).getbbox()[2]
    if min_footer_width > header.width:
        return
    footer = parts.footer.crop((0, 0, header.width, parts.footer.height))

    for threshold in 100, 80, 60, 40, 20, 15, 10, 5, 4, 3, 2:
        parts.body_right = trim_columns(parts.body_right, threshold)
        if parts.body_left.width + parts.body_right.width > header.width:
            continue

        padding_size = header.width - parts.body_right.width, parts.body.height
        parts.body_left = parts.body.crop((0, 0, *padding_size))
        body = join_img(parts.body_left, parts.body_right, vertical=False)
        join_img(header, body, footer, vertical=True).save(path)
        print(threshold, path)
        return


if __name__ == '__main__':
    for path in sys.argv[1:]:
        main(path)
