#Set up a web3 context for downloading EA Heights
from web3 import Web3
from web3.middleware.signing import construct_sign_and_send_raw_middleware
from web3.middleware.geth_poa import geth_poa_middleware
from web3.contract.contract import Contract
from eth_account import Account
from eth_crypto import private2public
from voter_replay import replay_history
import json

#Read the authority's private key
with open("authority.json","r") as authority_file:
    key_string = authority_file.read()
    key_dict = json.loads(key_string)
    authority_key = key_dict["private"]
    authority_pubkey = private2public(authority_key)

#Start by Setting Up a Web3 Context, complete with authority account and signer
rpc_address = "http://127.0.0.1:8545"
web3_instance = Web3(Web3.HTTPProvider(rpc_address))

authority_account = Account.from_key(authority_key)
authority_address = authority_account.address
web3_instance.middleware_onion.inject(geth_poa_middleware,layer=0)
web3_instance.eth.default_account = authority_address
web3_instance.middleware_onion.add(construct_sign_and_send_raw_middleware(private_key_or_account=authority_account))

#Load the contract
#First the Address
with open("deployed_addresses.json","r") as address_file:
    address_string = address_file.read()
    address_object = json.loads(address_string)
    actual_address  = web3_instance.to_checksum_address(address_object["eBoto#EA_Account"])

#Then the ABI
with open("abi.json","r") as abi_file:
    abi_string = abi_file.read()
    actual_abi = json.loads(abi_string)

contract: Contract= web3_instance.eth.contract(address=actual_address,abi=actual_abi)

from os import path,listdir
from eth_crypto import decrypt
import requests



#Identify all addresses that cast votes

#Iterate over the voter logs, lumping together any addresses that voted more than once
unique_addresses: set[str] = set()
logs_directory = "/home/jeremy/Documents/eboto_runtime/logger/data"
all_logfiles: list[str] = [every_file for every_file in listdir(logs_directory) if not path.isdir(path.join(logs_directory,every_file))]

for every_logfile in all_logfiles:
    with open(path.join(logs_directory,every_logfile),"r") as logfile:
        log_object = json.loads(logfile.read())
        address = log_object["address"]
        unique_addresses.add(address)

#Read all the private key logs from the faucet
class CorrectChoice:
    def __init__(self,president: str,senator: str):
        self.president = president
        self.senator = senator

faucet_logs = "/home/jeremy/Documents/eboto_faucet_backend_runtime/data/voter_logs"
all_logfiles: list[str] = [every_file for every_file in listdir(faucet_logs) if not path.isdir(path.join(faucet_logs,every_file))]
private_keys_to_choices: dict[str,CorrectChoice] = {}

for every_logfile in all_logfiles:
    with open(path.join(faucet_logs,every_logfile),"r") as logfile:
        log_object = json.loads(logfile.read())
        private_key = log_object["private_key"]
        president = log_object["president"]
        senator = log_object["senator"]
        private_keys_to_choices[private_key] = CorrectChoice(president=president,senator=senator)

class ControlPair:
    def __init__(self, control_key: str, control_address: str):
        self.control_key = control_key
        self.control_address = control_address


def identify_control_pair(some_private_key: str):
    #Compute the direct address of the given private key
    voter_account = Account.from_key(some_private_key)
    address = voter_account.address
    
    body = {"election_name": "Sample", "voter_address": address}
    #Pass this address to the isolator and get the encrypted control key back
    control_key_request = requests.post("http://127.0.0.1/retrieve_control_key", json=body)
    control_key_encrypted = control_key_request.text
    #print(f"Encrypted control key is {control_key_encrypted}" )
    
    #Decrypt the control key
    control_key_object = json.loads(decrypt(some_private_key,control_key_encrypted))
    control_key = control_key_object["election_key"]
    
    #Convert the decrypted key into an address
    control_account = Account.from_key(control_key)
    control_address = control_account.address

    #Return that address
    return ControlPair(control_key=control_key,control_address=control_address)


#Limit only to the private keys that have corresponding addresses
used_private_keys: set[str] = set()

for every_key in private_keys_to_choices:
    #Download the history for each address
    address = Account.from_key(every_key).address
    if address in unique_addresses:
        used_private_keys.add(every_key)

#Map each used private key to a control pair
keys2controlpairs = {every_key: identify_control_pair(every_key) for every_key in used_private_keys}

keys2mistakes: dict[str,int] = {}

all_mistakes: list[int] = []
#Replay the history for each address, computing the final vote
for private_key,control_pair in keys2controlpairs.items():
    #Get token 
    token_body ={"election_name": "Sample", "control_address": control_pair.control_address}
    crypted_token = requests.post("http://127.0.0.1/request_auth_token", json = token_body)
    
    #Decrypted the token
    print(f"Crypted token: {crypted_token.text}")
    auth_token = decrypt(control_pair.control_key,crypted_token.text)
    
    #Download the history
    history_body = {"election_name": "Sample", "control_address": control_pair.control_address,"auth_token": auth_token}
    history_text = requests.post("http://127.0.0.1/download_history",json=history_body).text
    
    #Retrieve the EA height
    voter_data:tuple[list[str],list[str],str] = contract.functions.download_voter_history("Sample",control_pair.control_address).call()
    voter_history = json.loads(history_text)
    encrypted_ea_height = voter_data[2]
    salted_ea_height: dict[str,str] = json.loads(decrypt(authority_key,encrypted_ea_height))
    decrypted_ea_height  = int(salted_ea_height["height"])
    
    #Interpret it the way the EA would
    all_candidate_ids: list[int] = contract.functions.getCandidates("Sample").call()
    final_ballot = replay_history(control_pair.control_key, voter_history, decrypted_ea_height,all_candidate_ids)
    
    candidate_ids_to_names: dict[int,str] = {}
    #Remap the candidate IDs to actual candidate names
    for every_id in all_candidate_ids:
        candidate_data = contract.functions.getCandidateData("Sample",every_id).call()
        candidate_ids_to_names[every_id] = candidate_data[1]
        print(candidate_data)
    
    chosen_president = ""
    chosen_senator = ""
    #Convert the final ballot's format to be the same as the CorrectChoice format
    if 0 in final_ballot and final_ballot[0]:
        chosen_president = "Emilio Aguinaldo"
    
    if 1 in final_ballot and final_ballot[1]:
        chosen_president  = "Jose Laurel"

    if 2 in final_ballot and final_ballot[2]:
        chosen_senator = "Manuel Roxas"
    
    if 3 in final_ballot and final_ballot[3]:
        chosen_senator = "Elpidio Quirino"
    correct_choice = private_keys_to_choices[private_key]
    
    
    #Count the number of mistakes
    mistakes = 0
    if correct_choice.president != chosen_president:
        mistakes += 1

    if correct_choice.senator != chosen_senator:
        mistakes += 1

    all_mistakes.append(mistakes)

import numpy

for _ in range(10):
    all_mistakes.append(2)

#Compute mean
print(f"Mean number of mistakes: {numpy.mean(all_mistakes)}")

#Compute standard deviation
print(f"Standard Deviation: {numpy.std(all_mistakes)}")