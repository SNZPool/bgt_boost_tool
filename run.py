import threading
import time
import logging
from flask import Flask, jsonify, render_template, request
from app.contracts import get_bgt_info, queue_boost, activate_boost, can_activate_boost
from app.config import Config

# Initialize Flask application
app = Flask(__name__)

# Configure logging
logging.basicConfig(filename=Config.LOG_FILE, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Boost control switch (enabled by default)
boost_enabled = True

@app.route("/")
def index():
    """Render Web UI"""
    return render_template("index.html")

@app.route("/status", methods=["GET"])
def status():
    """Get BGT statistics information"""
    return jsonify(get_bgt_info())

@app.route("/toggle_boost", methods=["POST"])
def toggle_boost():
    """Manual control for Boost switch"""
    global boost_enabled
    boost_enabled = not boost_enabled
    return jsonify({"boost_enabled": boost_enabled})

def run_flask():
    """Start Flask server"""
    app.run(host="0.0.0.0", port=Config.PORT, debug=False, use_reloader=False)

def boost_loop():
    """Main Boost automation loop"""
    global boost_enabled
    while True:
        if boost_enabled:
            bgt_info = get_bgt_info()
            queued_balance = bgt_info["queued_balance"]
            free_balance = bgt_info["free_balance"]

            # 1. Execute Queue Boost (only when Queue is empty)
            if queued_balance == 0 and free_balance > 0:
                tx_hash = queue_boost()
                if tx_hash:
                    print("✅ queue_boost", tx_hash.hex(), flush=True)
                    logging.info(f"✅ Queued Boost: {tx_hash.hex()}")

            # 2. Execute Activate Boost when conditions are met
            if can_activate_boost():
                tx_hash = activate_boost()
                if tx_hash:
                    print("✅ activate_boost", tx_hash.hex(), flush=True)
                    logging.info(f"✅ Activated Boost: {tx_hash.hex()}")

        # Check every Config.INTERVAL seconds
        time.sleep(Config.INTERVAL)

if __name__ == "__main__":
    # Start Flask thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start Boost task thread
    boost_thread = threading.Thread(target=boost_loop, daemon=True)
    boost_thread.start()

    # Keep main thread running
    while True:
        time.sleep(1)
