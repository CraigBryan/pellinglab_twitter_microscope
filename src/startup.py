''' Created on Nov 8, 2013

@author: Craig Bryan
'''

from production_files import router, logger
import traceback
from time import sleep
import os
from production_files import utils
import time

count = 0
logr = logger.Logger("system_status")
running = True
print utils.get_log_dir()

start_time = time.time();
try:
    while(running):
        if(time.time() - start_time > 86400):
            logr.log("Normal daily restart routine")
            os.system("sudo reboot")  
            
        try:
            r = router.Router()
        except Exception as e:
            print "Exception on router instantiation: %s" %str(e)
            print traceback.format_exc(e)
            logr.log("Exception on router instantiation: %s" %str(e))
            count += 1
    
            if count > 3:
                os.system("sudo reboot")
    
            sleep(60)
            continue
        else:
            count = 0
            
            while(True):
                if(time.time() - start_time > 86400):
                        os.system("sudo reboot")
            
                try:
                    r.next()
                except Exception as e:
                    print "Exception during router running: %s" %str(e)
                    print traceback.format_exc(e)
                    logr.log("Exception during router running: %s" %str(e))
                    sleep(60)
                    del r
                    break
                
except Exception as e:
    logr.log(e);
    print traceback.format_exc(e)
    os.system("sudo reboot")
    
