from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return 'OK'

if __name__ == '__main__':
    print("Starting minimal Flask test on port 5001...")
    app.run(host='127.0.0.1', port=5001, debug=False)
