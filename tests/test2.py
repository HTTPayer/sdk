"""
// Copyright (c) 2025 HTTPayer Inc. under ChainSettle Inc. All rights reserved.
// Licensed under the HTTPayer SDK License – see LICENSE.txt.
"""

from flask import Flask, request, jsonify, make_response
from httpayer.gate import X402Gate
import os
from dotenv import load_dotenv
from python_viem import get_network_by_chain_id
from web3 import Web3

load_dotenv()

current_dir = os.getcwd()

ERC20_ABI_PATH = os.path.join(current_dir, "tests", "abi", "erc20.json")
print(f'ERC20_ABI_PATH: {ERC20_ABI_PATH}')

with open(ERC20_ABI_PATH, 'r') as f:
    ERC20_ABI = f.read()

load_dotenv()

FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://x402.org")
PAY_TO_ADDRESS = os.getenv("PAY_TO_ADDRESS", None)
RPC_GATEWAY = os.getenv("RPC_GATEWAY", None)

if not PAY_TO_ADDRESS:
    raise ValueError("PAY_TO_ADDRESS must be set in the environment variables.")

if not RPC_GATEWAY:
    raise ValueError("RPC_GATEWAY must be set in the environment variables.")

chain_id = int(os.getenv("CHAIN_ID", "84532")) 
network = get_network_by_chain_id(chain_id)

print(f'Network: {network}')
print(f'FACILITATOR_URL: {FACILITATOR_URL}')
print(f'PAY_TO_ADDRESS: {PAY_TO_ADDRESS}')
print(f'RPC_GATEWAY: {RPC_GATEWAY}')

if network == 'avalanche-fuji':
    if FACILITATOR_URL == "https://x402.org":
        raise ValueError("FACILITATOR_URL must be set to a valid URL for Avalanche Fuji testnet.")
elif network == 'base-sepolia':
    if FACILITATOR_URL != "https://x402.org":
        FACILITATOR_URL = "https://x402.org"

w3 = Web3(Web3.HTTPProvider(RPC_GATEWAY))

USDC_MAP = {
    "avalanche-fuji": "0x5425890298aed601595a70ab815c96711a31bc65",
    "base-sepolia": "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    # Add more networks as desired
}

token_address = USDC_MAP.get(network)

token_contract = w3.to_checksum_address(token_address)
token = w3.eth.contract(address=token_contract, abi=ERC20_ABI)
name_onchain    = token.functions.name().call()
version_onchain = token.functions.version().call() 

extra = {"name": name_onchain, "version": version_onchain}

print(f'Network: {network}, extra: {extra}')

gate = X402Gate(
    pay_to=PAY_TO_ADDRESS,
    network=network,
    asset_address=token_address,
    max_amount=1000,
    asset_name=extra["name"],
    asset_version=extra["version"],
    facilitator_url=FACILITATOR_URL
)

def create_app():
    app = Flask(__name__)

    @app.route("/health")
    def health():
        return "OK", 200
    
    @app.route('/')
    def index():
        return "<h1>Weather Server</h1><p>Welcome to the Weather Server!</p>"

    @app.route("/weather")
    @gate.gate
    def weather():
        response = make_response(jsonify({"weather": "sunny", "temp": 75}))
        return response
    
    @app.route("/post-weather", methods=["POST"])
    @gate.gate
    def post_weather():
        data = request.json
        location = data.get("location", "default_location")
        print(f"Received weather request for location: {location}")
        # Simulate a weather response
        # In a real application, you would fetch actual weather data here
        # For demonstration, we return a static response
        response = make_response(jsonify({"weather": "sunny", "temp": 75, "location": location}))
        return response

    return app

if __name__ == "__main__":
    port = int(os.getenv("TEST_SERVER_PORT", 5035))
    print(f'Starting test2 on {port}...')
    app = create_app()
    app.run(host="0.0.0.0",port=port)