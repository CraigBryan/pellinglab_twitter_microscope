class Receiver(object):
    """
    This is a baseclass that is not meant to be instantiated.
        
    Wrapper object that allows the router to store different route-to locations
    such as arduino boards, twitter, gui. Receivers take the transactions and
    process them. Concrete receivers are subclasses of this one.
        
    Attributes:
        router: A reference to the router object that sends transactions and takes 
                transaction requests.
        r_id: The id that the router uses to route transactions to a receiver
    """
    
    def __init__(self, router, r_id):
        """
        Initializes every receiver object to give them an id and a reference to the
        router.
            
        Args:
            router: A reference to the router object that sends transactions and takes 
                    transaction requests.
            r_id: The id that the router uses to route transactions to a receiver
        """
        super(Receiver, self).__init__()
        self.router = router
        self.r_id = r_id
    
    def check_id(self, i):
        """
        A method the router uses to determine whether or not to route a transaction to
        a certain receiver. This method allows for transactions to have more than one 
        destination receiver.
            
        Args:
            i: The id to check against. It is either a list or string
        """
        if isinstance(i, basestring):
            if i == self.r_id:
                return True
            else:
                return False
        else:
            if i in self.r_id:
                return True
            else:
                return False
                
        
    def process_transaction(self, transaction):
        """
        The method that the router calls to get a receiver to process a transaction.
        
        Args:
            transaction: the transaction to be processed by the receiver.
        """
        raise NotImplementedError() 
    
    def cleanup(self):
        """
        The method that the router when something goes wrong, used to free local resources
        (ie serial connections, cameras)
        """
        pass   
        

                   
        
     



                                            

