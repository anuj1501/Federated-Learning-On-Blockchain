from flask import Flask, session,g
from flask_cors import CORS,cross_origin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from web3 import Web3, HTTPProvider
import json
from flask_session import Session
from werkzeug.utils import secure_filename
import os
import pandas as pd
# Flask App initialization
app = Flask(__name__)
app.secret_key = 'secret_key'

BASE_PATH = 'C:/Users/user/federated-learning/' # Modify it to your own directory path

UPLOAD_FOLDER = BASE_PATH + 'flask/uploads/'
BASE_DATA_FOLDER = BASE_PATH + 'flask/basedata/'
MODEL_FOLDER = BASE_PATH + 'flask/models/'

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','pkl', 'csv'])

# SESSION_TYPE = 'redis'
app.config['SESSION_TYPE'] = 'filesystem'
app.config.from_object(__name__)
Session(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///federated_learning.sqlite"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config['BASE_PATH'] = BASE_PATH
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BASE_DATA_FOLDER'] = BASE_DATA_FOLDER
app.config['MODEL_FOLDER'] = MODEL_FOLDER


CORS(app)

server = Web3(HTTPProvider('http://localhost:7545'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


from app import model
db.create_all()
from app import views
