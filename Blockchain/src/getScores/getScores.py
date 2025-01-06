from web3 import Web3
from solcx import compile_files, install_solc, set_solc_version

install_solc("0.8.0")
set_solc_version("0.8.0")

holesky_url = "https://holesky.infura.io/v3/0aabcb786ad6420dba1750e2d705c786"
web3 = Web3(Web3.HTTPProvider(holesky_url))

if not web3.is_connected():
    raise ConnectionError("error to login testnet holesky")

compiled_sol = compile_files(["../TournamentContract.sol"])
contract_interface = compiled_sol["../TournamentContract.sol:TournamentScores"]
abi = contract_interface["abi"]

def get_tournament_info(contract_address):
    contract = web3.eth.contract(address=contract_address, abi=abi)
    tournament_name = contract.functions.tournamentName().call()
    admin_address = contract.functions.admin().call()
    print(f"Tournament name: {tournament_name}")
    print(f"Creator hash: {admin_address}")

def get_players(contract_address):
    contract = web3.eth.contract(address=contract_address, abi=abi)
    players_count = contract.functions.getPlayersCount().call()
    print(f"Total players: {players_count}")
    for index in range(players_count):
        name, score = contract.functions.getPlayer(index).call()
        print(f"Player {index + 1}: Name = {name}, Score = {score}")

if __name__ == "__main__":
    contract_address = input("Enter the deployed contract address: ")
    print("\nTournament information:")
    get_tournament_info(contract_address)
    print("\nPlayers information:")
    get_players(contract_address)