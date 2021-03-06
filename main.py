"""
Module to tinker with models, data loading and trainings
"""
import cv2
import numpy as np
import csv
import sys
import matplotlib.pyplot as plt
from numba import njit, vectorize, prange
from typing import List, Any, Tuple,Dict
from nptyping import NDArray
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
import tensorflow as tf
from ctypes import *

# User-defined modules
from models import *

# Definition of types for typing
DataSources = Dict[str,str]
Image = NDArray[(Any, Any, 3), int]
ImageSeg = NDArray[(Any, Any, 3), int]
ImageSegBinary = NDArray[(Any, Any, 1), int]
ImageCollection = NDArray[(Any), Image]
ImageSegCollection = NDArray[(Any), ImageSeg]
ImageSegBinaryCollection = NDArray[(Any), ImageSegBinary]

# For printing all nmumpy array values
np.set_printoptions(threshold=np.inf)

def loadFromDataSources(d_list: List[DataSources]) -> Tuple[List[Image], List[ImageSeg]]:
    """
    Function to load the original images and ground truth images from the paths
    given in the DataSources
    Args:
        d_list: List of DataSources

    Returns:
        A tuple with a list of original images and a list of ground truth images
    """
    if len(d_list) == 0:
        raise ValueError("Param is empty")
    if not isinstance(d_list[0], dict):
        raise TypeError("Param is not a dictionary list")
    data = []
    lbl = []
    count = 0
    for row in d_list:
        if not "data" in row.keys() or not "label" in row.keys():
            raise ValueError("Param dictionaries do not contain the desired keys")
        try:
            count += 1
            if count % 15 == 0:
                print(count)
            auxData = cv2.imread(row["data"])
            auxLbl = cv2.imread(row["label"])
            auxData = cv2.resize(auxData, (304,304))
            auxLbl = cv2.resize(auxLbl, (304,304))
            if auxData is not None:
                data.append(auxData)
            if auxLbl is not None:
                lbl.append(auxLbl)
        except ValueError:
            sys.stderr.write("Could not load an image")
    return data, lbl

def getItems(data_src: List[str],lbl_src: List[str]) -> Tuple[ImageCollection,ImageSegBinaryCollection]:
    """
    Funcion that opens and loads the imges given as paths for the data and labels
    Args:
        data_src: List with the paths to the images that will be loaded as data
        lbl_src: List with the paths to the images that will be loaded as labels

    Returns:
        Tuple with the collection of the data and the collection of the labels
    """
    count = 0
    x = np.zeros((len(data_src),224,224,3),dtype=np.int32)
    for j,path in enumerate(data_src):
        count += 1
        print("{}: {}".format(count,path))
        x[j] = tf.keras.preprocessing.image.load_img(path,target_size=(224,224))
    count = 0
    y = np.zeros((len(data_src),224,224,1),dtype=np.int32)
    for j,path in enumerate(lbl_src):
        count += 1
        print("{}: {}".format(count,path))
        img = tf.keras.preprocessing.image.load_img(path,color_mode="grayscale",target_size=(224,224))
        y[j] = np.expand_dims(img,2)
        y[j] -= 1
        
    return x,y

def loadCsvFile(filename: str) -> Tuple[List[Image], List[ImageSeg],List[DataSources]]:
    """
        Function to load original images and ground truth images from .csv file
        Args:
            filename: .csv file name

        Returns:
            a tuple with a list of original images  and a list of ground truth images
    """
    if not isinstance(filename, str):
        raise TypeError("Name is not a string")
    with open(filename) as csvfile:
        data_storage = list(csv.DictReader(csvfile, delimiter=";"))
        train_dict, test_dict = train_test_split(data_storage,test_size=0.3,train_size=0.7,random_state=69)
        train_dict, test_dict = train_test_split(data_storage,test_size=0.95,train_size=0.05,random_state=69)
        data,lbl = loadFromDataSources(train_dict)
        return data,lbl,test_dict

