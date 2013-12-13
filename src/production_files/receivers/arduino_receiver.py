'''
Created on Sep 6, 2013

@author: Craig Bryan
'''

from serial import Serial, SerialException
from serial.tools import list_ports
from receiver import Receiver
from time import sleep


class ArduinoReceiver(Receiver):
    """
    This is a depreciated class. No longer in use in the production software.
    The functionality of this class has been moved into the camera_communicator class.
    
    A receiver that transmits data to and from an arduino board
        
    Attributes:
        router: A reference to the router object that sends transactions and takes 
                transaction requests.
        r_id: The id that the router uses to route transactions to this receiver
        ok_to_associate: A boolean that stops the router from stacking more than one 
                         "associate" transactions
        keywords: The list of keywords recognized by the router, and the receivers
        connections: A dictionary of keyword-Serial connection pairs, each keyword
                     is associated with an Arduino board, and therefore a Serial connection
            
    """
    
    def __init__(self, router, r_id, keywords):
        """
        On initialization, this receiver creates a transaction that sets its associations.
        This way, the first transaction this receiver processes will setup connections 
        with the peripheral boards.
            
        Args:
            router: A reference to the router object
            r_id: The id of this receiver (usually "arduino")
            keywords: A list of keywords that recognized by this receiver     
        """
        super(ArduinoReceiver, self).__init__(router, r_id)
        
        self.keywords = keywords
        self.connections = {}
        self.router.create_transaction(origin = self.r_id, to_id = self.r_id, 
                                  command = "associations", command_args = keywords)
        self.ok_to_associate = False
            
    def process_transaction(self, transaction):
        """
        Attempts to process an incoming transaction, is called by the router object.
            
        Args:
            transaction: A reference to a transaction object.
        Transaction commands:
            get: Takes a keyword from the transaction message, and a sample number,
                 then requests that information from the arduino board. If a keyword
                 is not recognized, a transaction to reset the associations with the 
                 boards is queued.
            associate: Communicates with the arduino boards and attempts to associate
                       keywords with serial connections with each board
        """
        
        if transaction.command == "get" or transaction.command == "set":
            #takes a get command with command_arg list of form [keyword, number]
            
            try:
                #grab the proper serial connection
                connection = self.connections[transaction.command_arg[0]]
                
                #write the sample number to the arduino
                connection.write(str(transaction.command_arg[1]))  
                        

            except KeyError:
                transaction.log("Keyword not recognized. Is the arduino " +
                            "board for \"%s\" connected?" %transaction.message[0])
                
                transaction.process(success = False) #ensures the transaction will be added again 
                
            except ValueError:
                transaction.log("Arduino board not connected. Check the port status + %s"
                                         %transaction.message[0])
                
                #queues a arduino board re-association if there is not one queued already
                if(self.ok_to_associate):
                
                    transaction.log("Resetting Arduino board interactions")
                                
                    self.router.create_transaction(origin = self.r_id, to_id = self.r_id, 
                                           command = "associations", command_args = self.keywords)
                    
                    self.ok_to_associate = False
                    
                                               
                transaction.process(success = False) #ensures the transaction will be added again 
            
            except Exception, e:
            
                transaction.log("Unexpected Exception: %s" %str(e))
                raise    
            else: 
            
                if transaction.command == "get":
                    sleep(10) #to give the arduino time to respond
                    
                    reading = connection.read(connection.inWaiting())
                    
                    #requeue a the transaction, with the outgoing message
                    transaction.command_args = "%s reading from sample %d: %s" % (
                                                                transaction.command_args[0].capitalize(),
                                                                transaction.command_args[1], reading)
                    
                    transaction.to_id = transaction.origin
                    transaction.command = "post"
                    
                    transaction.process(success = True, finished = False)
                
                elif transaction.command == "set":
                    transaction.process()
        
        elif transaction.command == "associations":
            self._set_associations(transaction)
                   
        else:
            transaction.log(info = "Unknown command passed to arduino receiver: %s"
                                    % transaction.command)
    
    def cleanup(self):
        """
        Closes connections with any boards connected.
        """
        
        for board in self.connections:
            self.connections[board].close()
        del self.connections
            
    
    #Private Members
    def _set_associations(self, transaction):
        """
        Finds all the serial ports, and sends a probe string.
        The keyword that is returned is that arduino's keyword
        """
        
        self.ok_to_associate = True
        
        keywords = transaction.command_args
        
        #dictionary for the various serial connections with their associated keywords
        self.connections = {}
        
        #get all the ports
        ports = [port[0] for port in list_ports.comports()] 
        
        #trim the bluetooth ports
        for p in ports[:]:
            if "bluetooth" in p.lower():
                ports.remove(p)
        
        #make a connection to each port, and if successful, send the config signal
        for p in ports:
            try:
                connection = Serial(p, 19200)
                sleep(4) #TODO find for reliable way of getting this?
                connection.flushInput()
                connection.write("probe")
                sleep(1)
                keyword = connection.read(connection.inWaiting()).rstrip()
                
                if(keyword == "failed"):
                    transaction.log(info = "Probe signal failed to %s" %p)
                
            except SerialException:
                transaction.log(info = "Serial connection failure to %s" %p)
                
            if keyword in keywords:
                self.connections[keyword] = connection
            elif keyword == "":
                pass 
            else: 
                transaction.log(info = "Unexpected keyword \"%s\" received from arduino board"
                                                                                   % keyword)
            
        transaction.process(success = True)
