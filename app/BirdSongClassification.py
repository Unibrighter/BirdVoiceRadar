import pymongo
import sys
import argparse
from sklearn.mixture import GMM
#from features import mfcc
#import scipy.io.wavfile as wav
#from glob import glob
import os
import numpy as np
from scikits.audiolab import Sndfile
from MFCC import melScaling
import random
from sklearn.linear_model import LogisticRegression
from sklearn import cross_validation
from sklearn.metrics import accuracy_score, classification_report

framelen=1024
fs = 44100.0

'''
This class contains functions to do feature extraction, cross validation, and so on
'''

class BirdSong:

    def __init__(self):
        self.mfccMaker = melScaling(int(fs), framelen/2, 40)
        self.mfccMaker.update()

    '''
    Convert a file to features. Take the file location as input and return a numpy array
    '''
    def file_to_features(self,wavpath):

        sf = Sndfile(wavpath, "r")
        window = np.hamming(framelen)
        features = []
        while(True):
                try:
                    chunk = sf.read_frames(framelen, dtype=np.float32)
                    if len(chunk) != framelen:
                        print("Not read sufficient samples - returning")
                        break
                    if sf.channels != 1:
                        chunk = np.mean(chunk, 1) # mixdown
                    framespectrum = np.fft.fft(window * chunk)
                    magspec = abs(framespectrum[:framelen/2])

                    # do the frequency warping and MFCC computation
                    melSpectrum = self.mfccMaker.warpSpectrum(magspec)
                    melCepstrum = self.mfccMaker.getMFCCs(melSpectrum,cn=True)
                    melCepstrum = melCepstrum[1:]   # exclude zeroth coefficient
                    melCepstrum = melCepstrum[:13] # limit to lower MFCCs
                    framefeatures = melCepstrum
                    features.append(framefeatures)

                except RuntimeError:
                    break

        sf.close()
        return np.array(features)

    '''
    Do 10 folds cross validation, print classifier, accuracy, and classification report
    '''
    def do_multiple_10foldcrossvalidation(self,clf,data,classifications):
        predictions = cross_validation.cross_val_predict(clf, data,classifications, cv=10)
        print clf
        print "accuracy"
        print accuracy_score(classifications,predictions)
        print classification_report(classifications,predictions)
    '''
    Fetch features from database, and store the features into a dictionary
    '''
    def get_feature_dic_mongodb(self,mongo_path):
        connection = pymongo.MongoClient(mongo_path)
        # get a handle to the bird database
        db = connection.bird
        birdFeature = db.birdFeature

        dic={}
        try:
            cursor = birdFeature.find({})

        except Exception as e:
            print "Unexpected error:", type(e), e

        count = 0
        for doc in cursor:
            count += 1
            dic[doc['_id']]=doc['feature']

        #print count

        return dic
    '''
    Get a dictionary of features for all the files in the files_list.
    files_list is a list of file locations.
    A dictionary of features is returned
    '''
    def get_feature_dic(self,files_list):
        dic={}
        for a_file in sorted(files_list):
            mfcc_feat=self.file_to_features(a_file)
            dic[a_file]=mfcc_feat

        return dic
    '''
    normed_features returns the normalized features
    dic: a dictionary of features to be normalized
    means: a vector of means
    invstds: a vector of inversed standard deviations
    return: a dictionary of normalized features
    '''
    def normed_features(self, dic,means,invstds):

        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-c', '--charsplit', default='_', help="Character used to split filenames")
        args = vars(parser.parse_args())
        normedFeatures = {}
        for aLabel, feature in dic.items():
            label = os.path.basename(aLabel).split(args['charsplit'])[0]
            #print label
            if label not in normedFeatures:
                normedFeatures[label] = (feature-means)*invstds#.tolist()
            else:
                normedFeatures[label] = np.vstack((normedFeatures[label], (feature-means)*invstds))  #.tolist()

        return normedFeatures

    '''
    Train a gmm for each key in normedData dictionary
    '''
    def train_the_model(self, normedData):

        gmm = {}
        for aLabel in normedData.keys():
            gmm[aLabel] = GMM(n_components=10)
            gmm[aLabel].fit(normedData[aLabel])

        return gmm

    '''
    Test the models using a dictionary of features.
    dic2: a dictionary of features to be tested. Keys are the file names.
    gmm: a dictionary of gmm models
    return: the number of correct predictions and total number of files, the predicted labels and actual
    labels
    '''
    def test(self,dic2,gmm):
        actual_labels=[]
        predicted_labels=[]
        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-c', '--charsplit', default='_', help="Character used to split filenames")
        args = vars(parser.parse_args())
        i=0
        n=len(dic2)
        for a_file in dic2:
            best_label = ''
            best_likelihood = -9e99
            likelihood_list=[]
            for label, agmm in gmm.items():
                likelihood = agmm.score_samples(dic2[a_file])[0]
                likelihood = np.sum(likelihood)
                likelihood_list.append(
                        likelihood)

                #print(ll,'ll')
                if likelihood > best_likelihood:
                    best_likelihood = likelihood

                    best_label = label

            likelihood_list=sorted(likelihood_list)

            #confidence


            #print(likelihood_list[len(likelihood_list)-2]/(likelihood_list[len(likelihood_list)-2]+likelihood_list[len(likelihood_list)-1]),'confidence')

            predicted_labels.append(best_label)
            actual_labels.append(os.path.basename(a_file).split(args['charsplit'])[0])
            if best_label == (os.path.basename(a_file).split(args['charsplit'])[0]):
                #print('prediction correct',best_label)
                i = i + 1
            '''
            else:
                print 'predicion wrong predicted',best_label,(os.path.basename(a_file).split(args['charsplit'])[0])
            '''

        print(i,float(i)/n,'accuracy')

        return i, n,predicted_labels,actual_labels

    '''
    predict the bird species for one file.
    '''
    def predict_one_bird(self,mfcc_feature,gmm):
        best_label = ''
        best_likelihood = -9e99
        likelihood_list=[]
        for label, agmm in gmm.items():
            likelihood = agmm.score_samples(mfcc_feature)[0]
            likelihood = np.sum(likelihood)
            likelihood_list.append(
                    likelihood)

            if likelihood > best_likelihood:
                best_likelihood = likelihood
                best_label = label

        likelihood_list=sorted(likelihood_list)

        confidence=likelihood_list[len(likelihood_list)-2]/(likelihood_list[len(likelihood_list)-2]+likelihood_list[len(likelihood_list)-1])
        print likelihood_list[len(likelihood_list)-2],likelihood_list[len(likelihood_list)-1]
        print best_label,' for one file test'
        return best_label,confidence

    '''
    Calculate n folds cross validation
    '''

    def n_fold_cross_validation(self, num_fold,dic,means,invstds):
        num_files=len(dic)
        file_list=dic.keys()
        test_dic=[]
        train_dic=[]
        correct=0
        total=0

        actual_labels=[]
        predicted_labels=[]

        for fold in range(num_fold):
            test_dic.append({})
            train_dic.append({})
            test_file=[]
            for i in random.sample(range(0,num_files), num_files/num_fold):
                test_dic[fold][file_list[i]]=dic[file_list[i]]
                test_file.append(file_list[i])
            test_file_set=set(test_file)
            for file in file_list:
                if file not in test_file_set:
                    train_dic[fold][file]=dic[file]

        for fold in range(num_fold):
            print fold
            normed_train=self.normed_features(train_dic[fold],means,invstds)
            gmm =self.train_the_model(normed_train)

            for test in test_dic[fold]:
                test_dic[fold][test]=(test_dic[fold][test]-means)*invstds

            num_correct,num_total,alabels,plabels=self.test(test_dic[fold],gmm)

            correct+=num_correct
            total+=num_total
            actual_labels=actual_labels+alabels
            predicted_labels=predicted_labels+plabels
        print classification_report(actual_labels,predicted_labels)
        return float(correct)/total


    def logistic_regression_test_one(self,clf, test_data,label):


        prob_list=np.asarray(clf.predict_proba(test_data))
        prob_list=prob_list.sum(axis=0)

        print prob_list

        best_label=''
        best_prob=-9e99
        for index,prob in enumerate(prob_list.tolist()):
            if prob > best_prob:
                best_prob=prob
                best_label=clf.classes_[index]

        if best_label==label:
            return 1
        else:
            return 0












