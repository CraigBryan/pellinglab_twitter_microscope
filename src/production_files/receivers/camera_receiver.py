'''
Created on Sep 6, 2013

@author: Craig Bryan
'''

from receiver import Receiver
from camera_communicator import CameraCommunicator
from production_files import utils
import os

class CameraReceiver(Receiver):
    """
    The receiver that deals with transactions that call for sample images. Has
    a camera communicator instance that acts as the interface to the camera.
    
    Attributes:
        _photo_dir: The name of the directory where images are stored.
        _camera_comm: The camera_communicator instance that allows this receiver
            to capture images.
    """
    
    def __init__(self, router, r_id):
        """
        Creates the camera communicator and ensures the image directory exists.
        
        Args:
            router: A reference to the router that this receiver is associated with.
            r_id: The string that the router refers to this receiver with.
        """
        
        super(CameraReceiver, self).__init__(router, r_id)
        
        self._photo_dir = utils.get_image_dir()
        
        self._camera_comm = CameraCommunicator()
        
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
            get_image: Takes an image and stores it locally, then changes the 
                destination to an appropiate receiver to return the image to the
                user that requested it.
        """
        if transaction.command == "get_image":
             
            timestamp, filename = self._camera_comm.get_sample_image(
                                                  transaction.command_args[0])
            
            if(transaction.origin == "gui"):
                raise NotImplementedError("GUI not yet implemented")
                
            else:
                transaction.to_id = "flickr"
            
            transaction.command = "store"
            transaction.command_args = [filename, 
                                        transaction.command_args[0], 
                                        timestamp]
                                                                            
        else: 
            transaction.log(info = "Unknown command passed to camera receiver: " + 
                            "%s" % transaction.command)
    def cleanup(self):
        """
        Ensure local resources are freed.
        """
        self._camera_comm.cleanup()
        del self._camera_comm