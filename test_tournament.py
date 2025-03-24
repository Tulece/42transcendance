from web3 import Web3
import json
import os

# Setup web3
w3 = Web3(Web3.HTTPProvider('https://ethereum-holesky-rpc.publicnode.com'))
contract_address = '0x8e923EfD5682916F432Cab3eC756bF7247415062'
private_key = 'c3db1dae82c0bed3a4a3666e78def0ecc140ec099ce5dc00c611f35865c6a4dd'

print(f'Connected to network: {w3.is_connected()}')

# Load contract details
with open('django/pong/blockchain/TournamentStorage.json') as f:
    data = json.load(f)
    contract_abi = data['abi']
    bytecode = data.get('bytecode', '')
    print(f'\nBytecode from JSON length: {len(bytecode)}')

# Create contract instance
contract = w3.eth.contract(address=contract_address, abi=contract_abi)
account = w3.eth.account.from_key(private_key)

print(f'\nContract address: {contract_address}')
print(f'Our account address: {account.address}')

# Get deployment transaction
print('\nLooking for contract deployment transaction...')
code = w3.eth.get_code(contract_address)
print(f'Deployed bytecode length: {len(code)}')

# Get creation transaction
try:
    block = w3.eth.get_transaction_by_block(3548740, 0)  # From a previous transaction
    print(f'\nBlock creator: {block["from"] if block else "Unknown"}')
    print(f'Block miner: {block["miner"] if "miner" in block else "Unknown"}')
except Exception as e:
    print(f'Error getting block: {e}')

# Try to create tournament with more details about the transaction
def create_tournament():
    try:
        tournament_name = 'Test Tournament'
        winner_name = 'Test Winner'
        
        print('\nPreparing transaction...')
        print(f'Tournament Name: {tournament_name}')
        print(f'Winner Name: {winner_name}')
        
        # Create transaction
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price
        
        print(f'\nAccount nonce: {nonce}')
        print(f'Gas price: {gas_price}')
        
        tx = contract.functions.addTournament(
            tournament_name,
            winner_name
        ).build_transaction({
            'from': account.address,
            'chainId': 17000,
            'gas': 300000,  # Increased gas limit
            'gasPrice': gas_price,
            'nonce': nonce,
        })
        
        # Get function selector
        fn_selector = tx['data'][:10]
        print(f'Function selector: {fn_selector}')
        
        # Sign and send
        print('\nSigning and sending transaction...')
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        print(f'Transaction hash: {tx_hash.hex()}')
        
        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        success = receipt['status'] == 1
        print(f'\nTransaction status: {"Success" if success else "Failed"}')
        print(f'Gas used: {receipt["gasUsed"]}')
        print(f'Block number: {receipt["blockNumber"]}')
        
        if not success:
            # Try to get revert reason
            try:
                w3.eth.call({
                    'from': account.address,
                    'to': contract_address,
                    'data': tx['data'],
                    'value': 0,
                    'gas': 300000,
                    'gasPrice': gas_price
                })
            except Exception as e:
                reason = str(e)
                if 'revert reason' in reason.lower():
                    print(f'\nRevert reason: {reason}')
                else:
                    print(f'\nTransaction failed without clear reason: {e}')
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    create_tournament()
