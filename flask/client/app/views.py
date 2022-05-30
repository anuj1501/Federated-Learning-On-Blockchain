from http import client
from multiprocessing import synchronize
from multiprocessing.connection import Client
from flask import  request, flash, redirect, url_for,send_file,make_response
from app import *
from app.model import Contributor,Organizer,User
import ipfshttpclient
import os, time, requests, shutil
import pandas as pd
from solcx import compile_files, link_code, compile_source
from ai.ai import calculate_initial_accuracy,ClientUpdate,FederatedAveraging
import re

def base_directories(contract_add):
    if not os.path.exists(app.config['UPLOAD_FOLDER'] + contract_add):
        os.mkdir(app.config['UPLOAD_FOLDER'] + contract_add)
    if not os.path.exists(app.config['BASE_DATA_FOLDER'] + contract_add):
        os.mkdir(app.config['BASE_DATA_FOLDER'] + contract_add)
    if not os.path.exists(app.config['MODEL_FOLDER'] + contract_add):
        os.mkdir(app.config['MODEL_FOLDER'] + contract_add) 

def upload_file_sync(filepath):
    with app.app_context():
        print("Started")

        while not os.path.exists(filepath):
            print("Waiting for file to be visible")
            time.sleep(1)
            if os.path.isfile(filepath):
                print("Now the file is available")
            else:
                raise ValueError("%s isn't a file!" % filepath)
    print("Finished")
    return True
    

@app.route('/submit_contract',methods=['GET','POST'])
def submit_contract():

    if request.method == 'POST':        
        with open(app.config['BASE_PATH'] + "contracts/LearningContract.sol","r") as f:
            contract_src = str(f.read())
        contract_interface = compile_source(
            contract_src,
            output_values=["abi", "bin"],
            solc_version="0.5.0"
        )["<stdin>:LearningContract"]

        contract = server.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bin']
        )
        print ("Sender's address", session.get('account'), "\n")
        # account = "0x35ab83137e14FBeFE4b2c081F23a89D18cf510F5"
        print(request.form)
        account = request.form["userID"]
        print("account = ",account)
        # Submit the transaction that deploys the contract
        tx_hash = contract.constructor().transact({'from':account})
        print ("Tx submitted: ", server.toHex(tx_hash))

        # Wait for the transaction to be mined, and get the transaction receipt
        tx_receipt = server.eth.waitForTransactionReceipt(tx_hash)

        abi = contract_interface['abi']
        contract_address = tx_receipt.contractAddress

        #create all the base directories
        base_directories(str(contract_address))

        base_account_path = app.config['BASE_DATA_FOLDER'] + contract_address

        validation_data_upload_file = None
        if 'validationDataFile' not in request.files:
            print("Validation data not received")
        else:
            validation_data_upload_file = request.files['validationDataFile']
        validation_data_upload_file.save(base_account_path + '/' + validation_data_upload_file.filename)

        model_upload_file = None
        if 'modelFile' not in request.files:
            print("Model File not received")
        else:
            model_upload_file = request.files['modelFile']
        model_upload_file.save(base_account_path + '/' + model_upload_file.filename)

        reward = request.form['reward']
        model_description = request.form['modelDescription']
        contract_name = request.form['contractName']
        print(base_account_path + '/' + model_upload_file.filename)
        base_acc = calculate_initial_accuracy(validation_path=base_account_path + '/' + validation_data_upload_file.filename,model_path=base_account_path + '/' + model_upload_file.filename)
        
        new_organizer = Organizer(
            wallet_address = str(account),
            validation_data_path = base_account_path + '/' + validation_data_upload_file.filename,
            base_model_path = app.config['MODEL_FOLDER'] + model_upload_file.filename,
            contract_name = str(contract_name),
            model_description = str(model_description),
            reward = int(reward),
            base_accuracy = base_acc,
            contract_address = str(tx_receipt.contractAddress)
        )

        db.session.add(new_organizer)
        db.session.commit() 
        print("deployed the contract successfully")
        return {"base_accuracy" : base_acc, "contract_address": tx_receipt.contractAddress, "contract_organizer": str(account), "reward": int(reward)}


