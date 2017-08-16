#!/usr/bin/env python3

import os
from PIL import Image


def crop(src, dest):
    empty = Image.open('empty.png')
    mask = Image.open('mask.png')

    for file in os.listdir(src):
        im = Image.open(src + file).crop((3, 22, 1030, 622))
        Image.composite(im, empty, mask).save(dest + file)


if __name__ == '__main__':
    crop('temp/', 'img/')
