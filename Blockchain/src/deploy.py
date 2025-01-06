from web3 import Web3
from solcx import compile_files, install_solc, set_solc_version

install_solc("0.8.0")
set_solc_version("0.8.0")

holesky_url = "https://holesky.infura.io/v3/0aabcb786ad6420dba1750e2d705c786"
web3 = Web3(Web3.HTTPProvider(holesky_url))

if not web3.is_connected():
    raise ConnectionError("Failed to connect to the Holesky testnet")

DEPLOYER_ADDRESS = "0x0a5D25afFA75a0E4F7760E5c356a5047A768E02f"
DEPLOYER_PRIVATE_KEY = "303b03b38e725c037b6b2c02c0e9c2747aa74f3d653ae2bb28433ae6dfdb3d8a"

compiled_sol = compile_files(["TournamentContract.sol"])
contract_interface = compiled_sol["TournamentContract.sol:TournamentScores"]

def deploy_tournament_contract(tournament_name, player_names, player_scores):
    bytecode = contract_interface["bin"]
    abi = contract_interface["abi"]
    TournamentScores = web3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = web3.eth.get_transaction_count(DEPLOYER_ADDRESS)
    tx = TournamentScores.constructor(tournament_name, player_names, player_scores).build_transaction({
        "from": DEPLOYER_ADDRESS,
        "nonce": nonce,
        "gas": 4000000,
        "gasPrice": web3.to_wei("10", "gwei"),
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.contractAddress

if __name__ == "__main__":
    tournament_name = input("Enter the tournament name: ")
    player_names = ["test", "for", "transcendance"]
    player_scores = [2, 3, 4]
    contract_address = deploy_tournament_contract(tournament_name, player_names, player_scores)
    print(f"hash of new contract: {contract_address}")
