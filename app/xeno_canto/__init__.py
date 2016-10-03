from urllib2 import Request, build_opener, HTTPError, URLError, urlopen
import simplejson
import couchdb
import hashlib
import sys

sys.path.insert(0,'..')
import config


'''
The xeno-canto API for downloading audio files
'''

# Global variables
BASE_URL = "http://www.xeno-canto.org/api/2/recordings?query="

NUM_R = "numRecordings"
NUM_SP = "numSpecies"
PG = "page"
NUM_PG = "numPages"
RECS = "recordings"

COUCHDB_SERVER="http://bitmad:mylife4aiur@localhost:5984/"
DATABASE_NAME="db_bird"

SYSTEM_ADMIN="rocklee.au@foxmail.com"

'''
This method gets the couchdb connection for storing the data latter on
'''
def get_db():
    couch_server = couchdb.Server(COUCHDB_SERVER)
    if DATABASE_NAME not in couch_server:
        couch_server.create(DATABASE_NAME)
    db_bird = couch_server[DATABASE_NAME]
    return db_bird

def get_bird_code(bird_name):
    for i in range(len(config.BIRD_NAME_LIST)):
        if bird_name== config.BIRD_NAME_LIST[i]:
            return i
    # not found
    return -1


# Class that contains all params and methods for querying the db
class XenoCantoObject:
    # Initialize some empty parameters
    def __init__(self):
        self.name = ""
        self.tags = {
            "gen": "",
            "rec": "",
            "cnt": "",
            "loc": "",
            "rmk": "",
            "lat": "",
            "lon": "",
            "box": "",
            "also": "",
            "type": "",
            "nr": "",
            "lic": "",
            "q": "",
            "q<": "",
            "q>": "",
            "area": "",
            "since": "",
            "year": "",
            "month": "",
        }
        self.query_url = ""

    # Sets the "name" parameter
    def setName(self, name):
        self.name = name;

    # Sets a "tag" parameter
    def setTag(self, key, val):
        self.tags[key] = val

    # Makes a query url from the "name" and "tag"
    def makeUrl(self):
        name_url = self.name

        tag_url = ""
        for key, value in self.tags.iteritems():
            if value != "":
                tag_url += "%20" + key + ":\"" + value + "\""

        self.query_url = BASE_URL + name_url + tag_url
        print self.query_url

    # Performs HTTP GET request, returns JSON object
    def get(self):
        try:
            request = Request(self.query_url)
        except HTTPError as e:
            print e.code
            print e.read
        except URLError as e:
            print 'We failed to reach a server.'
            print 'Reason: ', e.readon
        else:
            opener = build_opener()
            f = opener.open(request)
            json_obj = simplejson.load(f)
            return json_obj

    # Decodes JSON object into its components and sets them as class variables
    def decode(self, json):
        self.num_recs = json[NUM_R]
        self.num_sp = json[NUM_SP]
        self.page = json[PG]
        self.num_pages = json[NUM_PG]
        self.recs = json[RECS]

    # Downloads all audio files in the 'recs' class variable
    # while setting up the connection to couchdb and store the necessary data for latter usages
    def download_audio(self, audio_dir):
        for idx, rec in enumerate(self.recs):

            # the rec obj should contain the meta data we are interested in ,
            # build an instance for rec that interacts with couchdb, and store the file to local disk


            rec_url = rec['file']

            print rec

            conn = urlopen(rec_url)
            file_name = audio_dir + rec['en'] + '_' + rec['id'] + '.mp3'
            f = open(file_name, 'wb')
            size = int(conn.info().getheaders("Content-Length")[0])

            block_size = 8192
            while True:
                buf = conn.read(block_size)

                if not buf:
                    break

                f.write(buf)

            f.close()
            print "Wrote %d/%s" % (idx + 1, self.num_recs)

            # get the md5 of the file we just downloaded and stored
            with open(file_name) as file_to_check:
                # read contents of the file
                data = file_to_check.read()
                # pipe contents of the file through
                md5_returned = hashlib.md5(data).hexdigest()

            file_to_check.close
            # get db connection
            bird_db = get_db()

            doc = {
                "type": "record",
            # this is the file label that distinguish the user account information from audio records
                "training_data": "true",
            # this boolean tells if a record belongs to training data or user uploaded category
                "client": "browser",  # here the client could be one of ['browser','android','ios']
                "file_path": file_name,
                "md5":md5_returned,
                "location":rec['loc'],
                "longitude":rec['lng'],
                "latitude":rec['lat'],
                "evaluation":"",
                "submitted_by":SYSTEM_ADMIN,
                "date":rec['date'],
                "time":rec['time'],
                "estimation_rank":{},
                "confidence": "true",
                "top_estimation_code":get_bird_code(rec['en']),
                "top_estimation_bird":rec['en'], # this could be latter expanded to a more mature json with more information
                "user_comment":"This audio file is downloaded from Xeno-Canto.com!",
                "expert_request_status":"not", # the request status could one of ['not','pending','classified','completed']
                "expert_comment":"This audio file is downloaded from Xeno-Canto.com!"
            }

            bird_db.save(doc)
