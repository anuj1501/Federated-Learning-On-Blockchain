import sys
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.datasets import mnist
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential
from tqdm import tqdm
import pandas as pd
import os,pickle
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from model import EWC, MLP3, Train, evaluate
MAX_CLIENTS = 2
epochs = 1
lambda_ = 0.1 
lr = 0.001
num_sample = 30
opt = tf.keras.optimizers.Adam(learning_rate=lr)
loss_fn=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)

(X_Train, Y_Train), (X_Test, Y_Test) = mnist.load_data()

X_Train = X_Train.reshape(X_Train.shape[0],X_Train.shape[1]*X_Train.shape[2])
X_Test = X_Test.reshape(X_Test.shape[0],X_Test.shape[1]*X_Test.shape[2])

X_Train = X_Train.astype('float32')
X_Test = X_Test.astype('float32')
X_Train /= 255
X_Test /= 255

train = tf.data.Dataset.from_tensor_slices((X_Train, Y_Train)).shuffle(1000).batch(32)
test = (X_Test, Y_Test)


def create_initial_model(output_file):

    mlp_init = MLP3()
    trn_gd_init = Train(opt, loss_fn)
    model_init = mlp_init.get_compiled_model(opt, loss_fn, ['accuracy'])
    acc_init = trn_gd_init.train(model_init, epochs, train, test_tasks=[test])[0]
    model_init.save(output_file)
    with open('accuracy.txt', 'w') as f:
            f.write("%s" % " ".join(map(str,[acc_init])))

def train_task(model_path, model_uncompiled, lambda_,client_address):

    model = model_uncompiled.get_compiled_model(opt, loss_fn, ['accuracy'])
    model.load_weights(model_path)

    df = pd.read_csv("C:/Users/user/federated-learning/flask/client/client_data.csv")
    data = pd.read_csv(str(df.loc[df["id"] == client_address]["data_path"].values[0]))
    # data = pd.read_csv("C:/Users/user/federated-learning/mnist_test.csv",header=None)
    x_train_client, y_train_client = data.iloc[:,1:], data.iloc[:,0]

    x_train_client = x_train_client.astype('float32')
    x_train_client /= 255


    train_client = tf.data.Dataset.from_tensor_slices((x_train_client.to_numpy(),y_train_client.to_numpy())).shuffle(1000).batch(32)

    # construct the fisher matrix using samples from task A
    ewc = EWC(model, X_Train, num_sample=num_sample)
    f_matrix = ewc.get_fisher()

    data = "uploads/"
    prior_weights = model.get_weights()
    trn = Train(opt, loss_fn, prior_weights=prior_weights, lambda_=lambda_)
    accuracy = trn.train(model, 
                        epochs, 
                        train_client, 
                        fisher_matrix=f_matrix, 
                        test_tasks=[test]
                        )
    
    model.save("C:/Users/user/federated-learning/flask/client/models/" + str(client_address) + "_model.h5")
    df.loc[df["id"] == client_address,"model_path"] = str("models/" + str(client_address) + "_model.h5")
    df.loc[df["id"] == client_address,"accuracy"] = str(accuracy[0][0])
    df.to_csv("C:/Users/user/federated-learning/flask/client/client_data.csv",index=False)
    return model, accuracy[0][0]

def ClientUpdate(model_filename,client_address):

    accs = []
    
    m = MLP3()
    trained_model, acc = train_task(model_filename, m, lambda_,client_address)
    print("model saved successfully")
    accs.append(acc)
    
    with open('accuracy.txt', 'w') as f:
            f.write("%s" % " ".join(map(str,accs)))


def FederatedAveraging(models_dir_path):

    new_model = MLP3().get_compiled_model(opt, loss_fn, ['accuracy'])
    
    # WEIGHTS = np.array([np.zeros(layer.numpy().shape) for layer in weights], 
    #                     dtype=object
    #                     )

    models_path = os.listdir(models_dir_path)  
    
    # clients = np.random.permutation(MAX_CLIENTS)[:np.random.randint(1, MAX_CLIENTS + 1)]
    n_models = len(models_path)
    total_weights = list()

    for model_path in models_path:

        if model_path.startswith("0x"):
            
            model = MLP3().get_compiled_model(opt, loss_fn, ['accuracy'])
            model.load_weights("../client/models/" + str(model_path).replace("//","/"))
            
            total_weights.append(model.get_weights())

    new_weights = list()

    for weights_list_tuple in zip(*total_weights):
        new_weights.append(np.array([np.array(weights_).mean(axis=0) for weights_ in zip(*weights_list_tuple)]))

     
    new_model.set_weights(new_weights)
    federated_accuracy = evaluate(new_model,test[0],test[1])
    with open('accuracy.txt', 'w') as f:
            f.write("%s" % " ".join(map(str,[federated_accuracy]))) 

    new_model.save("../client/models/model.h5")
          
    print("federated learning successful")
    # with open(output_file, "wb") as f:
    #     pickle.dump(WEIGHTS, f)

if __name__ == '__main__':

    if not os.path.exists("C:/Users/user/federated-learning/flask/client/models/model.h5"):
        create_initial_model("C:/Users/user/federated-learning/flask/client/models/model.h5")

    if len(sys.argv) > 2:
        if sys.argv[1] == 'client':
            print(sys.argv)
            ClientUpdate(sys.argv[2], sys.argv[3])

        elif sys.argv[1] == 'org':
            FederatedAveraging(sys.argv[2])
