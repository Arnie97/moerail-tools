#!/usr/bin/env python3

from io import BytesIO
from flask import send_file, Flask
from shot import query

app = Flask(__name__)


@app.route('/<train>')
def image_route_handler(train):
    'Responds HTTP requests.'
    img = query(train)
    img = img.convert('1', dither=0)
    return serve_image(img)


def serve_image(img):
    'Converts Pillow image to Flask response.'
    buffer = BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0')