if __name__ == '__main__':

    birdsong=BirdSong()
    dic=birdsong.get_feature_dic_mongodb("mongodb://localhost")
    allconcat = np.vstack((dic.values()))
    means = np.mean(allconcat, 0)
    invstds = np.std(allconcat, 0)
    for i, val in enumerate(invstds):
        if val == 0.0:
            invstds[i] = 1.0
        else:
            invstds[i] = 1.0 / val



    print birdsong.n_fold_cross_validation(7,dic,means,invstds)


    '''
    #using test files from another folder
    normedTrain=birdsong.normed_features(dic,means,invstds)
    gmm =birdsong.train_the_model(normedTrain)
    print(len(gmm) ,'len gmm')

    files_list = glob(os.path.join('wavs2', '*.wav'))

    dic2={}
    for a_file in sorted(files_list):
        #print a_file

        mfcc_feat=birdsong.file_to_features(a_file)
        mfcc_feat=(mfcc_feat-means)*invstds
        dic2[a_file]=mfcc_feat

    birdsong.test(dic2,gmm)



    #test for one file

    mfcc_feat=birdsong.file_to_features('wavs2/BrushCuckoo_34.wav')
    mfcc_feat=(mfcc_feat-means)*invstds

    birdsong.predict_one_bird(mfcc_feat,gmm)
    '''

#logistic regression ----------------
'''

    trn_data=[]
    trn_data_labels=[]

    for bird in normedTrain:
        for feature in normedTrain[bird]:

            trn_data_labels.append(bird)
            trn_data.append(feature)

    print len(trn_data)
    print len(trn_data_labels)

    trn_data_labels=np.asarray(trn_data_labels)
    trn_data=np.asarray(trn_data)
    clf=LogisticRegression()
    #birdsong.do_multiple_10foldcrossvalidation(clf,trn_data,trn_data_labels)
    clf.fit(trn_data,trn_data_labels)

    files_list = glob(os.path.join('wavs2', '*.wav'))

    dic2={}
    for a_file in sorted(files_list):
        #print a_file

        mfcc_feat=birdsong.file_to_features(a_file)
        mfcc_feat=(mfcc_feat-means)*invstds
        dic2[a_file]=mfcc_feat

    n_correct=0
    n_total=len(dic2)
    for a_file in dic2:
        label=os.path.basename(a_file).split('_')[0]
        n_correct+= birdsong.logistic_regression_test_one(clf,dic2[a_file],label)

    print 'logistic regression accuracy',float(n_correct)/n_total
'''