@app.route('/add_data_from_client', methods=['GET', 'POST'])
@cross_origin()
def add_data_from_client():
    if request.method == 'POST':
        upload_file = None        
        upload_file = request.files['dataFile']
        if upload_file and allowed_file(upload_file.filename):
            acct_address = request.form["userID"]
            contract_address = request.form["contractAddress"]

            base_contract_path = app.config['UPLOAD_FOLDER'] + contract_address

            if not os.path.exists(base_contract_path + '/' + acct_address):
                os.mkdir(base_contract_path + '/' + acct_address)
            client_folder_path = base_contract_path + '/' + acct_address
            
            upload_file.save(client_folder_path + "/" + upload_file.filename)
            api = ipfshttpclient.connect("/ip4/127.0.0.1/tcp/5001/http")    
            res = api.add(client_folder_path + "/" + upload_file.filename)        
            ipfsHash = res['Hash']
            datapath = client_folder_path + "/" + upload_file.filename
            print("Uploaded file successfully")

            abi = [{'constant': True, 'inputs': [], 'name': 'getCheckPointIpfsHash', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'fileName', 'type': 'string'}, {'name': 'ipfsHash', 'type': 
            'string'}], 'name': 'addFile', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'ipfsHash', 'type': 'string'}], 'name': 'setCheckPointIpfsHash', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'getModelIpfsHash', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'index', 'type': 'uint256'}], 'name': 'getRegisteredUsers', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'getRegisteredUsers', 'outputs': [{'name': '', 'type': 'address[]'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': '', 'type': 'uint256'}], 'name': 'registeredUsers', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 
            'user', 'type': 'address'}], 'name': 'getIpfsHashForUser', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'getIpfsHashForCheckpoint', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'w', 'type': 'address'}], 'name': 'transferReward', 'outputs': [], 'payable': True, 'stateMutability': 'payable', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'owner', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'checkpointIpfsMap', 'outputs': [{'name': '', 'type': 'uint256'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': '', 'type': 'address'}], 'name': 'filenames', 'outputs': [{'name': 'fileName', 'type': 'string'}, {'name': 'ipfsHash', 'type': 'string'}, {'name': 'modelHash', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'user', 'type': 'address'}], 'name': 'getFileNameForUser', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'modelIpfsHash', 'type': 'string'}], 'name': 'addModelFile', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'constructor'}]
            
            
            contract = server.eth.contract(
                address=request.form["contractAddress"],
                abi=abi,
                )
            print(contract.functions)
            if acct_address is not None:
                tx_hash = contract.functions.addFile(datapath,ipfsHash).transact({'from':acct_address})
                receipt = server.eth.waitForTransactionReceipt(tx_hash)
                print("Gas Used ", receipt.gasUsed)
            else:
                flash('No account was chosen')


            new_client = Contributor(
            wallet_address = str(acct_address),
            data_path = str(datapath),
            model_path = "",
            accuracy = 0,
            contract_address = request.form["contractAddress"]
            )
            db.session.add(new_client)
            db.session.commit()
   
    return {"message" : "upload_successful", "data_file_uploaded": 1}

@app.route('/model_pull', methods=['POST'])
@cross_origin()
def model_pull():

    abi = [{'constant': True, 'inputs': [], 'name': 'getCheckPointIpfsHash', 'outputs': [{'name': '', 'type': 'string'}], 'payable': 
            False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'fileName', 'type': 'string'}, {'name': 'ipfsHash', 'type': 'string'}], 'name': 'addFile', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'ipfsHash', 'type': 'string'}], 'name': 'setCheckPointIpfsHash', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'getModelIpfsHash', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'index', 'type': 'uint256'}], 'name': 'getRegisteredUsers', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': 
            True, 'inputs': [], 'name': 'getRegisteredUsers', 'outputs': [{'name': '', 'type': 'address[]'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': '', 'type': 'uint256'}], 'name': 'registeredUsers', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'user', 'type': 'address'}], 'name': 'getIpfsHashForUser', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'getIpfsHashForCheckpoint', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'w', 'type': 'address'}], 'name': 'transferReward', 'outputs': [], 'payable': True, 'stateMutability': 'payable', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'owner', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'checkpointIpfsMap', 'outputs': [{'name': '', 'type': 'uint256'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': '', 'type': 'address'}], 'name': 'filenames', 'outputs': [{'name': 'fileName', 'type': 'string'}, {'name': 'ipfsHash', 'type': 'string'}, {'name': 'modelHash', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'user', 
            'type': 'address'}], 'name': 'getFileNameForUser', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'modelIpfsHash', 'type': 'string'}], 'name': 'addModelFile', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'constructor'}]
    contract_address = request.form["contractAddress"]
    print(request.form)
    account = request.form["userID"]
    contract = server.eth.contract(
                address=request.form["contractAddress"],
                abi=abi
                )
    
    account = request.form["userID"]
    organizer = Organizer.query.filter_by(contract_address=contract_address).order_by(Organizer.oid.desc()).first()
    users = contract.functions.getRegisteredUsers().call()
    # users = Contributor.query.filter_by(contract_address=contract_address).all()    
    print(users)
    base_accuracy = organizer.base_accuracy
    best_model_paths = list()
    map_of_address_to_reward = dict()
    best_accuracy_improvements = dict()
    total_improvement = 0
    print("users = ",users)
    for user in users:
        contributor = Contributor.query.filter_by(wallet_address=user).order_by(Contributor.cid.desc()).first()
        if contributor.accuracy > base_accuracy:
            best_model_paths.append(contributor.model_path)
            best_accuracy_improvements[contributor.wallet_address] = (contributor.accuracy - base_accuracy)
            total_improvement += (contributor.accuracy - base_accuracy)

    print("model paths = ",best_model_paths)
    print()
    federated_accuracy = FederatedAveraging(best_model_paths, organizer.base_model_path)
    print("federated_learning_successful")
    reward = organizer.reward
    for add,acc in best_accuracy_improvements.items():
        final_reward_value = (acc / total_improvement) * reward
        map_of_address_to_reward[add] = final_reward_value

    print("map of address and reward: ", map_of_address_to_reward)
    for add,rew in map_of_address_to_reward.items():

        nonce = server.eth.getTransactionCount(account)
        tx_hash = contract.functions.transferReward(add).transact({
            'nonce':nonce,
            'from': account,
            'to': add,
            'value': server.toWei(rew,'ether')
        })
        receipt = server.eth.waitForTransactionReceipt(tx_hash)
        print("Gas Used ", receipt.gasUsed)

        contributor = Contributor.query.filter_by(wallet_address=add)
        
        contributor.reward_earned = rew
        db.session.commit()
    
    # Contributor.query.filter_by(contract_address=contract_address).delete(synchronize_session='fetch')
    # Organizer.query.filter_by(contract_address=contract_address).delete(synchronize_session='fetch')
    # db.session.commit()

    response = make_response(send_file(organizer.base_model_path, as_attachment=True))
    response.headers["federated_accuracy"] = federated_accuracy

    return response

