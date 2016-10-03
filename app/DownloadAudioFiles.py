from xeno_canto.__init__ import *
import os
import sys
sys.path.insert(0,'..')
import config



#Run this code to download audio files using xeno-canto API

for name in config.BIRD_DOWNLOAD_LIST:
    # Audio recording quality tag
    q = "A"
    # Instantiate XenoCantoObject
    xc_obj = XenoCantoObject()

    # Set the class variables using these methods
    xc_obj.setName(name)
    xc_obj.setTag('q', q)

    # Create the query url based on the set parameters
    xc_obj.makeUrl()

    # Makes the HTTP GET request, returns the JSON response
    json_obj = xc_obj.get()

    # Sets the individual component of JSON response as class variables
    xc_obj.decode(json_obj)

    # Print out the class variables (JSON data)
    print "numRecs    : " + xc_obj.num_recs
    print "numSpecies : " + xc_obj.num_sp
    print "page       : %d" % xc_obj.page
    print "numPages   : %d" % xc_obj.num_pages

    # Here we need to add some codes to get the md5 hash of the file name, and store the meta data along with the new
    # file path, so that we can have a check on the files downloaded latter.


    # Download all audio files like this
    # rec_dir = os.path.dirname(os.path.realpath(__file__)) + "/audio_tmp/"
    xc_obj.download_audio(config.TRAINING_FILE_FOLDER)

