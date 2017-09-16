#!/usr/bin/env python3

from io import BytesIO
from flask import send_file, Flask
from shot import Automation

app = Flask(__name__)


@app.route('/<train>')
def image_route_handler(train):
    'Responds HTTP requests.'
    me.query(train)
    img = me.get_shot()
    return serve_image(img)


def serve_image(img):
    'Converts Pillow image to Flask response.'
    buffer = BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')


if __name__ == '__main__':
    me = Automation()
    app.run(host='0.0.0.0')
