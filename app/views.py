from flask import jsonify, request, render_template
from app import app
from app.contracts import get_bgt_info

boost_enabled = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status", methods=["GET"])
def status():
    return jsonify(get_bgt_info())

@app.route("/toggle_boost", methods=["POST"])
def toggle_boost():
    global boost_enabled
    boost_enabled = not boost_enabled
    return jsonify({"boost_enabled": boost_enabled})
