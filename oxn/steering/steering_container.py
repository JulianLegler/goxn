# This python should run in a sidecar container in a kubernetes cluster.
# It can be used to execute specific commands on this specific pod.
# Such as:
# - Killing the pod
# - Manipulate the internal network configuration (e.g. packet loss, latency, etc.) via tc
# - start stress-ng to simulate high loads

import os
import subprocess
import signal
import json
import logging
import logging.handlers
import argparse

from flask import Flask, request, jsonify

app = Flask(__name__)

# Global variables
log = None

# Constants
POD_NAME = os.environ.get('POD_NAME')
POD_NAMESPACE = os.environ.get('POD_NAMESPACE')
POD_IP = os.environ.get('POD_IP')
POD_PORT = os.environ.get('POD_PORT')
POD_LABELS = os.environ.get('POD_LABELS')
POD_LABELS = json.loads(POD_LABELS) if POD_LABELS else {}
POD_LABELS['pod_name'] = POD_NAME
POD_LABELS['pod_namespace'] = POD_NAMESPACE
POD_LABELS['pod_ip'] = POD_IP
POD_LABELS['pod_port'] = POD_PORT

# Constants
DEFAULT_LOG_LEVEL = logging.DEBUG
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_FILE = '/var/log/steering_pod.log'

# Constants
DEFAULT_PORT = 5000
DEFAULT_HOST = '0.0.0.0'

# general log call for all incoming traffic
@app.before_request
def log_request():
    log.info(f'Received request: {request.method} {request.path} {request.get_json()}')

# Listen for incoming requests
@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({'status': 'ok'})

@app.route('/info', methods=['GET'])
def info():
    return jsonify({
        'status': 'ok',
        'message': 'This is OXNs steering container',
        'pod_name': POD_NAME,
        'pod_namespace': POD_NAMESPACE,
        'pod_ip': POD_IP,
        'pod_port': POD_PORT,
        'pod_labels': POD_LABELS
    })

@app.route('/kill', methods=['POST'])
def kill():
    log.info('Received kill request')
    os.kill(os.getpid(), signal.SIGTERM)
    return jsonify({'status': 'ok'})

@app.route('/exec', methods=['POST'])
def exec():
    data = request.get_json()
    cmd = data.get('cmd')
    log.info(f'Received exec request: {cmd}')
    try:
        output = subprocess.check_output(cmd, shell=True)
        return jsonify({'status': 'ok', 'output': output.decode()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'ok'})

@app.route('/tc', methods=['POST'])
def tc():
    data = request.get_json()
    cmd = data.get('cmd')
    log.info(f'Received tc request: {cmd}')
    try:
        output = subprocess.check_output(cmd, shell=True)
        return jsonify({'status': 'ok', 'output': output.decode()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'ok'})

@app.route('/stress', methods=['POST'])
def stress():
    data = request.get_json()
    cmd = data.get('cmd')
    log.info(f'Received stress request: {cmd}')
    try:
        output = subprocess.check_output(cmd, shell=True)
        return jsonify({'status': 'ok', 'output': output.decode()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'ok'})

def setup_logging(log_level, log_file):
    global log
    log = logging.getLogger('steering_pod')
    log.setLevel(log_level)
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    if log_file:
        handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

def main():
    global log
    parser = argparse.ArgumentParser(description='Steering Pod')
    parser.add_argument('--log-level', type=int, default=DEFAULT_LOG_LEVEL, help='Log level')
    parser.add_argument('--log-file', type=str, default=DEFAULT_LOG_FILE, help='Log file')
    parser.add_argument('--host', type=str, default=DEFAULT_HOST, help='Host')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port')
    args = parser.parse_args()

    setup_logging(args.log_level, args.log_file)
    log.info('Starting steering pod')

    app.run(host=args.host, port=args.port)

if __name__ == '__main__':
    main()
