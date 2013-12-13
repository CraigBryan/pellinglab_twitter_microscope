from collections import deque
from logger import Logger
from receivers import twitter_receiver, camera_receiver, filemanager_receiver
from receivers import flickr_receiver, gui_receiver, translator_receiver 
from transaction import Transaction
import utils
from copy import deepcopy
import os
                
class Router(object):
    """
        This class initializes all receivers, and creates and routes transactions.
        
        The driving method of the program is the next() function. It takes the next
        transaction from the transaction queue and processes it.
    """
    
    def __init__(self, attempt_threshold = 5, logger = None, gui_communicator = None):
        """           
           Args:
            attempt_threshold: The max number of times one transaction will appear on the
                               transaction queue. Defaults to 5.
            logger: Allows use of a non-default named logger. A default logger is used
                    if this parameter is not supplied.
            gui_communicator: The communicator for a GUI for local use of the system.
                              This initialized before the router, unlike the rest of
                              the communicators.
        """
        
        self.settings = utils.read_config_dict("Router")
        
        self._transactions = deque()
        
        self._receivers = []
        
        if logger is None:
            self._logger = Logger()
        else:
            self._logger = logger
            
        self._create_receivers(gui_communicator) 
        self._attempt_threshold = attempt_threshold
    
    def create_transaction(self, to_id = None, command = None, 
                                        command_args = None, origin = None):
        """
        Creates a new transaction and adds it to the transaction queue.
            
        Args:
            origin: The twitter user (or receiver) this transaction originated
                    from
            to_id: The id of the receiver this transaction will be routed to
            command: The string command word that the receiver will understand
            command_args: Addition arguments for the command
        """
        
        self._transactions.append(Transaction(self._logger, 
                                              to_id, 
                                              command, 
                                              command_args, 
                                              origin))
        
    def clone_transaction(self, original_transaction, to_id = None, 
                          command = None, command_args = None):
        """
        Deep copies an existing transaction, allowing changing of any routing
        parameter or carried information. The origin remains constant. A deep
        copy of a transaction avoids duplication of the logger.
        
        Args:
            original_transaction: The transaction being copied
            to_id: A new receiver id to send this transaction to
            command: The new command being carried by the transaction 
            command_args: The new command arguments being carried by the 
                          transaction
        """
        
        new_transaction = deepcopy(original_transaction)
        
        if to_id is not None:
            new_transaction.to_id = to_id
        if command is not None:
            new_transaction.command = command
        if command_args is not None:
            new_transaction.command_args = command_args
            
        new_transaction.finished = new_transaction.processed = False
        new_transaction.attempts = 0
        
        self._transactions.append(new_transaction)
       
    def next(self):
        """
        The method that drives the router. It will process the next transaction in the queue.
        If there are no transaction in the queue, transactions to pull tweets and gui commands
        are queued. Any transactions that fail to process are added to the queue again, but
        will not be added more than the attempt_threshold.
        """
        
        if len(self._transactions) > 0:
            transaction = self._transactions.popleft()
            
            for rec in self._receivers:
                if rec.check_id(transaction.to_id):
                    rec.process_transaction(transaction)
                                                        
            if transaction.processed and not transaction.finished:
                transaction.requeue()
                self._transactions.append(transaction)
                
            elif not transaction.processed:
                if transaction.attempts < self._attempt_threshold:
                    self._transactions.append(transaction)
                    
                else:
                    self._logger.log("Transaction failed to process too many " + 
                                     "times: " + str(transaction))
        
        else: #no transaction to handle, lets find others
            #Poll the twitter receiver for new tweets
            self.create_transaction(to_id = "twitter", command = "update")
            
            #If a GUI is present, poll it for new requests
            if self.gui_communicator:
                self.create_transaction(to_id = "gui", command = "update")
    
    def reboot(self):
        """
        A system reboot command that all receivers can call. This ensures a controlled
        shutdown of all receivers. Unprocessed transactions are lost.
        """
        for rec in self._receivers:
            rec.cleanup()
            os.system("sudo reboot")
        
    ##Private members
    
    def _create_receivers(self, gui_communicator): 
        """
        Creates all the receivers.
        """
        
        #Only create a GUI receiver if the GUI exists
        if gui_communicator:
            self._receivers.append(gui_receiver.
                                   GuiReceiver(self, "gui", gui_communicator))
            
        self._receivers.append(twitter_receiver.
                               TwitterReceiver(self, "twitter"))
        
        self._receivers.append(translator_receiver.
                               TranslatorReceiver(self, "translator", 
                                                  self.settings['num_samples']))
        
        self._receivers.append(filemanager_receiver.
                               FileManagerReceiver(self, "filemanager"))
        
        self._receivers.append(flickr_receiver.
                               FlickrReceiver(self, "flickr"))
        
        self._receivers.append(camera_receiver.
                               CameraReceiver(self, "camera"))
        
        self._logger.log("Receivers created")
