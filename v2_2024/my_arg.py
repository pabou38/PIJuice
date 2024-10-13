#!/usr/bin/python3 

import argparse

def parse_arg(): # parameter not used yet
    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--local", help="optional. -l to store picture locally default FALSE, ie only copy to web server", action="store_true", default =0)
    parser.add_argument("-n", "--ntp", help="optional. -n to use ntp default  FALSE, ie only copy to web server", action="store_true", default =0)

    # return from parsing is NOT a dict, a namespace
    parsed_args=parser.parse_args() #Namespace(load=0, new=True, predict=0, retrain=0) NOT A DICT
    # can access as parsed_args.new if stay as namespace

    parsed_args = vars(parsed_args) # convert object to dict. get __dict__ attribute
    print('parsed argument as dictionary: ', parsed_args)

    print('keys:' , end = ' ')
    for i in parsed_args.keys():
        print (i , end = ' ')
    print('\n')

    return(parsed_args) # dict

