import os
import shutil

'''
Some helper functions for various parts of the program.

Created on Sep 4, 2013

@author: Craig Bryan
'''

dict_filename = "dicts_t.cfg"

def get_resource_files_prefix():
    """
    This returns the absolute file prefix for the resource folder.
    Uses a breadth-first search of directories.
    """
        
    found = False
    os.chdir(os.path.abspath(__file__[:-9]))
    while not found:
        for directory in os.walk('.').next()[1]:
            if directory == "resources":
                found = True
                break
        else:
            os.chdir('..')
        
        if os.getcwd == 'home':
            return False
        
    return os.getcwd() + "/resources/"

def get_image_dir():
    """
    This returns the absolute file location of the image storage directory.
    Uses a breadth-first search of directories.
    """
    
    found = False
    os.chdir(os.path.abspath(__file__[:-9]))
    while not found:
        for directory in os.walk('.').next()[1]:
            if directory == "images":
                found = True
                break
        else:
            os.chdir('..')
            
        if os.getcwd == "home":
            return False
        
    return os.getcwd() + "/images/"

def get_log_dir():
    """
    This returns the absolute file location of the log storage directory.
    Uses a breadth-first search of directories.
    """
    
    found = False
    os.chdir(os.path.abspath(__file__[:-9]))
    while not found:
        for directory in os.walk('.').next()[1]:
            if directory == "log":
                found = True
                break
        else:
            os.chdir('..')
                
            if os.getcwd == "home":
                return False
            
        return os.getcwd() + "/log/"

def clear_image_cache():
    """
    This erases all the images in the image directory.
    """
    
    shutil.rmtree("%s." %get_image_dir(), ignore_errors = True)

def read_config_dict(header, raw = False):
    """
    Reads from the config file, finds the given header and loads 
    the data in the config to a dictionary and returns it to the caller.
    The raw option skips the casting of integers and lists and is used by the 
    update_config_dict function.
    
    Arguments:
        raw: If raw is True, then the type flags in front of individual values
             is ignored. Used for writing values to the configuration dictionary.
    """
    
    dict_file = open(get_resource_files_prefix() + dict_filename, 'r')
    isHeaderFound = False
    config_dict = dict()
    
    #Reads the dicts.cfg file and finds the relevant section. Converts the
    #data to a dictionary.
    for line in dict_file.readlines():
        line = line.strip() #removes trailing newline
        
        if not isHeaderFound:
            if line == ("start " + header):
                isHeaderFound = True
                
        else:
            key, colon, value = line.partition(':')            #@UnusedVariable
            
            if key == "end":
                break
            else:
                config_dict[key] = value
            
    else: #header never found
        raise BadConfigFileError("Requested header not found")
    
    #Casting dictionary values to ints, or a comma-separated string list into
    #a python list of strings, if requested
    if not raw:
        for key in config_dict:
            current = config_dict[key]
            if "(int)" in current:
                current = current.replace("(int)", "")
    
                try:
                    current = int(current)
                except ValueError:
                    raise BadConfigFileError("Can't cast a non-number value to int")
                
                config_dict[key] = current
            elif "(list)" in  current:
                current = current.replace("(list)", "")
                current = current.split(',')
        
    dict_file.close()
    return config_dict

def update_config_dict(header, new_dict):
    """
    This reads the specified configuration dictionary and updates it with the
    given dictionary. It can overwrite configuration entries, but will 
    overwrite other values if new values are added.
    
    Arguments:
        new_dict: The configuration dictionary to be appended to the configuration
                  dictionary with the same header name in the 
    """
    
    #modify the values to be placed in the dictionary
    for key in new_dict:
        if type(new_dict[key]) is int:
            new_dict[key] = "(int)" + str(new_dict[key])
        if type(new_dict[key]) is list:
            new_dict[key] = "(list)" + ",".join([str(item) for item in new_dict[key]])
        
    original = read_config_dict(header, raw = True) 
    
    #change and add any values
    for key in new_dict:
        original[key] = new_dict[key]
        
    #change the dictionary into a list of strings
    updated_dict_list = []
    for key in original:
        updated_dict_list.append(str(key) + ":" + str(original[key]))
    
    #open the configuration file and put all the lines in a list
    with open(get_resource_files_prefix() + dict_filename, 'r') as resource_file:
        filelist = resource_file.readlines()
    
    #find the header entry being updated
    start_index = filelist.index("start " + header + '\n')
    end_index = filelist.index("end\n", start_index)
    
    #write the updated header's configurations
    filelist[start_index + 1:end_index] = updated_dict_list
    
    #open the file again to write.
    with open(get_resource_files_prefix() + dict_filename, 'w') as file_to_overwrite:
        for line in filelist:
            file_to_overwrite.write("%s\n" %line.rstrip())

class BadConfigFileError(Exception):
    """
    An exception that is thrown whenever a given header cannot be found.
    """
    pass