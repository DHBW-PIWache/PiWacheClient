from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)
process = None

@app.route('/start', methods=['POST'])
def start_script():
    global process
    if process is None or process.poll() is not None:
        process = subprocess.Popen(['python3', 'Python/Combined_detection.py'])
        return jsonify({"status": "started"}), 200
    return jsonify({"status": "already running"}), 200

@app.route('/stop', methods=['POST'])
def stop_script():
    global process
    if process and process.poll() is None:
        process.terminate()
        return jsonify({"status": "stopped"}), 200
    return jsonify({"status": "not running"}), 200

@app.route('/status', methods=['GET'])
def check_status():
    global process
    if process and process.poll() is None:
        return jsonify({"status": "running"}), 200
    return jsonify({"status": "stopped"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)