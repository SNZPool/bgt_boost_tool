from flask import Flask
from app.config import config

app = Flask(__name__)
app.config.from_object(config)
