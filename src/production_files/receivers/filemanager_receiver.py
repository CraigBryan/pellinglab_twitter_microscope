'''
Created on Sep 6, 2013

@author: Craig Bryan
'''

import os
from receiver import Receiver

class FileManagerReceiver(Receiver):
    """
    A receiver that allows the router and other receivers to change files and
    directories locally. Not used to its full potential, nor is fully implemented.
    """
    
    def __init__(self, router, r_id):        
        super(FileManagerReceiver, self).__init__(router, r_id)
        
    def process_transaction(self, transaction):
        """
        Method called by the router to deal with transactions routed to this receiver.
        
        Args:
            Transaction: The transaction to be processed.
            
        Commands:
            mkdir: Creates a directory locally.
            store: Not implemented.
        """
        if transaction.command == "mkdir":
            try:
                os.makedirs(transaction.command_args)
            except OSError:
                if not os.path.isdir(transaction.command_args):
                    raise 
            transaction.process(success = True)
        elif transaction.command == "store":
            raise NotImplementedError()
        
        else: 
            transaction.log(info = "Unknown command passed to file receiver: %s"
                                    % transaction.command)        

