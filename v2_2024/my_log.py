#!/usr/bin/python3

version = 1.1  # 14/05/2024  new victor

import datetime
import logging
import os, sys
import platform




###############################
# various system parameters
###############################

def view_system():
    print( "system:", platform.system())
    print( "processor:", platform.processor())
    print( "machine:", platform.machine())
    print( "system:", platform.system())
    print( "version:", platform.version())
    print( "uname:", platform.uname())
    print( "node:", platform.node())

    os.environ["PYTHONIOENCODING"] = "utf8"
    print('default encoding', sys.getdefaultencoding())
    print('file system encoding', sys.getfilesystemencoding())

    # env variable set in .vscode/launch.json
    try:
        print('author from env variable ', os.environ['author'])
    except:
        pass  # env variable not defined in colab

    
    if sys.platform in ["win32"]:
        print("running on WINDOWS on system: " , platform.node())
        colab=False # proceed from training to real time audio
    
    elif sys.platform in ['linux']:
        print("running on linux on system: ", platform.node())
        # os: posix, sys.platform: linux, platform.machine: x86_64
        colab = True # to stop at the end of training, and not go in audio, remi, flask 

   

def running_on_edge():
    # bool to determine if we are running on the Jetson/PI 
    # eg do not evaluate model after loading, 
    # running_on_edge = sys.platform in ["linux"]
    return(platform.processor in ["aarch64"])

def running_on_colab():
    ##### TO DO
    return(False)

    



#############################
# time stamp
#############################
def get_stamp():

    d = datetime.datetime.now()

    s = "%d/%d-%d:%d" %(d.month, d.day, d.hour, d.minute)

    return(s)


#################################
# logging
# https://docs.python.org/3/howto/logging.html
#################################

def get_log(log_file, level = logging.INFO, root = "."):

    log_file = os.path.join(root,log_file)
    
    # debug, info, warning, error, critical

    print ("logging to:  " , log_file)

    if os.path.exists(log_file) == False:
        with open(log_file, "w") as f:
            pass  # create empty file

    print("logging level", level)
    
    # The call to basicConfig() should come before any calls to debug(), info()
    # https://docs.python.org/3/library/logging.html#logging.basicConfig
    # https://docs.python.org/3/howto/logging.html#changing-the-format-of-displayed-messages
        
    # encoding not supported on ubuntu/jetson ?
    try:
        logging.basicConfig(filename=log_file,  encoding='utf-8', format='%(levelname)s %(name)s %(asctime)s %(message)s',  level=level, datefmt='%m/%d/%Y %I:%M')
    except:
        try:
            logging.basicConfig(filename=log_file, format='%(levelname)s %(name)s %(asctime)s %(message)s',  level=level, datefmt='%m/%d/%Y %I:%M')
        except Exception as e:
            print("cannot create logger", str(e))
            sys.exit(1)

    # define a name (used in %(name)s )
    # name are any hiearchy
    # use root if not defined (ie use logging.info vs logger.info )
    # importing logging in all modules easier

    logger = logging.getLogger(__name__) # INFO __main__ 2024-02-01 08:52:45,142 logger defined with name
    #logger.info("logger defined with name")

    # https://docs.python.org/3/howto/logging.html#logging-from-multiple-modules

    return(logging)


def tf_log_level():
    import tensorflow as tf
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    """
    0 = all messages are logged (default behavior)
    1 = INFO messages are not printed
    2 = INFO and WARNING messages are not printed
    3 = INFO, WARNING, and ERROR messages are not printed
    """

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

    # prevent spitting too much info ?
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

    # prevent spitting too much info ?
    tf.get_logger().setLevel('ERROR')
    tf.autograph.set_verbosity(0)

if __name__ == "__main__":

    get_log("test_log", root="logs")
    # kind of configure logging
    logging.info("testing logging")
    logging.error("testing error logging")





