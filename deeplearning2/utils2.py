import os
os.environ["KERAS_BACKEND"] = "tensorflow"

import math, keras, datetime, pandas as pd, numpy as np, keras.backend as K, threading, json, re, collections
import tarfile, tensorflow as tf, matplotlib.pyplot as plt, xgboost, operator, random, pickle, glob, os, bcolz
import shutil, sklearn, functools, itertools, scipy
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
import matplotlib.patheffects as PathEffects
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.neighbors import NearestNeighbors, LSHForest
import IPython
from IPython.display import display, Audio
from numpy.random import normal
from gensim.models import word2vec
from keras.preprocessing.text import Tokenizer
#from nltk.tokenize import ToktokTokenizer, StanfordTokenizer  # - changed for compatibility with conda-installed nltk
from nltk.tokenize import ToktokTokenizer  # - changed for compatibility with conda-installed nltk
from nltk.tokenize.stanford import StanfordTokenizer  # - changed for compatibility with conda-installed nltk
from functools import reduce
from itertools import chain

from tensorflow.python.framework import ops
#from tensorflow.contrib import rnn, legacy_seq2seq as seq2seq

from keras_tqdm import TQDMNotebookCallback
#from keras import initializations  # Keras 1
from keras.applications.resnet50 import ResNet50, decode_predictions, conv_block, identity_block
from keras.applications.vgg16 import VGG16
from keras.preprocessing import image, sequence
from keras.preprocessing.sequence import pad_sequences
from keras.models import Model, Sequential
from keras.layers import *
from keras.layers.core import *
from keras.layers.merge import dot, add, concatenate  # Keras2
from keras.optimizers import Adam, SGD, RMSprop
from keras.regularizers import l2, l1 # keras2
from keras.utils.data_utils import get_file
from keras.utils import np_utils
from keras.utils.np_utils import to_categorical

from keras.applications.imagenet_utils import decode_predictions, preprocess_input

np.set_printoptions(threshold=50, edgeitems=20)
def beep(): return Audio(filename='/home/jhoward/beep.mp3', autoplay=True)
def dump(obj, fname): pickle.dump(obj, open(fname, 'wb'))
def load(fname): return pickle.load(open(fname, 'rb'))


def limit_mem():
    K.get_session().close()
    cfg = K.tf.ConfigProto()
    cfg.gpu_options.allow_growth = True
    K.set_session(K.tf.Session(config=cfg))


def autolabel(plt, fmt='%.2f'):
    rects = plt.patches
    ax = rects[0].axes
    y_bottom, y_top = ax.get_ylim()
    y_height = y_top - y_bottom
    for rect in rects:
        height = rect.get_height()
        if height / y_height > 0.95:
            label_position = height - (y_height * 0.06)
        else:
            label_position = height + (y_height * 0.01)
        txt = ax.text(rect.get_x() + rect.get_width()/2., label_position,
                fmt % height, ha='center', va='bottom')
        txt.set_path_effects([PathEffects.withStroke(linewidth=3, foreground='w')])


def column_chart(lbls, vals, val_lbls='%.2f'):
    n = len(lbls)
    p = plt.bar(np.arange(n), vals)
    plt.xticks(np.arange(n), lbls)
    if val_lbls: autolabel(p, val_lbls)


def save_array(fname, arr):
    c=bcolz.carray(arr, rootdir=fname, mode='w')
    c.flush()


def load_array(fname): return bcolz.open(fname)[:]


def load_glove(loc):
    return (load_array(loc+'.dat'),
        pickle.load(open(loc+'_words.pkl','rb'), encoding='latin1'),
        pickle.load(open(loc+'_idx.pkl','rb'), encoding='latin1'))

def plot_multi(im, dim=(4,4), figsize=(6,6), **kwargs ):
    plt.figure(figsize=figsize)
    for i,img in enumerate(im):
        plt.subplot(*((dim)+(i+1,)))
        plt.imshow(img, **kwargs)
        plt.axis('off')
    plt.tight_layout()

def plot_train(hist):
    h = hist.history
    if 'acc' in h:
        meas='acc'
        loc='lower right'
    else:
        meas='loss'
        loc='upper right'
    plt.plot(hist.history[meas])
    plt.plot(hist.history['val_'+meas])
    plt.title('model '+meas)
    plt.ylabel(meas)
    plt.xlabel('epoch')
    plt.legend(['train', 'validation'], loc=loc)


def fit_gen(gen, fn, eval_fn, nb_iter):
    for i in range(nb_iter):
        fn(*next(gen))
        if i % (nb_iter//10) == 0: eval_fn()


def wrap_config(layer):
    return {'class_name': layer.__class__.__name__, 'config': layer.get_config()}


def copy_layer(layer): return layer_from_config(wrap_config(layer))


def copy_layers(layers): return [copy_layer(layer) for layer in layers]


def copy_weights(from_layers, to_layers):
    for from_layer,to_layer in zip(from_layers, to_layers):
        to_layer.set_weights(from_layer.get_weights())


def copy_model(m):
    res = Sequential(copy_layers(m.layers))
    copy_weights(m.layers, res.layers)
    return res


def insert_layer(model, new_layer, index):
    res = Sequential()
    for i,layer in enumerate(model.layers):
        if i==index: res.add(new_layer)
        copied = layer_from_config(wrap_config(layer))
        res.add(copied)
        copied.set_weights(layer.get_weights())
    return res

# copied from utils.py
to_bw = np.array([0.299, 0.587, 0.114])

def gray(img):
    if K.image_dim_ordering() == 'tf':
        return np.rollaxis(img, 0, 1).dot(to_bw)
    else:
        return np.rollaxis(img, 0, 3).dot(to_bw)

def to_plot(img):
    if K.image_dim_ordering() == 'tf':
        return np.rollaxis(img, 0, 1).astype(np.uint8)
    else:
        return np.rollaxis(img, 0, 3).astype(np.uint8)

def plot(img):
    plt.imshow(to_plot(img))


def floor(x):
    return int(math.floor(x))
def ceil(x):
    return int(math.ceil(x))

def plots(ims, figsize=(12,6), rows=1, interp=False, titles=None):
    if type(ims[0]) is np.ndarray:
        ims = np.array(ims).astype(np.uint8)
        if (ims.shape[-1] != 3):
            ims = ims.transpose((0,2,3,1))
    f = plt.figure(figsize=figsize)
    for i in range(len(ims)):
        sp = f.add_subplot(rows, len(ims)//rows, i+1)
        sp.axis('Off')
        if titles is not None:
            sp.set_title(titles[i], fontsize=16)
        plt.imshow(ims[i], interpolation=None if interp else 'none')


def do_clip(arr, mx):
    clipped = np.clip(arr, (1-mx)/1, mx)
    return clipped/clipped.sum(axis=1)[:, np.newaxis]


def get_batches(dirname, gen=image.ImageDataGenerator(), shuffle=True, batch_size=4, class_mode='categorical',
                target_size=(224,224)):
    return gen.flow_from_directory(dirname, target_size=target_size,
            class_mode=class_mode, shuffle=shuffle, batch_size=batch_size)


def onehot(x):
    return to_categorical(x)

