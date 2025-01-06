from web3 import Account

account = Account.create()

print("Adresse Ethereum :", account.address)
print("Clé privée :", account.key.hex())