@app.route('/get_updated_model')
@cross_origin()
def get_updated_model():
    filename = app.config['MODEL_FOLDER'] + "model.h5"
    return send_file(filename)

@app.route('/get_contributor_balance', methods=['POST'])
@cross_origin()
def get_contributor_balance():
    account = request.form["userID"]
    c = Contributor.query.filter_by(wallet_address=account)
    return {"balance" : c.reward_earned}

@app.route('/get_balance', methods=['GET','POST'])
@cross_origin()
def get_organizer_balance():
    account = request.args.get("userID")
    print(account)
    balance = server.eth.getBalance(account)
    print(balance)
    balance = (balance / (10**18))
    print("balance = ",balance)
    return {"balance" : balance}

@app.route('/train', methods=['POST'])
@cross_origin()
def train():
    account = request.form["userID"]
    contributor = Contributor.query.filter_by(wallet_address=account).order_by(Contributor.cid.desc()).first()

    if len(contributor.data_path) == 0:
        return {"data_file_uploaded": 0}
    else:    
        abi = [{'constant': True, 'inputs': [], 'name': 'getCheckPointIpfsHash', 'outputs': [{'name': '', 'type': 'string'}], 'payable': 
                False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'fileName', 'type': 'string'}, {'name': 'ipfsHash', 'type': 'string'}], 'name': 'addFile', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'ipfsHash', 'type': 'string'}], 'name': 'setCheckPointIpfsHash', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'getModelIpfsHash', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'index', 'type': 'uint256'}], 'name': 'getRegisteredUsers', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': 
                True, 'inputs': [], 'name': 'getRegisteredUsers', 'outputs': [{'name': '', 'type': 'address[]'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': '', 'type': 'uint256'}], 'name': 'registeredUsers', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'user', 'type': 'address'}], 'name': 'getIpfsHashForUser', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'getIpfsHashForCheckpoint', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'w', 'type': 'address'}], 'name': 'transferReward', 'outputs': [], 'payable': True, 'stateMutability': 'payable', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'owner', 'outputs': [{'name': '', 'type': 'address'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'checkpointIpfsMap', 'outputs': [{'name': '', 'type': 'uint256'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': '', 'type': 'address'}], 'name': 'filenames', 'outputs': [{'name': 'fileName', 'type': 'string'}, {'name': 'ipfsHash', 'type': 'string'}, {'name': 'modelHash', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'user', 
                'type': 'address'}], 'name': 'getFileNameForUser', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'modelIpfsHash', 'type': 'string'}], 'name': 'addModelFile', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'constructor'}]
        
        contract_address = request.form["contractAddress"]
        contract = server.eth.contract(
                    address=request.form["contractAddress"],
                    abi=abi,
                    )

        model_folder_path = app.config['MODEL_FOLDER'] + contract_address

        accuracy,model_saved_path = ClientUpdate(model_folder_path= model_folder_path,data_path= contributor.data_path,contract_address= contract_address,client_address=account, base_data_path = app.config['BASE_DATA_FOLDER'])
        contributor.model_path = model_saved_path
        contributor.accuracy = accuracy
        db.session.commit()

        api = ipfshttpclient.connect("/ip4/127.0.0.1/tcp/5001/http")
        res = api.add(model_saved_path)
        modelHash = res['Hash']

        tx_hash = contract.functions.addModelFile(modelHash).transact(
            {'from': account})
        receipt = server.eth.waitForTransactionReceipt(tx_hash)
        print("Gas Used ", receipt.gasUsed)
        return {"accuracy":accuracy}

