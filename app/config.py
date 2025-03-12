import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    RPC_URL = os.getenv("RPC_URL")
    BGT_CONTRACT_ADDRESS = os.getenv("BGT_CONTRACT_ADDRESS")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    ADDRESS = os.getenv("ADDRESS")
    PUBKEY = os.getenv("PUBKEY")
    LOG_FILE = "logs/boost.log"
    PORT = int(os.getenv("PORT",5010))
    INTERVAL = int(os.getenv("INTERVAL",30))
