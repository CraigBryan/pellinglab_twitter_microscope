'''
Created on Sep 6, 2013

@author: Craig Bryan
'''

from receiver import Receiver
from flickrapi import FlickrAPI
from flickrapi import shorturl
from production_files import utils
import os

class FlickrReceiver(Receiver):
    """
    The reciever that deals with storing images online. Uses the flickr API to 
    store images in a Flickr account.
    
    Attributes:
        _photo_dir: The name of the local directory that images are stored.
        flickr: The FlickrCommunicator that interfaces with the Flickr API.
    """
    
    def __init__(self, router, r_id,
                 app_name = "My super-duper Flickr app", flickr_auth = None):
        """
        Initialize the image directory name, and ensure it exists. Sets up the
        interface with the Flickr API.
        
        Args:
            router: A reference to the router that this receiver is associated with.
            r_id: The string that the router refers to this receiver with.
        """
        super(FlickrReceiver, self).__init__(router, r_id)
        
        self._photo_dir = utils.get_image_dir()
        
        self.flickr = FlickrCommunicator()
                                                
        if not os.path.isdir(self._photo_dir):
            self.router.create_transaction(origin = self.r_id, 
                                           to_id = "filemanager", 
                                           command = "mkdir", 
                                           command_args = self._photo_dir)
    
    def process_transaction(self, transaction):
        """
        The method the router calls when a transaction is routed to this receiver.
        
        Args:
            transaction: The transaction that is being processed by the receiver.
            
        Commands:
            store: Saves the image to the associated Flickr account. Then passes
                the link to the newly uploaded image to the the GUI or Twitter 
                (depending on where the request for the image came from) with a
                new 'post' command.
        """
        
        if transaction.command == "store":
            link = self.flickr.upload_photo(transaction.command_args[0], 
                                       transaction.command_args[1],
                                       transaction.command_args[2])
            
            transaction.process(success = True, finished = False)
                                       
            if transaction.origin == "gui":                 
                transaction.to_id = transaction.origin
            else:
                transaction.to_id = "twitter"
                
            transaction.command = "post"
            transaction.command_args = link
                        
        else: 
            transaction.log(info = "Unknown command passed to flickr receiver: %s"
                                    % transaction.command)
                                    
    def cleanup(self):
        del self.flickr
    
class FlickrCommunicator(object):
    """
    The interface to the Flickr API. 
    
    Attributes:
        flickr: The FlickrAPI object that allows communication with Flickr services.
        app_name: The application name to be assoicated with the uploaded images.
    """

    def __init__(self):
        """
        Initializes the link between this app and Flickr API using stored 
        configuration values. Due to the way the Flickr API authorizes, the 
        first time a set of credentials are used on a given system, this must 
        be initialized within a context that allows a browser window to open and
        username and password to be entered.
        """
        
        config_dict = utils.read_config_dict("FlickrCommunicator")
        
        self.flickr = FlickrAPI(config_dict['api_key'], 
                                config_dict['api_secret'])
        
        self.app_name = config_dict['app_name']
        
        (token, frob) = self.flickr.get_token_part_one(perms='write')
        if not token: 
            raw_input("Press ENTER after you authorized this program")
            
        self.flickr.get_token_part_two((token, frob))

    def upload_photo(self, filename, sample_num, timestamp):
        """
        Post an image to the Flickr account.
        
        Args:
            filename: The filename of the image to be uploaded.
            sample_num: The sample number associated with the image.
            timestamp: A string representing the date and time the image was taken.
            
        Returns:
            A shortened url that points to the image uplaoded to Flickr.
        """
        
        #build a description string
        time, date = self._get_timestamp_strings(timestamp)
        
        description = "Sample %d taken at %s on %s" %(sample_num, time, date)
        
        #generate the tag string
        tags = "pellinglab, %s, 'sample %d'" %(self.app_name, sample_num)
        
        #generate the title string
        title = "Pellinglab image. %s" %date
        
        feedback = self.flickr.upload(filename = filename, 
                                    title = title, 
                                    description = description, 
                                    tags = tags)
        
        for elem in feedback:
            photoID = elem.text
        
        return shorturl.url(photoID)

    def _get_timestamp_strings(self, timestamp):
        """
        A helper method to create the time and date strings from a datetime 
        timestamp
        """
        
        months = {
                    1:"Jan",
                    2:"Feb",
                    3:"Mar",
                    4:"Apr",
                    5:"May",
                    6:"Jun",
                    7:"Jul",
                    8:"Aug",
                    9:"Sep",
                    10:"Oct",
                    11:"Nov",
                    12:"Dec"
                 }
        
        time = "%02d:%02d:%02d" %(timestamp.hour, timestamp.minute, timestamp.second)
                
        date = "%s %02d, %d" %(months[timestamp.month], timestamp.day, timestamp.year)
    
        return time, date