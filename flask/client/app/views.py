from flask import render_template, request, flash, redirect, url_for,send_file
from app import *
import ipfshttpclient
import os, time, requests, shutil
import pandas as pd
from solcx import compile_files, link_code, compile_source

def get_accuracy():
    file = open('../ai/accuracy.txt', 'r')
    accuracy = file.read()
    return accuracy

def fetch_model_from_ipfs(ipfsHash):
    if not os.path.exists('models'):
        os.mkdir('models')
    req = requests.get("http://localhost:8080/ipfs/" + ipfsHash)

    if req.status_code != 200:
        print("Failed to retrieve checkpoint")
    else:
        with open("models/model.pkl", "wb") as f:
            f.write(req.content)
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

@app.route('/deploy_contract', methods=['POST'])
def deploy_contract():
    with open("C:/Users/user/federated-learning/contracts/LearningContract.sol","r") as f:
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
    account = session.get('account')

    # Submit the transaction that deploys the contract
    tx_hash = contract.constructor().transact({'from':account})
    print ("Tx submitted: ", server.toHex(tx_hash))  # added by me.

    # Wait for the transaction to be mined, and get the transaction receipt
    tx_receipt = server.eth.waitForTransactionReceipt(tx_hash)

    session['abi'] = contract_interface['abi']
    session['contract_address'] = tx_receipt.contractAddress

    return render_template('functions.html', account=account, accuracy=get_accuracy())


@app.route('/', defaults={'account_no': None}, methods=['GET', 'POST'])
@app.route('/account/set/<string:account_no>', methods=['POST'])
def homepage(account_no):
    if request.method == 'GET':
        accounts = [server.toChecksumAddress(i) for i in server.eth.accounts]
        return render_template('homepage.html', accounts=accounts)
    elif request.method == 'POST':
        session['account'] = account_no
        return redirect(url_for('contract_operations'))


@app.route('/functions', methods=['GET', 'POST'])
def contract_operations():
    if request.method == 'GET':
        account = session.get('account')    
        print(os.path.abspath(os.curdir))
        os.system('python ../ai/ai.py')     
        return render_template('functions.html', account=account, accuracy = get_accuracy())
    else:
        return None


@app.route('/addFileToIPFS', methods=['GET', 'POST'])
def addFileToIPFS():
    if request.method == 'POST':
        upload_file = None
        if 'file' not in request.files:
            upload_file = 'temp.txt'
        else:
            upload_file = request.files['file']

        if upload_file.filename == '':
            error = "File wasn't selected!"
            print("File wasn't selected")
            return render_template('functions.html', error=error)
        elif upload_file and allowed_file(upload_file.filename):

            acct_address = session.get('account')
            upload_file_filename_secure = secure_filename(upload_file.filename)

            if not os.path.exists(app.config['UPLOAD_FOLDER'] + "/" + acct_address):
                os.mkdir(app.config['UPLOAD_FOLDER'] + "/" + acct_address)

            upload_file.save(app.config['UPLOAD_FOLDER'] + "/" + acct_address + "/test.csv")
            result = upload_file_sync(app.config['UPLOAD_FOLDER'] + "/" + acct_address + "/test.csv")
            client_folder_path = app.config['UPLOAD_FOLDER'] + "/" + acct_address
            model_number = int(request.form['model_number'])
            filename = upload_file.filename
            
            api = ipfshttpclient.connect("/ip4/127.0.0.1/tcp/5001/http")
            
            res = api.add(app.config['UPLOAD_FOLDER'] + "/" + acct_address + "/test." + upload_file_filename_secure.split('.')[1])
            print(res)
            ipfsHash = res['Hash']

            datapath = str(client_folder_path) + "/" + str(ipfsHash + "_" + upload_file_filename_secure)
            os.replace(app.config['UPLOAD_FOLDER'] + "/" + acct_address + "/test.csv", datapath)            
            print("Uploaded file successfully")

            df = pd.read_csv("C:/Users/user/federated-learning/flask/client/client_data.csv")
            if str(acct_address) not in df["id"].values.tolist():
                df = df.append({
                    "id": str(acct_address),
                    "data_path": str(datapath),
                    "model_path":"",
                    "model_id":str(model_number),
                    "total_reward":""
                }, ignore_index = True)
            else:
                df.loc[df["id"] == acct_address,"data_path"] = str(str(client_folder_path) + "/" + str(ipfsHash + "_" + upload_file_filename_secure))
                df.loc[df["id"] == acct_address,"model_id"] = str(model_number)
            df.to_csv("C:/Users/user/federated-learning/flask/client/client_data.csv",index=False)
            
            contract = server.eth.contract(
                address=session.get('contract_address'),
                abi=session.get('abi'),
                )
            if acct_address is not None:
                tx_hash = contract.functions.addFile(model_number,datapath,ipfsHash).transact({'from':session.get('account')})
                receipt = server.eth.waitForTransactionReceipt(tx_hash)
                print("Gas Used ", receipt.gasUsed)
                return render_template('functions.html', account=acct_address, success=True, accuracy = get_accuracy())
            else:
                flash('No account was chosen')
                return render_template('functions.html', account=acct_address, success=False, accuracy = get_accuracy())
   
        return render_template('functions.html', error="Something went wrong.")

    
    return render_template('functions.html', account=acct_address , accuracy = get_accuracy())


@app.route('/model_pull', methods=['POST'])
def checkpoint_model_pull():
    contract = server.eth.contract(
                address=session.get('contract_address'),
                abi=session.get('abi'),
                )
    account = session.get('account')

    os.chdir('../ai')
    os.system('python ai.py org C:/Users/user/federated-learning/flask/client/models')
    os.chdir('../client')
    df = pd.read_csv("C:/Users/user/federated-learning/flask/client/client_data.csv")

    users = contract.functions.getRegisteredUsers().call()
    best_acc_address = None
    highest_accuracy = 0
    for user in users:
        client_acc = df.loc[df["id"] == user,"accuracy"].values.tolist()[0]
        if highest_accuracy < client_acc:
            best_acc_address = user
    print(best_acc_address)
    
    nonce = server.eth.getTransactionCount(account)
    
    tx_hash = contract.functions.transferReward(best_acc_address).transact({
        'nonce':nonce,
        'from': account,
        'to': best_acc_address,
        'value': server.toWei(2,'ether')
    })
    receipt = server.eth.waitForTransactionReceipt(tx_hash)
    print("Gas Used ", receipt.gasUsed)

    path = "C:/Users/user/federated-learning/flask/client/models/model.h5"
    return send_file(path, as_attachment=True)
    # return redirect(url_for('download_model'))



@app.route('/train', methods=['POST'])
def train():
    os.chdir('../ai')
    print(os.path.abspath(os.curdir))
    os.system('python ai.py client C:/Users/user/federated-learning/flask/client/models/model.h5 ' + str(session.get('account')))
    os.chdir('../client')
    account = session.get('account')  
    contract = server.eth.contract(
                address=session.get('contract_address'),
                abi=session.get('abi'),
                )

    df = pd.read_csv("C:/Users/user/federated-learning/flask/client/client_data.csv")
    model_path =  df.loc[df["id"] == account,"model_path"]

    api = ipfshttpclient.connect("/ip4/127.0.0.1/tcp/5001/http")
    res = api.add(model_path)
    modelHash = res['Hash']

    tx_hash = contract.functions.addModelFile(modelHash).transact(
        {'from': account})
    receipt = server.eth.waitForTransactionReceipt(tx_hash)
    print("Gas Used ", receipt.gasUsed)
    
    return render_template('functions.html', account=account, accuracy=get_accuracy())
