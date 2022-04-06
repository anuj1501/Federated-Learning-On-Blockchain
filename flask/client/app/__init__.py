from flask import Flask, session
from web3 import Web3, HTTPProvider
import json
from flask_session import Session
from werkzeug.utils import secure_filename
import os
import pandas as pd
# Flask App initialization
app = Flask(__name__)
app.secret_key = 'secret_key'

BASE_PATH = 'C:/Users/user/'

if not os.path.exists("C:/Users/user/federated-learning/flask/client/client_data.csv"):
    df = pd.DataFrame(columns=["id","data_path","model_path","model_id","total_reward","accuracy"])
    df.to_csv("C:/Users/user/federated-learning/flask/client/client_data.csv",index=False) 

UPLOAD_FOLDER = BASE_PATH + 'federated-learning/flask/client/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','pkl', 'csv'])

# SESSION_TYPE = 'redis'
app.config['SESSION_TYPE'] = 'filesystem'
app.config.from_object(__name__)
Session(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

server = Web3(HTTPProvider('http://localhost:7545'))

# CONTRACT_ADDRESS = server.toChecksumAddress("0xDC32ACb654e7A9dB87c9F6ca831d6C52D0E82149")
# DEFAULT_ACCOUNT = server.toChecksumAddress("0x35ab83137e14FBeFE4b2c081F23a89D18cf510F5")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


from app import views
