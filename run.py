import os
import hashlib
import subprocess
import shlex
import requests
import json
import atexit
import socket
import tifffile
import viridis
import numpy as np
from multiprocessing import Process
from flask import Flask, request, jsonify, abort, url_for, send_file
from flask_script import Manager
from PIL import Image

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['NOVA_API_URL'] = 'http://localhost:5000/api'

SERVICE_NAME = 'thumbnail-server'
SERVICE_DESCRIPTION = """Thumbnail server"""
SERVICE_SECRET = '123'

manager = Manager(app)

jobs = {}

viridis_data = np.array(viridis.color)

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
    jpg_path = os.path.join('cache', user, dataset, '{}.jpg'.format(size))
    tif_path = os.path.join('cache', user, dataset, '{}.tif'.format(size))

    if not os.path.exists(jpg_path) or force:
        # authenticate for path access
        token = request.args.get('token')
        headers = {'Auth-Token': token}
        url = '{}/datasets/{}/{}'.format(app.config['NOVA_API_URL'], user, dataset)
        r = requests.get(url, headers=headers)
        abort_for_status(r)

        # get middle slice
        slice_path = os.path.join(r.json()['path'], 'slices')
        slices = sorted(os.listdir(slice_path))
        fname = os.path.join(slice_path, slices[len(slices) / 2])

        # resize
        cmd = "ufo-launch --quieter read path={} ! rescale width={} height={} ! write bits=8 filename={}".format(fname, size, size, tif_path)
        output = subprocess.call(shlex.split(cmd))

        # color
        image = tifffile.imread(tif_path)
        r = viridis_data[:,0][image] * 256
        g = viridis_data[:,1][image] * 256
        b = viridis_data[:,2][image] * 256
        image = Image.fromarray(np.dstack((np.dstack((r, g)), b)).astype(np.uint8))
        image.save(jpg_path)

    return send_file(jpg_path, mimetype='image/jpeg')



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
