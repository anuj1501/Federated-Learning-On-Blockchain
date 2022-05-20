import datetime
from app import *

class Contributor(db.Model):
    cid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    wallet_address = db.Column(db.String(100))
    data_path = db.Column(db.String(100))
    model_path = db.Column(db.String(100))
    accuracy = db.Column(db.Integer, default=0)
    reward_earned = db.Column(db.Integer, default=0)
    dateofsub = db.Column(db.DateTime, default=datetime.datetime.now)
    contract_address = db.Column(db.String(100))

    def __init__(self, wallet_address,data_path,model_path,accuracy,contract_address):
        self.wallet_address = wallet_address
        self.data_path = data_path
        self.model_path = model_path
        self.accuracy = accuracy
        self.contract_address = contract_address


class Organizer(db.Model):
    oid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    wallet_address = db.Column(db.String(100))
    validation_data_path = db.Column(db.String(100))
    base_model_path = db.Column(db.String(100))
    contract_name = db.Column(db.String(100))
    model_description = db.Column(db.String(1000))
    reward = db.Column(db.Integer, default=0)
    base_accuracy = db.Column(db.Integer, default=0)
    dateofsub = db.Column(db.DateTime, default=datetime.datetime.now)
    contract_address = db.Column(db.String(100))

    def __init__(self,wallet_address,validation_data_path,base_model_path,contract_name,model_description,reward,base_accuracy,contract_address):
        
        self.wallet_address = wallet_address
        self.validation_data_path = validation_data_path
        self.base_model_path = base_model_path
        self.contract_name = contract_name
        self.model_description = model_description
        self.reward = reward
        self.base_accuracy = base_accuracy
        self.contract_address = contract_address

class User(db.Model):
    uid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    password = db.Column(db.String(200))
    wallet_address = db.Column(db.String(100))

    def __init__(self,first_name,last_name,email,password,wallet_address):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.wallet_address = wallet_address
      
    