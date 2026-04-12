from flask import Flask, jsonify
import datetime
import socket

app = Flask(__name__)

@app.route("/api/v1/details")

def details():
    return ({
        'time': datetime.datetime.now().strftime("%I:%M:%p on %B %d, %Y"),
        'hostname': socket.gethostname(),
        'message': 'You are doing great, human! :)'
    })

@app.route("/api/v1/health")

def health():
    return ({ 'status': 'up' }), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
