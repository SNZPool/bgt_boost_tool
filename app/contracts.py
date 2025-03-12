import json
from web3 import Web3
from app.config import Config

def load_abi():
    """Load contract ABI from JSON file"""
    with open("app/bgt_abi.json", "r") as f:
        return json.load(f)

# Initialize Web3 connection
w3 = Web3(Web3.HTTPProvider(Config.RPC_URL))

# Load contract instance
BGT_ABI = load_abi()
bgt_contract = w3.eth.contract(address=Config.BGT_CONTRACT_ADDRESS, abi=BGT_ABI)

def get_bgt_info():
    """
    Query BGT balance information and convert to standard units
    Returns:
        dict: Contains total_balance, boost_balance, queued_balance, and free_balance
    """
    address = Config.ADDRESS
    decimals = 18  # BGT decimal places

    total_balance = bgt_contract.functions.balanceOf(address).call() / (10 ** decimals)
    boost_balance = bgt_contract.functions.boosts(address).call() / (10 ** decimals)
    queued_balance = bgt_contract.functions.queuedBoost(address).call() / (10 ** decimals)
    free_balance = total_balance - boost_balance - queued_balance

    return {
        "total_balance": round(total_balance, 4),
        "boost_balance": round(boost_balance, 4),
        "queued_balance": round(queued_balance, 4),
        "free_balance": round(free_balance, 4)
    }

def queue_boost():
    """
    Execute Queue Boost operation
    Returns:
        tx_hash: Transaction hash if successful, None if conditions not met
    """
    if get_bgt_info()["queued_balance"] > 0:
        return None
    
    free_balance = int(get_bgt_info()["free_balance"] * (10 ** 18))
    tx = bgt_contract.functions.queueBoost(Config.PUBKEY, free_balance).build_transaction({
        'from': Config.ADDRESS,
        'nonce': w3.eth.get_transaction_count(Config.ADDRESS),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    signed_tx = w3.eth.account.sign_transaction(tx, Config.PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return tx_hash

def can_activate_boost():
    """
    Check if Activate Boost conditions are met
    Returns:
        bool: True if conditions are met, False otherwise
    """
    address = Config.ADDRESS
    pubkey = Config.PUBKEY

    # Get the block number when queueBoost was entered
    queued_boost = bgt_contract.functions.boostedQueue(address, pubkey).call()
    block_number_last = queued_boost[0]  # Get blockNumberLast
    amount = queued_boost[1]  # Get queuedBoost BGT amount

    # Return False if no Queue Boost balance
    if amount == 0:
        return False

    # Check current block number
    current_block = w3.eth.block_number
    activate_boost_delay = bgt_contract.functions.activateBoostDelay().call()

    # Check if waiting time requirement is met
    print("Waiting ", activate_boost_delay-current_block+block_number_last, " to activate queued BGT.", flush=True)
    return current_block - block_number_last > activate_boost_delay

def activate_boost():
    """
    Execute Activate Boost operation if conditions are met
    Returns:
        tx_hash: Transaction hash if successful, None if conditions not met
    """
    if not can_activate_boost():
        print("⚠️  Activation conditions not met, skipping Activate Boost", flush=True)
        return None

    tx = bgt_contract.functions.activateBoost(Config.ADDRESS, Config.PUBKEY).build_transaction({
        'from': Config.ADDRESS,
        'nonce': w3.eth.get_transaction_count(Config.ADDRESS),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    signed_tx = w3.eth.account.sign_transaction(tx, Config.PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return tx_hash
