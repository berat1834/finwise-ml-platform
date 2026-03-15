# -*- coding: utf-8 -*-
from waitress import serve
from app import app

if __name__ == "__main__":
    # Start production server on localhost:5000
    serve(app, host="127.0.0.1", port=5000)
