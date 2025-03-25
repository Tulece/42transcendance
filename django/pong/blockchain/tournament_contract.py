from web3 import Web3
import os
import json
import logging

logger = logging.getLogger(__name__)

def get_contract():
    w3 = Web3(Web3.HTTPProvider("https://ethereum-holesky-rpc.publicnode.com"))
    contract_address = os.getenv("TOURNAMENT_CONTRACT_ADDRESS")
    
    abi_path = os.path.join(os.path.dirname(__file__), "TournamentStorage.json")
    with open(abi_path) as f:
        contract_abi = json.load(f)["abi"]
    
    return w3, w3.eth.contract(address=contract_address, abi=contract_abi)

def store_tournament_result(tournament_name, winner_name):
    try:
        w3, contract = get_contract()
        private_key = os.getenv("CONTRACT_PRIVATE_KEY")
        if not private_key:
            raise Exception("CONTRACT_PRIVATE_KEY not found")
        
        private_key = private_key.rstrip("%")
        
        account = w3.eth.account.from_key(private_key)
        
        winner_address = "0x0000000000000000000000000000000000000000"
        full_name = f"{tournament_name} - Winner: {winner_name}"
        
        tx = contract.functions.addTournament(
            full_name,
            winner_address
        ).build_transaction({
            "from": account.address,
            "chainId": 17000,
            "gas": 2000000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(account.address),
        })
        
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        for log in receipt["logs"]:
            try:
                decoded = contract.events.TournamentCreated().process_log(log)
                tournament_id = decoded["args"]["tournamentId"]
                logger.info(f"Tournament created with ID: {tournament_id}")
                return True, tournament_id
            except:
                continue
        
        raise Exception("Tournament ID not found in logs")
        
    except Exception as e:
        logger.error(f"Error storing tournament: {e}")
        return False, str(e)

def get_tournament_info(tournament_id):
    try:
        w3, contract = get_contract()
        name, _ = contract.functions.getTournament(tournament_id).call()
        
        if " - Winner: " in name:
            tournament_name, winner = name.split(" - Winner: ")
        else:
            tournament_name, winner = name, "Unknown"
        
        return tournament_name, winner
    except Exception as e:
        logger.error(f"Error getting tournament: {e}")
        return None, None

