from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from flask_cors import CORS,cross_origin

app = Flask(__name__)
CORS(app)
# app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/set_name",methods=["POST", "GET"])
@cross_origin()
def set_name():
    session["name"] = "anju"
    return {"output":"success"}
  
  
@app.route("/get_name", methods=["POST", "GET"])
@cross_origin()
def get_name():
    return {"name" : session.get("name")}

if __name__ == '__main__':

    port = 5000 #int(sys.argv[2])
    app.debug = True
    app.run(host='localhost', port=port)
