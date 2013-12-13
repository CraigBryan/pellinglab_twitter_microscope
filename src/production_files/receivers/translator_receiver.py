'''
Created on Sep 6, 2013

@author: Craig Bryan
'''

from receiver import Receiver
from production_files import utils
import re

class TranslatorReceiver(Receiver):
    """
    A receiver that is responsible to translating tweet content into keywords and commands
    that the other receivers understand.
        
    Attributes:
       router: A reference to the router object that sends transactions and takes 
               transaction requests.
       r_id: The id that the router uses to route transactions to this receiver
       cmd_args_dict: A dictionary with commands as keys and a list of
                    possible arguments as values
       num_samples: The number of samples available to query.
    """
    
    def __init__(self, router, r_id, samples, keyword = "CommandArguments"):
        """
        Initializes the attributes of the translator
        
        Args:
            router: A reference to the router object using this receiver.
            r_id: The id of this receiver (usually "translator").
            samples: The number of samples being monitored.
            keyword: The name of the dictionary of command:[args] pairs for
                this translator to use.
        """
        super(TranslatorReceiver, self).__init__(router, r_id)
        
        self.cmd_args = utils.read_config_dict(keyword)
        self.num_samples = samples
        
        self.help_strings = utils.read_config_dict("HelpStrings")
        
        self.test_whitelist = utils.read_config_dict("TestWhiteList").values()
          
    def process_transaction(self, transaction): 
        """
        Attempts to process an incoming transaction, is called by the router object.
            
        Args:
            transaction: A reference to a transaction object.
            
        Raises:
            BadTweetCommandError: No commands, or an invalid command found in a tweet
            BadTweetArgError: An argument to a command is invalid.
            BadTweetSampleError: An invalid sample number was found in a tweet, or
                no sample number was found in a tweet.
            
        Commands:
            parse: Take a tweet and uses a regex to pull all the queries out. For each
                   query, a new transaction is made to the translator to translate that
                   command string.
            translate: Takes a single query, translates it into a command that can be understood by other  and creates the 
                       appropriate transaction.
        """
        
        if transaction.command == "parse": 
            try:
                num_parsed = self._parse(transaction)
            except BadTweetCommandError:
                transaction.log("No command strings found in query '%s'" 
                                %transaction.command_args)
                transaction.to_id = "twitter"
                transaction.command = "post"
                transaction.command_args = ("I cannot understand your tweet. "
                                            "Please tweet 'help() -s' for "
                                            "my command syntax")
                transaction.requeue()
            else:
                transaction.log("%d command strings parsed from twitter query '%s'"
                                %(num_parsed, transaction.command_args))
            
        elif transaction.command == "translate":
            try:
                self._translate(transaction)
            except BadTweetCommandError:
                transaction.log("Invalid command string in query '%s'"
                                %transaction.command_args)
                self.router.clone_transaction(transaction, to_id = "twitter",
                                  command = "post",
                                  command_args = ("'%s' contains no valid " 
                                  "command. Please tweet help() -c for a "
                                  "list of commands" 
                                  %transaction.command_args))
            except BadTweetArgError as e:
                transaction.log("Invalid command arguments in query '%s'"
                                %transaction.command_args)
                self.router.clone_transaction(transaction, to_id = "twitter",
                                  command = "post",
                                  command_args = ("The %s command does not take" 
                                                  " %s as an argument. ")
                                                  %(e.command, e.argument) + 
                                                  self.help_strings[e.command])
            except BadTweetSampleError:
                transaction.log("Invalid sample numbers in query '%s'"
                                %transaction.command_args)
                self.router.clone_transaction(transaction, to_id = "twitter",
                                  command = "post",
                                  command_args = ("Your tweet contains invalid"
                                                  " sample numbers. Please use"
                                                  " sample numbers between 1"
                                                  " and %d" %self.num_samples))
    
    def _parse(self, transaction):
        """
        Takes the raw tweet or other command string and breaks it into
        individual requests. Each individual request is used as the command
        arg for transactions. The original transaction is modified for the
        first request found, and then for further requests found, the
        original transaction is cloned and modified.
        
        Args:
            transaction: The transaction to be parsed.
        """
        
        parsing_regex = re.compile('[a-z]+\(\d*(?:\s*,\d*\s*)*\)(?:\s+-[a-z])*')
        command_strings = re.findall(parsing_regex, transaction.command_args)
            
        if not command_strings:
            transaction.log("No command string found in tweet: %s" 
                            %transaction.command_args)
            raise BadTweetCommandError()
        else:
            transaction.command = "translate"
            transaction.command_args = command_strings.pop()
            transaction.requeue()
            count = 1
            
            transaction.log("Command string found in tweet: %s" 
                            %transaction.command_args)
            
            for cmd_string in reversed(command_strings):
                transaction.log("Command string found in tweet: %s" 
                            %cmd_string)
                self._router.clone_transaction(transaction, 
                                               command_args = cmd_string)
                count += 1
            
            return count

    def _translate(self, transaction):
        """
        This method takes a single a transaction that has a single parsed
        command string in the form cmd(num1, num2, ..) -arg1 -arg2..
        It takes this string apart, and validates the commands, sample numbers,
        and arguments. If the all parts are valid, it reroutes the transaction 
        (cloning if more than one sample number is present) to the correct 
        receiver.
        
        Args:
            transaction: The transaction to be parsed.
        """
        
        content = transaction.command_args
        
        parsed_args = re.findall('-[a-z]', content)
        args = []
        for arg in parsed_args:
            args.append(arg.replace("-", ""))
            
        try:
            command = re.findall('^[a-z]+', content.lower())[0]
        except IndexError:
            raise BadTweetCommandError()
        samples = [int(s) for s in re.findall('\d+', content)]
        
        #Checking the validity of the pulled queries
        if not command in self.cmd_args:
            transaction.log("No valid command found in command string: %s"
                            %content)
            raise BadTweetCommandError()
    
        for arg in args:
            if not arg in self.cmd_args[command.lower()]:
                transaction.log("Bad argument found in command string %s"
                                %content)
                raise BadTweetArgError()
        
        if not samples:
            if not (command.lower() == "help" or command.lower() == "test"):
                transaction.log("Sample numbers missing from command string %s"
                                %content)
                raise BadTweetSampleError()
        
        if samples:
            for num in samples:
                if num <= 0 or num > self.num_samples:
                    transaction.log("Bad sample numbers in command string %s"
                                    %content)
                    raise BadTweetSampleError()
        
        #Calls the appropriate, non-public helper method.
        if command.lower() == "sample":
            self._camera_request(transaction, args, samples)
        elif command.lower() == "test":
            self._test_request(transaction, args)
        elif command.lower() == "help":
            self._help_request(transaction, args)
        
    def _camera_request(self, transaction, args, samples):
        """
        Helper method that Modifies the transaction to take an image, and clones 
        the transaction for the rest of the requests made.
        """
        
        transaction.to_id = "camera"
        transaction.command = "get_image"
        transaction.command_args = [samples.pop(), args]
        transaction.requeue()
        
        for s in samples:
            self.router.clone_transaction(transaction, 
                                          command_args = [s, args])

    def _test_request(self, transaction, args):
        """
        An hook that allow for whitelisted twitter-based commands to be made to
        the system. Currently is used to remotely tell the system to reboot.
        """
        
        if transaction.origin in self.test_whitelist:
            #allows for remote reboot
            if 'r' in args and len(args) == 1:
                transaction.process(True)
                #This is super ungraceful. A future improvement would be to save
                #Any transaction that are still valid
                self.router.reboot()
            
        else:
            #Gives a message to unauthorized users that the test command is not valid
            transaction.to_id = "twitter"
            transaction.command = "post"
            transaction.command_args = ("No valid commands found in your "
                                            "tweet. Please tweet help() -c for "
                                            "a list of commands")
            transaction.requeue()
        
    def _help_request(self, transaction, args):
        """
        A helper method that takes the help command transactions and sends the 
        help string corresponding to the command and args to twitter.
        """
        
        transaction.to_id = "twitter"
        transaction.command = "post"
        transaction.command_args = ""
        
        #Reads the help string from a configuration file, allowing rapid change
        #in the help strings, if necessary
        if not args:
            transaction.command_args = self.help_strings['default']
            
        else:
            for arg in args:
                try:
                    if transaction.command_args == "":
                        transaction.command_args = self.help_strings[arg]
                    else:
                        self.router.clone_transaction(transaction,
                                    command_args = self.help_strings[arg])
                except KeyError:
                        transaction.log("Bad arg from help request")
                
            
            if transaction.command_args == "":
                transaction.command_args = self.help_strings['bad']
                    
    
class BadTweetCommandError(Exception):
    """
    Raised when the command from a tweet is missing, or is invalid.
    """
    pass

class BadTweetArgError(Exception):
    """
    Raised when one or more arguments in a tweet is invalid. Stores the command
    to which this argument was being applied.
    """
    def __init__(self, cmd, arg):
        self.command = cmd
        self.argument = arg

class BadTweetSampleError(Exception):
    """
    Raised when one or more sample numbers from a is invalid, or if sample 
    numbers are missing entirely.
    """
    pass
