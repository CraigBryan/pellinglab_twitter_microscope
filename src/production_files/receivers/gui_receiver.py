'''
Created on Sep 6, 2013

@author: Craig Bryan
'''

from receiver import Receiver

class GuiReceiver(Receiver):
    """
    A receiver that allows the router to receive and send data to a local GUI.
    This is to allow local requests for images, without using the Twitter-based
    interface. No GUI is currently implemented, so this acts as a hook for later.
    
    Attributes:
        gui: The gui this receiver is communicating with. The gui must have a post
            method that allows data to be displayed, and a retreive_requests 
            method that allows pulling of a list of requests for images or information.
    """
    
    def __init__(self, router, r_id, gui):
        """
        Args:
            router: A reference to the router that this receiver is associated with.
            r_id: The string that the router refers to this receiver with.
            gui: The gui this receiver is communicating with.
        """
        super(GuiReceiver, self).__init__(router, r_id)
        
        self.gui = gui
    
    def process_transaction(self, transaction):
        """
        The method the router calls when a transaction is routed to this receiver.
        
        Args:
            transaction: The transaction that is being processed by the receiver.
            
        Commands:
            update: Pull any new requests from the GUI and post turn them into new 
                transactions.
            post: Send data to the GUI to display.
        """
        
        if transaction.command == "update":
            requests = self.gui.retrieve_requests()
            
            while len(requests) > 0:
                #requests are routed to the translator
                self.router.create_transaction(origin = self.r_id, to_id = "translator", 
                                          command = "parse", command_arg = requests.popleft())
                                          
            transaction.process(success = True, finished = True, allow_log = False) 
                        
        elif transaction.command == "post":
        
            self.gui.send_data(transaction.message)
            
            transaction.process(success = True, finished = True)
                   
        else:
            transaction.log(info = "Unknown command passed to gui receiver: %s"
                                    % transaction.command)
