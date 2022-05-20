import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.layers import MaxPooling2D
from tensorflow.keras.layers import Activation
from tensorflow.keras.layers import Flatten
from tensorflow.keras.layers import Dense
from tensorflow.keras import layers
from tensorflow.keras import backend as K
from tensorflow.keras.datasets import mnist
import numpy as np
from tqdm import tqdm
import pickle
import pandas as pd

epochs = 1
lambda_ = 0.1 
lr = 0.001
num_sample = 30
opt = tf.keras.optimizers.Adam(learning_rate=lr)
loss_fn=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)

def evaluate(model, test_x, test_y):
    acc = tf.keras.metrics.SparseCategoricalAccuracy(name='accuracy')
    for imgs, labels in zip(test_x, test_y):
        preds = model.predict_on_batch(np.array([imgs]))
        acc.update_state(labels, preds)
    return round(100*acc.result().numpy(), 2)

def permute_task(train, test):
    train_shape, test_shape = train.shape, test.shape
    train_flat, test_flat = train.reshape((-1, 784)), test.reshape((-1, 784))
    idx = np.arange(train_flat.shape[1])
    np.random.shuffle(idx)
    train_permuted, test_permuted = train_flat[:, idx], test_flat[:, idx]
    return (train_permuted.reshape(train_shape), test_permuted.reshape(test_shape))

class MLP3:
    
    def __init__(self, input_sh=784, hidden_layers_neuron_list=[200, 200], num_classes=10):
        self.input_sh = input_sh
        self.num_classes = num_classes
        self.hidden_layers_neuron_list = hidden_layers_neuron_list
        self.model = self.create_mlp()
        
    def create_mlp(self):
        model = Sequential([
                Dense(self.hidden_layers_neuron_list[0], input_shape=(self.input_sh,), activation='relu'),
                Dense(self.hidden_layers_neuron_list[1], activation='relu'),
                Dense(self.num_classes)
        ])
        return model
    
    def get_uncompiled_model(self):
        return self.model
    
    def get_compiled_model(self, optimizer, loss_fn, metrics ):
        compiled_model = self.model
        compiled_model.compile(optimizer, loss_fn, metrics)
        return compiled_model

(X_Train, Y_Train), (X_Test, Y_Test) = mnist.load_data()

X_Test = X_Test[:1000]
Y_Test = Y_Test[:1000]

train = tf.data.Dataset.from_tensor_slices((X_Train, Y_Train)).shuffle(1000).batch(32)
X_Test = X_Test.reshape(X_Test.shape[0],X_Test.shape[1]*X_Test.shape[2])

test = (X_Test, Y_Test)
model = MLP3().get_compiled_model(opt, loss_fn, ['accuracy'])
data = pd.read_csv("client1.csv")

x_train_client, y_train_client = data.iloc[:,1:], data.iloc[:,0]

x_train_client = x_train_client.astype('float32')
x_train_client /= 255


train_task = tf.data.Dataset.from_tensor_slices((x_train_client.to_numpy(),y_train_client.to_numpy())).shuffle(1000).batch(32)
test_tasks=[test]

if test_tasks:
    test_acc = [[] for _ in test_tasks]
else: 
    test_acc = None
for epoch in tqdm(range(1)):
    for batch in train_task:
        X, y = batch
        with tf.GradientTape() as tape:
            pred = model(X)
            loss = loss_fn(y, pred)

        grads = tape.gradient(loss, model.trainable_variables)
        opt.apply_gradients(zip(grads, model.trainable_variables))
    # evaluate with the test set of task after each epoch
    if test_acc:
        for i in range(len(test_tasks)):
            test_acc[i].append(evaluate(model, test_tasks[i][0], test_tasks[i][1]))

print(test_acc)
model.save("base_model.h5")

valid_data = data[:1000]
valid_data.to_csv("validation_data.csv",index=False)