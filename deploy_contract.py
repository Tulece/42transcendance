from web3 import Web3
import json
import os
from solcx import compile_source, install_solc

# Install specific solc version (adjust version if needed)
install_solc('0.8.0')

# Contract source code
contract_source = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TournamentStorage {
    struct Tournament {
        string name;
        string winner;
    }
    
    Tournament[] public tournaments;
    
    event TournamentCreated(uint256 indexed tournamentId, string name, string winner);
    
    function addTournament(string memory _name, string memory _winner) public returns (uint256) {
        Tournament memory newTournament = Tournament({
            name: _name,
            winner: _winner
        });
        
        tournaments.push(newTournament);
        uint256 tournamentId = tournaments.length - 1;
        
        emit TournamentCreated(tournamentId, _name, _winner);
        return tournamentId;
    }
    
    function getTournament(uint256 _id) public view returns (string memory, string memory) {
        require(_id < tournaments.length, "Tournament does not exist");
        Tournament memory tournament = tournaments[_id];
        return (tournament.name, tournament.winner);
    }
}
'''

print('Compiling contract...')
compiled_sol = compile_source(
    contract_source,
    output_values=['abi', 'bin'],
    solc_version='0.8.0'
)

contract_id, contract_interface = compiled_sol.popitem()
bytecode = contract_interface['bin']
abi = contract_interface['abi']

# Save contract data
contract_data = {
    'abi': abi,
    'bytecode': bytecode
}

with open('TournamentStorage.json', 'w') as f:
    json.dump(contract_data, f, indent=2)

print('Contract compiled and saved to TournamentStorage.json')

# Setup web3
w3 = Web3(Web3.HTTPProvider('https://ethereum-holesky-rpc.publicnode.com'))
private_key = 'c3db1dae82c0bed3a4a3666e78def0ecc140ec099ce5dc00c611f35865c6a4dd'
account = w3.eth.account.from_key(private_key)

print(f'\nAccount address: {account.address}')
print(f'Connected to network: {w3.is_connected()}')
print(f'Chain ID: {w3.eth.chain_id}')
print(f'Current balance: {w3.eth.get_balance(account.address)} wei')

# Deploy contract
print('\nPreparing contract deployment...')
contract = w3.eth.contract(abi=abi, bytecode=bytecode)

# Build deployment transaction
transaction = contract.constructor().build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 3000000,
    'gasPrice': w3.eth.gas_price
})

# Sign and send transaction
print('Signing and sending deployment transaction...')
signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
print(f'Deployment transaction sent: {tx_hash.hex()}')

# Wait for transaction receipt
print('\nWaiting for deployment transaction to be mined...')
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
contract_address = tx_receipt.contractAddress

print(f'\nContract deployed successfully!')
print(f'Contract address: {contract_address}')
print(f'Transaction hash: {tx_hash.hex()}')
print(f'Gas used: {tx_receipt["gasUsed"]}')
print(f'Block number: {tx_receipt["blockNumber"]}')

# Save deployment info
deployment_info = {
    'contract_address': contract_address,
    'transaction_hash': tx_hash.hex(),
    'block_number': tx_receipt['blockNumber'],
    'deployer_address': account.address
}

with open('deployment_info.json', 'w') as f:
    json.dump(deployment_info, f, indent=2)

print('\nDeployment information saved to deployment_info.json')
