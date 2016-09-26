from xeno_canto.__init__ import *
import os

#Run this code to download audio files using xeno-canto API


# the names of the birds we want to download
name_list=[
    'Brush%20Cuckoo','Australian%20Golden%20Whistler','Eastern%20Whipbird','Grey%20Shrikethrush','Pied%20Currawong',
           'Southern%20Boobook','Spangled%20Drongo','Willie%20Wagtail']


for name in name_list:
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


    # Download all audio files like this
    rec_dir = os.path.dirname(os.path.realpath(__file__)) + "/audio/"
    xc_obj.download_audio(rec_dir)



