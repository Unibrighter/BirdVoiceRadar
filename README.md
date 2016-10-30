#Bird Species Recognition System Using Audio Data

## Introduction
Species recognition plays a critical role in many nature science researches and studies. Among many features used for identification reference, audio is a common one that can be easily collected with mobile devices and internet support. This project aims at building and establishing a recognition model system that gives prediction result based on the audio data submitted to the server, and provide easy access to the prediction engines for its users on different mobile platforms. By taking advantage of the machine learning methodologies, clouding computing and service providing, we can give a fair estimation for the bird species across Australia, which may contribute great values to endangered species protection and other relevant researches. Also, system has a feature to use expert assistance to manually mark the difficult cases in which the results predicted by model do not reach the pre-set standards, which may benefit in training data collection and accuracy improvement in the future.

## Current System
The alive version of this project can be found on
http://115.146.90.254:5001/

Static Server is on
http://115.146.90.254:80/

CouchDB is on
http://115.146.90.254:5984/

## Deployment Instructions
If you plan to deploy the system on other virtual machine on Cloud. Here are the instruction to follow:

0. Make sure you have the right version of python, Nginx and CouchDB installed

1. Install pip for python and python_dev
> sudo apt-get install python-pip
> sudo apt-get install python-dev


2. Install the following packages in the right order using the command:
> pip install [packagename in the list]

	- flask
	- pymongo
	- numpy
	- scipy
	- sklearn
	- scikits.audiolab (this requires you have the compiled library installed before, if you have problems in this step ,visit https://github.com/cournape/audiolab/issues/7 for details)
	- flask_login
	- couchdb
	- peakutils

When all of the libraries are installed properly, you can start the server now.

3. Get the views ready in CouchDB

- _desing/record

> {
>   "all_training_and_upload": {
>       "map": "function (doc) {\n  if(doc.type==\"record\")\n  {\n    emit([doc.training_data,doc._id], doc);  \n  }\n  \n}"
>   },
>   "rank_by_time": {
>       "map": "function (doc) {\n  emit([doc.date, doc.time], doc);\n}"
>   },
>   "record_by_md5": {
>       "map": "function (doc) {\n  if(doc.type==\"record\")\n  {\n    emit(doc.md5, doc);  \n  }\n}"
>   },
>   "training_record": {
>       "map": "function (doc) {\n  if(doc.type=\"record\" && doc.training_data==\"true\")\n  {\n    emit(doc.md5, doc);\n  }\n}"
>   },
>   "upload_record": {
>       "map": "function (doc) {\n  if(doc.type=\"record\" && doc.training_data==\"false\")\n  {\n    emit(doc.md5, doc);\n  }\n}"
>   }
> }

---

- _design/account
> {
>       "account_by_email": {
>          "map": "function (doc) {\n  if(doc.type==\"account\")\n  {\n    emit(doc.email, doc);  \n  }\n}"
>       }

4. Configure Nginx Sever like the sample in the repository

5. Configure config.py in the root directory and set the right parameters according to the notes in that file


6. Then run webapp.py and the server is ready to go.


7. If you want to update the prediction model, you’ll need to follow the steps below:

	1. Run DownloadAudioFIles.py to download all the audio files to the “audio” folder.

	2. Convert the audio files to sample rate 44100Hz, “wav” format( I used iTunes for this). The file names are changed manually to the following format:
	 
		>AustralianGoldenWhistler_7.wav 

	where the string before “_” is the name of the bird.
	Store the files into a folder called “wav”

	3. Run populateDatabase.py to store features into the database. This might take a long time.

	4. Get the server ready and visit 
		> HOST:PORT/update

	and the system will general a new pickle file for the new model.

	5. Note that the default option has no other features mixed in the original GMM, if you wish to change this setting, please change the parameters in "update" route.
