from email.mime import base
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

from ai.model import EWC, MLP3, Train, evaluate
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


def calculate_initial_accuracy(validation_path,model_path):

    init_model = MLP3().get_compiled_model(opt, loss_fn, ['accuracy'])
    init_model.load_weights(model_path)
    data = pd.read_csv(validation_path)

    x_val, y_val = data.iloc[:,1:], data.iloc[:,0]
    x_val = x_val.astype('float32')
    x_val /= 255
    print(x_val.shape)
    print(y_val.shape)
    init_accuracy = evaluate(init_model,test[0],test[1])
    return init_accuracy
    # mlp_init = MLP3()
    # trn_gd_init = Train(opt, loss_fn)
    # model_init = mlp_init.get_compiled_model(opt, loss_fn, ['accuracy'])
    # acc_init = trn_gd_init.train(model_init, epochs, train, test_tasks=[test])[0]
    # model_init.save(output_file)
    # with open('accuracy.txt', 'w') as f:
    #         f.write("%s" % " ".join(map(str,[acc_init])))

def train_task(model_folder_path, model_uncompiled, lambda_,client_address,data_path,contract_address,base_data_path):

    model = model_uncompiled.get_compiled_model(opt, loss_fn, ['accuracy'])
    model.load_weights(base_data_path + contract_address + "/base_model.h5")
    data = pd.read_csv(data_path)
    x_train_client, y_train_client = data.iloc[:,1:], data.iloc[:,0]

    x_train_client = x_train_client.astype('float32')
    x_train_client /= 255

    train_client = tf.data.Dataset.from_tensor_slices((x_train_client.to_numpy(),y_train_client.to_numpy())).shuffle(1000).batch(32)

    # construct the fisher matrix using samples from task A
    ewc = EWC(model, X_Train, num_sample=num_sample)
    f_matrix = ewc.get_fisher()

    prior_weights = model.get_weights()
    trn = Train(opt, loss_fn, prior_weights=prior_weights, lambda_=lambda_)
    accuracy = trn.train(model, 
                        epochs, 
                        train_client, 
                        fisher_matrix=f_matrix, 
                        test_tasks=[test]
                        )
    
    model_saved_path = model_folder_path + "/" + str(client_address) + "_model.h5"
    model.save(model_saved_path)
    return accuracy[0], model_saved_path

def ClientUpdate(model_folder_path,data_path,contract_address,client_address,base_data_path):
    accs = []
    m = MLP3()
    acc,model_saved_path = train_task(model_folder_path, m, lambda_,client_address,data_path,contract_address,base_data_path)
    print("model saved successfully")
    accs.append(acc)
    return accs[0][0],model_saved_path


def FederatedAveraging(best_model_paths, base_model_path):

    new_model = MLP3().get_compiled_model(opt, loss_fn, ['accuracy'])
     
    total_weights = list()
    for model_path in best_model_paths:           
        model = MLP3().get_compiled_model(opt, loss_fn, ['accuracy'])
        model.load_weights(model_path)
        total_weights.append(model.get_weights())

    new_weights = list()
    for weights_list_tuple in zip(*total_weights):
        new_weights.append(np.array([np.array(weights_).mean(axis=0) for weights_ in zip(*weights_list_tuple)]))

    new_model.set_weights(new_weights)
    federated_accuracy = evaluate(new_model,test[0],test[1])
    new_model.save(base_model_path)
    return federated_accuracy