@app.route('/get_accuracies_and_submissions', methods=['POST','GET'])
@cross_origin()
def get_accuracies():

    contract_address = ""
    temp = request.get_json()
    print(temp)
    account = temp["params"]["userID"]
    print(account)
    contract_address = temp["params"]["contract_address"]
    o = Organizer.query.filter_by(wallet_address=account).first()
    base_accuracy = o.base_accuracy

    if Contributor.query.filter_by(accuracy = 0).all() is not None:
        Contributor.query.filter_by(accuracy = 0).delete()
        db.session.commit()

    accuracies = [c.accuracy for c in Contributor.query.filter_by(contract_address=contract_address)]
    accuracy_response = list()
    accuracy_response.append({"x":0,"y":base_accuracy})
    count = 1
    for acc in accuracies:

        accuracy_dict = dict()
        accuracy_dict["x"] = count
        count += 1
        accuracy_dict["y"] = acc
        accuracy_response.append(accuracy_dict)
    
    submission_response = list()
    temp_diff = []
    for c in Contributor.query.filter_by(contract_address=contract_address):
        temp_diff.append(c.accuracy - base_accuracy)

    itr = 0
    org = Organizer.query.filter_by(contract_address=contract_address).order_by(Organizer.oid.desc()).first()
    for c in Contributor.query.filter_by(contract_address=contract_address):
        submission_dict = dict()
        submission_dict["wallet_address"] = c.wallet_address
        submission_dict["accuracy"] = c.accuracy
        submission_dict["reward_earned"] = float(org.reward * (temp_diff[itr] / sum(temp_diff)))
        itr += 1
        submission_dict["contract_address"] = c.contract_address
        submission_dict["base_accuracy"] = base_accuracy
        
        submission_response.append(submission_dict)
    

    s = [{"wallet_address":"0xcC1C004756AC35572e225D0aE51e02fdD603Bf60","accuracy":70, "reward_earned": 10, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"},
        {"wallet_address":"0x57394cbFEF9a2955220f068a91e30125707b8Ec3","accuracy":80, "reward_earned": 20, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"},
        {"wallet_address":"0x26e99b39B91c3fe5b180E48EA01464a93f3CB7371","accuracy":90, "reward_earned": 30, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"}
    ]
    a = [{"x":1,"y":70},{"x":2,"y":75},{"x":3,"y":80},{"x":4,"y":85},{"x":5,"y":90}]

    
    return {"accuracy_response" : accuracy_response,"submission_response" : submission_response}

@app.route('/get_developer_submissions', methods = ["GET","POST"])
@cross_origin()
def get_developer_submissions():

    submission_response = list()
    temp = request.get_json()
    print(temp)
    account = temp["userID"]

    for c in Contributor.query.filter_by(wallet_address=account):
        submission_dict = dict()
        submission_dict["contract_address"] = c.contract_address
        temp_o = Organizer.query.filter_by(contract_address=c.contract_address).first()
        submission_dict["organizer_address"] = temp_o.wallet_address
        submission_dict["accuracy"] = c.accuracy
        
        submission_response.append(submission_dict)
    
    return {"submission_response" : submission_response}

@app.route('/get_organizer_contract_data', methods=['GET'])
@cross_origin()
def get_organizer_contract_data():
    
    account = request.args.get("userID")

    contracts = list()
    for o in Organizer.query.filter_by(wallet_address=account):
        organizer_dict = dict()
        organizer_dict["contract_address"] = o.contract_address
        organizer_dict["model_description"] = o.model_description
        organizer_dict["contract_name"] = o.contract_name
        organizer_dict["base_accuracy"] = o.base_accuracy
        organizer_dict["reward"] = o.reward
        # submission_response.append(submission_dict)
        contracts.append(organizer_dict)

    print(contracts)        
    c = [{"organizer_address":"0xcC1C004756AC35572e225D0aE51e02fdD603Bf60","base_accuracy":70, "reward": 10, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"},
        {"organizer_address":"0x57394cbFEF9a2955220f068a91e30125707b8Ec3","base_accuracy":80, "reward": 20, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"},
        {"organizer_address":"0x26e99b39B91c3fe5b180E48EA01464a93f3CB7371","base_accuracy":90, "reward": 30, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"}
    ]
    return {"contract_data" : contracts}

@app.route('/get_contract_data', methods=['GET'])
@cross_origin()
def get_contract_data():

    account = request.args.get("userID")
    contracts = list()
    for o in Organizer.query.all():
        organizer_dict = dict()
        organizer_dict["contract_address"] = o.contract_address
        organizer_dict["organizer_address"] = o.wallet_address
        organizer_dict["contract_name"] = o.contract_name
        organizer_dict["base_accuracy"] = o.base_accuracy
        organizer_dict["reward"] = o.reward
        # submission_response.append(submission_dict)
        contracts.append(organizer_dict)

    print(contracts)        
    c = [{"organizer_address":"0xcC1C004756AC35572e225D0aE51e02fdD603Bf60","base_accuracy":70, "reward": 10, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"},
        {"organizer_address":"0x57394cbFEF9a2955220f068a91e30125707b8Ec3","base_accuracy":80, "reward": 20, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"},
        {"organizer_address":"0x26e99b39B91c3fe5b180E48EA01464a93f3CB7371","base_accuracy":90, "reward": 30, "contract_address": "0xd227568bF5B97cf351Bb95D4fC6a423e9CBa35e3"}
    ]
    return {"contract_data" : contracts}


@app.route('/login', methods=['GET','POST'])
@cross_origin()
def login():
    if request.method == 'POST':
        temp = request.get_json()
        print(temp)
        email = temp['email']
        password = temp['password']

        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password, password):
                return {"user" : {"message" : "login successful", "account_address" : user.wallet_address, "email": user.email,"firstName": user.first_name, "lastName": user.last_name}}
            else:
                return {"message" : "the password entered is incorrect"}
        else:
            return {"message" : "the user is not found, please regsiter first"}
    

@app.route('/signup', methods=['GET','POST'])
@cross_origin()
def signup():

    if request.method == 'POST':
        temp = request.get_json()
        print(temp)
        error = False
        first_name = temp['firstName']
        last_name = temp['lastName']
        email = temp['email']
        password = temp['password']
        password_confirmation = temp['passwordConfirm']
            
        # if len(first_name) < 1 or first_name.isalpha() == False:
        #     error = True
        #     return {"error" : "First name is not valid. Must be more than one character and alphabet only"}

        # if len(last_name) < 1 or last_name.isalpha() == False:
        #     error = True
        #     return {"error" : "First name is not valid. Must be more than one character and alphabet only"} 

        # if len(password) < 8:
        #     error = True
        #     flash('Please enter a valid Password')
        # if len(password_confirmation) < 8:
        #     error = True
        #     flash('Please enter password confirmation')

        # if len(email) < 3:
        #     error = True
        #     return {"error" : "Email cannot be blank"}

        # EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
        # if not EMAIL_REGEX.match(email):
        #     error = True
        #     return {"error" : "Email is invalid"}

        if password != password_confirmation:
            error = True
            return {"error" : "Passwords do not match"}

        else:
            hashed_password = generate_password_hash(
                        password, method='sha256')
            
            users = User.query.all()
            user_count = -1 if users is None else (len(users) - 1)
            accounts = server.eth.accounts

            new_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=hashed_password,
                wallet_address=accounts[user_count+1]
            )
            db.session.add(new_user)
            db.session.commit()
            return {"success" : "user has been registered successfully","account" : accounts[user_count+1]}