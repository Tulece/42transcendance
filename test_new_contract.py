from web3 import Web3
import json

# Setup web3
w3 = Web3(Web3.HTTPProvider('https://ethereum-holesky-rpc.publicnode.com'))
private_key = 'c3db1dae82c0bed3a4a3666e78def0ecc140ec099ce5dc00c611f35865c6a4dd'

# Load deployment info
with open('deployment_info.json') as f:
    deployment_info = json.load(f)
    contract_address = deployment_info['contract_address']

# Load contract ABI
with open('TournamentStorage.json') as f:
    contract_data = json.load(f)
    contract_abi = contract_data['abi']

# Create contract instance
contract = w3.eth.contract(address=contract_address, abi=contract_abi)
account = w3.eth.account.from_key(private_key)

print(f'Connected to network: {w3.is_connected()}')
print(f'Contract address: {contract_address}')
print(f'Account address: {account.address}')

def create_tournament():
    try:
        tournament_name = "First Tournament"
        winner_name = "John Doe"
        
        print(f'\nCreating tournament...')
        print(f'Name: {tournament_name}')
        print(f'Winner: {winner_name}')
        
        tx = contract.functions.addTournament(
            tournament_name,
            winner_name
        ).build_transaction({
            'from': account.address,
            'chainId': 17000,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })
        
        print('\nSending transaction...')
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        print(f'Transaction hash: {tx_hash.hex()}')
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt['status'] == 1:
            print('\nTournament created successfully!')
            
            # Try to read tournament data
            try:
                name, winner = contract.functions.getTournament(0).call()
                print('\nTournament details:')
                print(f'Name: {name}')
                print(f'Winner: {winner}')
            except Exception as e:
                print(f'Error reading tournament: {e}')
        else:
            print('\nTransaction failed')
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    create_tournament()
