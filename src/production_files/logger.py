
import time
import os
import utils

class Logger:
    """
        This class lets us log a particular set of data. The default setting is an error
        log that is meant mostly for debugging. By changing the name, this can be used
        as a data logger (ie, set the separator to a comma, adn the show_date to false,
        and extension to cv). 
    """
    
    def __init__(self, name = "messages", show_date = True, separator = " ", extension = "txt"):
        """
        Initializes a new logger object. The defaults are for status and error message
        logging, but the if a new name is used, there will be a new directory in the log
        directory that will store the data made by the logger with that name
        
        Arguments:
            name: The logger's name. All logs will go into a directory with the logger's name
            show_date: Whether or not a date should be printed with every log message
            separator: The delimiter for all strings passed to the logger in a log command
            extension: The file-type for the log messages. Defaults to '.txt'.
        """
        
        self.name = name
        self.directory = utils.get_log_dir()
        self.show_date = show_date
        self.separator = separator
        self.extension = extension
        
        #check for log directory, create if necessary
        if not self.directory:
            new_dir = str.replace(utils.get_resource_files_prefix(), 
                                     "resources", "log")
            os.mkdir(new_dir)
        
        #check for log/name directory, create if doesn't exist
        try:
            os.makedirs("%s%s/" %(self.directory, self.name))
        except OSError:
            if not os.path.isdir("%s%s/" %(self.directory, self.name)):
                raise
            
        #check for name directory in log, create if necessary
        self.log("logger created")
    
    def log(self, *messages):
        """
        This is the method that actually logs the information. It will log all data passed
        in the argument list, all separated by the logger object's separator. Each new day
        that a message is logged, a new file will be created. Each line of the log file
        will start with the date if the logger's show_date is set to true
        """
   
        current = time.localtime()
        
        #set the file name for logging
        file_name = "%s%s/%d%02d%02d.%s" % (self.directory, self.name, 
                                            current.tm_year, current.tm_mon, 
                                              current.tm_mday, self.extension)
        #open the file
        log_file = open(file_name, "a")
        
        #attach all the message arguments
        log_string = self.separator.join(str(x) for x in messages)
        
        #check the show_date flag, and write the log message
        if self.show_date:
            log_file.write("%02d:%02d:%02d - " % (current.tm_hour, current.tm_min, 
                                            current.tm_sec) + log_string + "\n")
        else:
            log_file.write(log_string + "\n")
                                              
        log_file.close()