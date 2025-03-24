import os
os.environ['CONTRACT_PRIVATE_KEY'] = 'c3db1dae82c0bed3a4a3666e78def0ecc140ec099ce5dc00c611f35865c6a4dd'
os.environ['TOURNAMENT_CONTRACT_ADDRESS'] = '0x8e923EfD5682916F432Cab3eC756bF7247415062'

from web3 import Web3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

w3 = Web3(Web3.HTTPProvider('https://ethereum-holesky-rpc.publicnode.com'))
contract_address = os.getenv('TOURNAMENT_CONTRACT_ADDRESS')

# Load ABI
with open('django/pong/blockchain/TournamentStorage.json') as f:
    contract_abi = json.load(f)['abi']

contract = w3.eth.contract(address=contract_address, abi=contract_abi)
private_key = os.getenv('CONTRACT_PRIVATE_KEY')
account = w3.eth.account.from_key(private_key)

def test_store_tournament():
    try:
        tournament_name = "Test Tournament"
        winner_address = "0x0000000000000000000000000000000000000000"
        full_name = f"{tournament_name} - Winner: Test Winner"

        print(f"Connected to network: {w3.is_connected()}")
        print(f"Using account: {account.address}")
        print(f"Account balance: {w3.eth.get_balance(account.address)} wei")
        print(f"Contract address: {contract_address}")
        
        print("\nBuilding transaction...")
        tx = contract.functions.addTournament(
            full_name,
            winner_address
        ).build_transaction({
            'from': account.address,
            'chainId': 17000,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })
        
        print("Transaction built successfully")
        
        print("\nSigning and sending transaction...")
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        print(f"Transaction sent: {tx_hash.hex()}")
        
        print("\nWaiting for transaction receipt...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction mined in block: {receipt['blockNumber']}")
        
        print("\nProcessing logs:")
        for log in receipt['logs']:
            print(f"\nRaw log: {log}")
            try:
                decoded = contract.events.TournamentCreated().process_log(log)
                print(f"Decoded event: {decoded}")
                tournament_id = decoded['args']['tournamentId']
                print(f"\nTournament created with ID: {tournament_id}")
                
                # Try to get the tournament info
                name, winner = contract.functions.getTournament(tournament_id).call()
                print(f"\nTournament info from blockchain:")
                print(f"Name: {name}")
                print(f"Winner address: {winner}")
            except Exception as e:
                print(f"Failed to decode log: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_store_tournament()

