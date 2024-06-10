import subprocess
import json

def encrypt(public_key: str, plain: str)->str:
    plain_with_pubkey = json.dumps({"public_key": public_key,"plain": plain})
    encryption_command = "node src/encryptor.js".split()
    encryption_process = subprocess.run(encryption_command, input=plain_with_pubkey,text=True,capture_output=True)
    return encryption_process.stdout.split("\n")[1].strip()

def decrypt(private_key: str, encrypted: str)->str:
    crypted_with_key = json.dumps({"private_key": private_key,"payload": encrypted})
    #input(f"Decryptor Input: {crypted_with_key}") 
    decryption_command = "node src/decryptor.js".split()
    decryption_process = subprocess.run(decryption_command, input=crypted_with_key,text=True,capture_output=True)
    #input(f"Decyption output is {decryption_process.stdout}")
    return decryption_process.stdout.split("\n")[1].strip()

def sign(private_key: str, message: str)->str:
    message_with_key = json.dumps({"private_key": private_key,"payload": message})
    signing_command ="node src/signer.js".split()
    signing_process =subprocess.run(signing_command,capture_output=True,text=True,input=message_with_key)
    return signing_process.stdout.split("\n")[1].strip()

def private2public(private_key: str)->str:
    conversion_command = "node src/private2public.js".split()
    conversion_process=subprocess.run(conversion_command,capture_output=True, text=True, input=private_key)
    return conversion_process.stdout.split("\n")[1].strip()

def generate_keypair()->str:
    generator_command = "node src/generate.js".split()
    generator_process=subprocess.run(generator_command, capture_output=True, text=True)
    return generator_process.stdout.split("\n")[1].strip()