def loadCsvFile2(filename: str) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
        Function to load original images and ground truth images from .csv file
        Args:
            filename: .csv file name

        Returns:
            a tuple with a list of original images  and a list of ground truth images
    """
    if not isinstance(filename, str):
        raise TypeError("Name is not a string")
    with open(filename) as csvfile:
        reader = csv.reader(csvfile, delimiter=";")
        next(reader)
        data_storage = list(reader)
        train_dict, test_dict = train_test_split(data_storage,test_size=0.3,train_size=0.7,random_state=69)
        train_data_src = [d[0] for d in train_dict]
        train_labl_src = [d[1] for d in train_dict]
        test_data_src = [d[0] for d in test_dict]
        test_labl_src = [d[1] for d in test_dict]
        return train_data_src,train_labl_src, test_data_src,test_labl_src

def oneDim2rgbLabel(imgBin: ImageSegBinaryCollection) -> ImageSegCollection:
    """
    Function to convert 1D ground truth values to 3D images
    Input:
        Numpy array of 1D ground truth values. Input must be (numImg, widht, height, 1)
    Returns:
        Numpy array with 3D images (numImg, widht, height, 3) with the followig codification:
        00 -> unlabeled
        01 -> paved-grass
        02 -> dirt
        03 -> grass
        04 -> gravel
        05 -> water
        06 -> rocks
        07 -> pool
        08 -> vegetation
        09 -> roof
        10 -> wall
        11 -> window
        12 -> door
        13 -> fence
        14 -> fence-pole
        15 -> person
        16 -> dog
        17 -> car
        18 -> bicycle
        19 -> tree
        20 -> bald-tree
        21 -> ar-marker
        22 -> obstacle
        23 -> conflicting

    """
    lblDict = {
        "unlabeled": [0, 0, 0], # 0
        "paved-area": [128, 64, 128], # 1
        "dirt": [0, 76, 130], # 2
        "grass": [0, 102, 0], # 3
        "gravel": [87, 103, 112], # 4
        "water": [168, 42, 28], # 5
        "rocks": [30, 41, 48], # 6
        "pool": [89, 50, 0], # 7
        "vegetation": [35, 142, 107], # 8 
        "roof": [70, 70, 70], # 9
        "wall": [156, 102, 102], # 10
        "window": [12, 228, 254], # 11
        "door": [12, 148, 254], # 12
        "fence": [153, 153, 190], # 13 
        "fence-pole": [153, 153, 153], # 14
        "person": [96, 22, 255], # 15
        "dog": [0, 51, 102], # 16 
        "car":[150, 143, 9], # 17
        "bicycle": [32, 11, 119], # 18
        "tree": [0, 51, 51],  # 19
        "bald-tree": [190, 250, 190], # 20
        "ar-marker": [146, 150, 112], # 21
        "obstacle": [115, 135, 2], # 22
        "conflicting": [0, 0, 255]  # 23
    }
     
    if len(imgBin.shape) != 4:
        raise TypeError("Array is not 4D")
    if imgBin.shape[3] != 1:
        raise ValueError("Array must have format (numImg, width, height, 1)")
     
    img = np.zeros((imgBin.shape[0],imgBin.shape[1],imgBin.shape[2], 3), dtype=np.int16)
    count = 0
    for i in range(imgBin.shape[0]):
        for j in range(imgBin.shape[1]):
            for k in range(img.shape[2]):
                if imgBin[i, j, k] == 0:
                    img[i, j, k, :]  = lblDict["unlabeled"]
                elif imgBin[i, j, k] == 1:
                    img[i, j, k, :] = lblDict["paved-area"]
                elif imgBin[i, j, k] == 2:
                    img[i, j, k, :] = lblDict["dirt"]
                elif imgBin[i, j, k] == 3:
                    img[i, j, k, :] = lblDict["grass"]
                elif imgBin[i, j, k] == 4:
                    img[i, j, k, :] = lblDict["gravel"]
                elif imgBin[i, j, k] == 5:
                    img[i, j, k, :] = lblDict["water"]
                elif imgBin[i, j, k] == 6:
                    img[i, j, k, :] = lblDict["rocks"]
                elif imgBin[i, j, k] == 7:
                    img[i, j, k, :] = lblDict["pool"]
                elif imgBin[i, j, k] == 8:
                    img[i, j, k, :] = lblDict["vegetation"]
                elif imgBin[i, j, k] == 9:
                    img[i, j, k, :] = lblDict["roof"]
                elif imgBin[i, j, k] == 10:
                    img[i, j, k, :] = lblDict["wall"]
                elif imgBin[i, j, k] == 11:
                    img[i, j, k, :] = lblDict["window"]
                elif imgBin[i, j, k] == 12:
                    img[i, j, k, :] = lblDict["door"]
                elif imgBin[i, j, k] == 13:
                    img[i, j, k, :] = lblDict["fence"]
                elif imgBin[i, j, k] == 14:
                    img[i, j, k, :] = lblDict["fence-pole"]
                elif imgBin[i, j, k] == 15:
                    img[i, j, k, :] = lblDict["person"]
                elif imgBin[i, j, k] == 16:
                    img[i, j, k, :] = lblDict["dog"]
                elif imgBin[i, j, k] == 17:
                    img[i, j, k, :] = lblDict["car"]
                elif imgBin[i, j, k] == 18:
                    img[i, j, k, :] = lblDict["bicycle"]
                elif imgBin[i, j, k] == 19:
                    img[i, j, k, :] = lblDict["tree"]
                elif imgBin[i, j, k] == 20:
                    img[i, j, k, :] = lblDict["bald-tree"]
                elif imgBin[i, j, k] == 21:
                    img[i, j, k, :] = lblDict["ar-marker"]
                elif imgBin[i, j, k] == 22:
                    img[i, j, k, :] = lblDict["obstacle"]
                elif imgBin[i, j, k] == 23:
                    img[i, j, k] = lblDict["conflicting"]
        count += 1
        if count % 15 == 0:
            print("Converted {} images to 3D".format(count))
    return img

@njit(parallel=True)
def rgb2oneDimLabel(img: ImageSegCollection) -> ImageSegBinaryCollection:
    """
    Function to convert 3D ground truth images to 1D numeric values
    Input:
        Numpy array of 3D ground truth images. Input must be (numImg, widht, height, 3)
    Returns:
        Numpy array with 1D images (numImg, widht, height, 1) with the followig codification:
        00 -> unlabeled
        01 -> paved-grass
        02 -> dirt
        03 -> grass
        04 -> gravel
        05 -> water
        06 -> rocks
        07 -> pool
        08 -> vegetation
        09 -> roof
        10 -> wall
        11 -> window
        12 -> door
        13 -> fence
        14 -> fence-pole
        15 -> person
        16 -> dog
        17 -> car
        18 -> bicycle
        19 -> tree
        20 -> bald-tree
        21 -> ar-marker
        22 -> obstacle
        23 -> conflicting

    """
    imgBin = np.zeros((img.shape[0],img.shape[1],img.shape[2], 1), dtype=np.int16)
    for i in prange(img.shape[0]):
        for j in prange(img.shape[1]):
            for k in prange(img.shape[2]):
                if np.array_equal(img[i, j, k, :], [0, 0, 0]):
                    imgBin[i,j] = 0
                elif np.array_equal(img[i, j, k, :], [128, 64, 128]):
                    imgBin[i,j] = 1
                elif np.array_equal(img[i, j, k, :], [0, 76, 130]):
                    imgBin[i,j] = 2
                elif np.array_equal(img[i, j, k, :], [0, 102, 0]):
                    imgBin[i,j] = 3
                elif np.array_equal(img[i, j, k, :], [87, 103, 112]):
                    imgBin[i,j] = 4
                elif np.array_equal(img[i, j, k, :], [168, 42, 28]):
                    imgBin[i,j] = 5
                elif np.array_equal(img[i, j, k, :], [30, 41, 48]):
                    imgBin[i,j] = 6
                elif np.array_equal(img[i, j, k, :], [89, 50, 0]):
                    imgBin[i,j] = 7
                elif np.array_equal(img[i, j, k, :], [35, 142, 107]):
                    imgBin[i,j] = 8
                elif np.array_equal(img[i, j, k, :], [70, 70, 70]):
                    imgBin[i,j] = 9
                elif np.array_equal(img[i, j, k, :], [156, 102, 102]):
                    imgBin[i,j] = 10
                elif np.array_equal(img[i, j, k, :], [12, 228, 254]):
                    imgBin[i,j] = 11
                elif np.array_equal(img[i, j, k, :], [12, 148, 254]):
                    imgBin[i, j] = 12
                elif np.array_equal(img[i, j, k, :], [153, 153, 190]):
                    imgBin[i, j] = 13
                elif np.array_equal(img[i, j, k, :], [153, 153, 153]):
                    imgBin[i, j] = 14
                elif np.array_equal(img[i, j, k, :], [96, 22, 255]):
                    imgBin[i, j] = 15
                elif np.array_equal(img[i, j, k, :], [0, 51, 102]):
                    imgBin[i, j] = 16
                elif np.array_equal(img[i, j, k, :], [150, 143, 9]):
                    imgBin[i, j] = 17
                elif np.array_equal(img[i, j, k, :], [32, 11, 119]):
                    imgBin[i, j] = 18
                elif np.array_equal(img[i, j, k, :], [0, 51, 51]):
                    imgBin[i, j] = 19
                elif np.array_equal(img[i, j, k, :], [190, 250, 190]):
                    imgBin[i, j] = 20
                elif np.array_equal(img[i, j, k, :], [146, 150, 112]):
                    imgBin[i, j] = 21
                elif np.array_equal(img[i, j, k, :], [115, 135, 2]):
                    imgBin[i, j] = 22
                elif np.array_equal(img[i, j, k, :], [0, 0, 255]):
                    imgBin[i, j] = 23
    print("Images converted")
    return imgBin

if __name__ == "__main__":

    # Clear gpu session
    tf.keras.backend.clear_session()
    
    # Limit gpu memory. Unncomment to set limit to 2GB
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
                # tf.config.experimental.set_virtual_device_configuration(
                    # gpu,
                    # [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=2048)])
        except RuntimeError:
            print("Invalid GPU configuration")

    # Set where the channels are specified
    tf.keras.backend.set_image_data_format("channels_last")

    # data, lbl, test_dict = loadCsvFile('img.csv')
    train_data_src,train_labl_src, test_data_src,test_labl_src = loadCsvFile2('dogCat.csv')
    data,lbl = getItems(train_data_src,train_labl_src)
    # Normalize data
    # data = np.array(data, dtype=np.float32)
    data = data / 255.0
    # Convert labels from 3 to 1 dimension
    # lbl = np.array(lbl, dtype=np.int32)
    # lblBin = rgb2oneDimLabel(lbl)


    # Net params
    numClasses = 3
    nEpochs = 150
    batchSize = 32

    net: UNetX = UNetX(img_size=(224,224,3),n_filters=[32,64,128,256,256,128,64,32], n_classes=numClasses)
    net.summary()

    net.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])


    # Create checkpoints to save different models
    path = "resultTraining/weightsEpoch_{epoch:02d}_valLoss_{val_loss:.2f}.hdf5"
    path2 = "resultTraining/bestModel.hdf5"
    checkpoint = ModelCheckpoint(path, monitor='val_loss', verbose=1, save_best_only=True)
    checkpoint2 = ModelCheckpoint(path2, monitor='val_loss', verbose=1, save_best_only=True)
    callbackList = [checkpoint, checkpoint2]

    history = net.fit(data, lbl, validation_split=0.3, epochs=nEpochs, batch_size=batchSize, callbacks=callbackList)

    # Loss Curves
    plt.figure(figsize=[8,6])
    plt.plot(history.history['loss'],'r',linewidth=3.0)
    plt.plot(history.history['val_loss'],'b',linewidth=3.0)
    plt.legend(['Training loss', 'Validation Loss'],fontsize=18)
    plt.xlabel('Epochs ',fontsize=16)
    plt.ylabel('Loss',fontsize=16)
    plt.title('Loss Curves',fontsize=16)

    # save the losses figure
    plt.tight_layout()
    plt.savefig('resultTraining/losses.png')
    plt.close()

    # Accuracy Curves
    plt.figure(figsize=[8,6])
    plt.plot(history.history['accuracy'],'r',linewidth=3.0)
    plt.plot(history.history['val_accuracy'],'b',linewidth=3.0)
    plt.legend(['Training Accuracy', 'Validation Accuracy'],fontsize=18)
    plt.xlabel('Epochs ',fontsize=16)
    plt.ylabel('Accuracy',fontsize=16)
    plt.title('Accuracy Curves',fontsize=16)

    # save the accuracies figure
    plt.tight_layout()
    plt.savefig('resultTraining/accs.png')
    plt.close()

