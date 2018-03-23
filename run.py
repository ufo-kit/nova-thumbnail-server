import os
import hashlib
import subprocess
import shlex
import requests
import json
import atexit
import socket
import numpy as np
from multiprocessing import Process
from flask import Flask, request, jsonify, abort, url_for, send_file
from flask_script import Manager

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['NOVA_API_URL'] = 'http://localhost:5000/api'

SERVICE_NAME = 'thumbnail-server'
SERVICE_DESCRIPTION = """Thumbnail server"""
SERVICE_SECRET = '123'

manager = Manager(app)

jobs = {}

def abort_for_status(response):
    if response.status_code != 200:
        try:
            message = json.loads(response.text)
            abort(response.status_code, message['message'])
        except ValueError:
            abort(response.status_code)


@app.route('/<user>/<dataset>')
def get_thumbnail(user, dataset):
    size = int(request.args.get('size', 128))
    force = bool(request.args.get('force', False))
    path = os.path.join('cache', user, dataset, '{}.jpg'.format(size))

    if not os.path.exists(path) or force:
        # authenticate for path access
        token = request.args.get('token')
        headers = {'Auth-Token': token}
        url = '{}/datasets/{}/{}'.format(app.config['NOVA_API_URL'], user, dataset)
        r = requests.get(url, headers=headers)
        abort_for_status(r)

        # get middle slice
        slice_path = os.path.join(r.json()['path'], 'slices')
        slices = sorted(os.listdir(slice_path))
        fname = os.path.join(slice_path, slices[int(len(slices) / 2)])

        # resize and color
        cmd = "ufo-launch --quieter read path={} ! crop width=512 height=512 from-center=true ! rescale width={} height={} ! map-color ! write filename={}"
        cmd = cmd.format(fname, size, size, path)
        output = subprocess.call(shlex.split(cmd))

    return send_file(path, mimetype='image/jpeg')


def register(host):
    data = dict(name=SERVICE_NAME, url='http://127.0.0.1:5003', secret=SERVICE_SECRET)
    requests.post('/'.join((host, 'services')), data=data)


def shutdown(host):
    data = dict(secret=SERVICE_SECRET)
    requests.delete('/'.join((host, 'service', SERVICE_NAME)), data=data)


@app.route('/service')
def service():
    data = dict(status='running')
    return jsonify(data)


if __name__ == '__main__':
    register(app.config['NOVA_API_URL'])
    atexit.register(shutdown, app.config['NOVA_API_URL'])
    manager.run()
