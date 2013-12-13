'''
Created on Sep 9, 2013

@author: Craig Bryan
'''

from copy import deepcopy

class Transaction(object):
    """
    This is the object that allows the router to control passage of information between
    the various receivers. It also encapsulates the logging capability. The transaction
    tracks the number of unsuccessful attempts at processing the transaction, so it
    will not cause the transaction stack to be perpetually populated.
    
    Attributes:
        to_id: The receiver the transaction is heading to 
        command_arg: The arguments for receivers to read
        command: The action for the receiver to do 
        logger: A logger object that allows the transactions to encapsulate 
                the logging capabilities 
        processed: A state boolean indicating whether the transaction is 
                   finished or not
        attempts: The number of times a receiver has attempted to process this
    """
    
    def __init__(self, logger, to_id = None, command = None, 
                            command_args = None, origin = None, attempts = 0):
        """
        TODO docstring
        """
        
        self.to_id = to_id
        self._logger = logger
        self.command = command
        self.command_args = command_args
        self.processed = False
        self.attempts = attempts
        self._origin = origin
        self.finished = False
                 
    def process(self, success, finished = True, allow_log = True):
        """
        The method that the receivers that are sent this transaction need to call
        whenever they finish a processing attempt.
        
        Args: 
            success: True if the receiver was able to handle this transaction.
            allow_log: True by default, allows to turn off logging of repetitive 
                       transactions (eg twitter update)
            finished: True if this is the end of the transaction's job
        """

        if success:
            self.processed = True
            self.finished = finished
            if allow_log:
                self._logger.log("%s to %s processed with args: %s" %(self.command, self.to_id, 
                                                                       self.command_args))
        else:
            self.attempts += 1
                                                                                    
    def log(self, info = "Not specified"):
        """
        A method that allows any class receiving a transaction to log errors or data
        
        Args:
            info: the message to be logged
        """
        
        self._logger.log("\"%s\". Originated from: %s receiver" % (info, self.to_id))    
        
    def requeue(self):
        """
        Mostly a placeholder to allow for future extension of functionality
        """
        
        self.processed = False
        self.attempts = 0
    
    def __deepcopy__(self, memo):
        """
        An override of __deepcopy__ to allow cloning of transactions but allowing
        the logger to be shared across all transactions
        """
        
        cls = self.__class__
        
        result = cls.__new__(cls)
        
        memo[id(self)] = result
        
        for k, v in self.__dict__.items():
            if k == '_logger': #skips the deep copy of the logger
                setattr(result, k, v)
                continue
            
            setattr(result, k, deepcopy(v, memo)) #deep copies all other attributes
            
        return result
    
    #override of __str__ for pretty representations when logging
    def __str__(self):
        return "Transaction: Command: %s From: %s To: %s Message: %s Attempts: %s" % (
                      self.command, self.origin, self.to_id, self.command_args, self.attempts)
    
    @property                  
    def origin(self):
        return self._origin