'''
convolutional neural network
tensorflow 
cross entropy loss function
relu activation function
max pooling
softmax logits
adam optimizer
based on LeNet
'''

import tensorflow as tf
import numpy as np
import data_loader

def convolution_layer(input, channels, filters, kernel_size=5, strides=1, padding='VALID'):
	weights = tf.Variable(tf.truncated_normal(
		shape=[kernel_size, kernel_size, channels, filters], 
		mean=0, 
		stddev=0.1
	))
	biases = tf.Variable(tf.zeros([filters]))
	layer = tf.nn.conv2d(
		input, 
		filter=weights, 
		strides=[1, strides, strides, 1], 
		padding=padding
	) + biases
	return tf.nn.relu(layer)

def pooling_layer(input, k=2, padding='VALID'):
	return tf.nn.max_pool(
		input, 
		ksize=[1, k, k, 1], 
		strides=[1, k, k, 1], 
		padding=padding
	)

def flatten_layer(layer):
	layer_shape = layer.get_shape()
	num_features = layer_shape[1:4].num_elements()
	return tf.reshape(layer, [-1, num_features])

def fully_connected_layer(input, num_inputs, num_outputs, relu=True):
	weights = tf.Variable(tf.truncated_normal(
		shape=[num_inputs, num_outputs], 
		mean=0, 
		stddev=0.1
	))
	biases = tf.Variable(tf.zeros([num_outputs]))
	layer = tf.matmul(input, weights) + biases
	if relu:
		return tf.nn.relu(layer)
	else:
		return layer


class NeuralNetwork:
	def __init__(self):
		self.sess = tf.Session()
		
		self.learning_rate = 0.001
		self.batch_size = 128
		self.patience = 8
		
		self.load_data()
		self.build()
	
	def load_data(self):
		self.X_train, self.y_train = data_loader.load_training_data(normalize=True)
		self.X_valid, self.y_valid = data_loader.load_validation_data(normalize=True)
		self.X_test, self.y_test = data_loader.load_testing_data(normalize=True)
		
		data = tf.data.Dataset.from_tensor_slices((self.X_train, self.y_train))
		data = data.shuffle(len(self.y_train), reshuffle_each_iteration=True).batch(self.batch_size)
		iterator = tf.data.Iterator.from_structure(data.output_types, data.output_shapes)
		self.train_initializer = iterator.make_initializer(data)
		self.X_batch, self.y_batch = iterator.get_next()
		
		self.img_shape = list(self.X_train[0].shape)
		self.num_classes = len(np.unique(self.y_train))
	
	def build(self):
		self.x = tf.placeholder(tf.float32, [None] + self.img_shape)
		self.y = tf.placeholder(tf.int32, [None])
		
		# Layer 1 = Convolution: 32x32@3 -> 28x28@6 + ReLU
		conv1 = convolution_layer(self.x, channels=3, filters=6, kernel_size=5, padding='VALID')
		# Layer 2 = Pooling: 28x28@6 -> 14x14@6
		pool1 = pooling_layer(conv1)
		# Layer 3 = Convolution: 14x14@6 -> 10x10@16 + ReLU
		conv2 = convolution_layer(pool1, channels=6, filters=16, kernel_size=5, padding='VALID')
		# Layer 4 = Pooling: 10x10@16 -> 5x5@16
		pool2 = pooling_layer(conv2)
		# Layer 5 = Flatten: 5x5@16 -> 400
		flat = flatten_layer(pool2)
		# Layer 6 = Fully Connected: 400 -> 120
		fc1 = fully_connected_layer(flat, num_inputs=400, num_outputs=120)
		# Layer 7 = Fully Connected: 120 -> 84
		fc2 = fully_connected_layer(fc1, num_inputs=120, num_outputs=84)
		# Layer 8 = Logits: 84 -> 43
		logits = fully_connected_layer(fc2, num_inputs=84, num_outputs=43, relu=False)
		
		one_hot_y = tf.one_hot(self.y, self.num_classes)
		
		cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits=logits, labels=one_hot_y)
		self.loss = tf.reduce_mean(cross_entropy)
		
		self.optimizer = tf.train.AdamOptimizer(learning_rate=self.learning_rate).minimize(self.loss)
		
		correct_prediction = tf.equal(tf.argmax(logits, axis=1), tf.argmax(one_hot_y, axis=1))
		self.accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
		self.prediction = tf.argmax(logits, axis=1)
	
	def train(self, epochs=10):
		self.sess.run(tf.global_variables_initializer())
		total_train_loss = []
		total_train_acc = []
		total_valid_loss = [] 
		total_valid_acc = []
		best_acc = 0
		no_acc_change = 0
		
		print('training start')
		
		for e in range(epochs):
			self.sess.run(self.train_initializer)
			try: 
				total_loss = 0
				total_acc = 0
				while True:
					batch_x, batch_y = self.sess.run([self.X_batch, self.y_batch])
					feed_dict = {self.x: batch_x, self.y: batch_y}
					self.sess.run(self.optimizer, feed_dict=feed_dict)
					loss, acc = self.sess.run([self.loss, self.accuracy], feed_dict=feed_dict)
					total_loss += loss * len(batch_y)
					total_acc += acc * len(batch_y)
			except tf.errors.OutOfRangeError:
				pass
			
			train_loss = total_loss / len(self.y_train)
			train_acc = total_acc / len(self.y_train)
			
			feed_dict = {self.x: self.X_valid, self.y: self.y_valid}
			valid_loss, valid_acc = self.sess.run([self.loss, self.accuracy], feed_dict=feed_dict)
			print(f'epoch {e + 1}: train loss = {train_loss:.4f}, train acc = {train_acc:.4f}, valid loss = {valid_loss:.4f}, valid acc = {valid_acc:.4f}')
			
			total_train_loss.append(train_loss)
			total_train_acc.append(train_acc)
			total_valid_loss.append(valid_loss)
			total_valid_acc.append(valid_acc)
			
			if valid_acc > best_acc:
				best_acc = valid_acc
				no_acc_change = 0
			else:
				no_acc_change += 1
			
			if no_acc_change >= self.patience:
				print('early stopping')
				break
			
		print('training complete')
		
		feed_dict = {self.x: self.X_test, self.y: self.y_test}
		acc = self.sess.run(self.accuracy, feed_dict=feed_dict)
		print(f'test accuracy = {acc:.4f}')
		
		return total_train_loss, total_train_acc, total_valid_loss, total_valid_acc
	
	def predict(self, x):
		feed_dict = {self.x : x}
		return self.sess.run(tf.argmax(self.prediction, axis=1), feed_dict=feed_dict)


if __name__ == '__main__':
	net = NeuralNetwork()
	net.train(10)
