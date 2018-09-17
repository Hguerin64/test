#!/usr/bin/python
import json
import os
import sys
#import time
import subprocess
import platform

#Colorful constants
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
NOCOLOR = '\033[0m'

#GITHUB URL
GITHUB_URL = "https://github.com/bolinches/HANA-TDI-healthcheck"

#devnull redirect destination
DEVNULL = open(os.devnull, 'w')

#This script version, independent from the JSON versions
HOH_VERSION = "0.36"

def load_json(json_file_str):
    #Loads  JSON into a dictionary or quits the program if it cannot. Future might add a try to donwload the JSON if not available before quitting
    try:
        with open(json_file_str, "r") as json_file:
            json_variable = json.load(json_file)
            return json_variable
    except:
        sys.exit(RED + "QUIT: " + NOCOLOR + "Cannot open JSON file: " + json_file_str)

def check_paramerters():
    main_script=sys.argv[0]
    error_message = RED + "QUIT: " + NOCOLOR + "To run hoh, you need to pass the argument of type of storage (XFS/NFS/ESS). In example: ./hoh.py XFS\n"
    try: #in case no argument is passed
        argument1=sys.argv[1]
    except:
        print
        sys.exit(error_message)

    if argument1.upper() in ('XFS', 'NFS', 'ESS'): #To check is a wanted argument
        return argument1.upper()
    else:
        print
        sys.exit(error_message)

def show_header(hoh_version,json_version):
    #Say hello and give chance to disagree to the no warranty of any kind
    while True:
        print
        print(GREEN + "Welcome to HANA OS Healthchecker (hoh) version " + hoh_version + NOCOLOR)
        print
        print("Please use " + GITHUB_URL + " to get latest versions and report issues about hoh.")
        print
        print("The purpouse of hoh is to supplment the official tools like HWCCT not to substitute them, always refer to official documentation from IBM, SuSE/RedHat, and SAP")
        print
        print("You should always check your system with latest version of HWCCT as explained on SAP note:1943937 - Hardware Configuration Check Tool - Central Note")
        print
        print("JSON files versions:")
        print("\tsupported OS:\t\t" + json_version['supported_OS'])
        print("\tsysctl: \t\t" + json_version['sysctl'])
        print("\tpackages: \t\t" + json_version['packages'])
        print("\tibm power packages:\t" + json_version['ibm_power_packages'])
        print
        print(RED + "This software comes with absolutely no warranty of any kind. Use it at your own risk" + NOCOLOR)
        print
        run_this = raw_input("Do you want to continue? (y/n): ")
        if run_this.lower() == 'y':
            break
        if run_this.lower() == 'n':
            print
            sys.exit("Have a nice day! Bye.\n")

def check_processor():
    expected_processor = 'ppc64le' #Not supporting other than ppc64le as now. Hardcoding here ppc64le
    error_message = RED + "QUIT: " + NOCOLOR + "Only " + expected_processor + " processor is supported.\n"
    current_processor = platform.processor()
    #print(current_processor)
    if current_processor != expected_processor:
        print
        sys.exit(error_message)

def check_os(os_dictionary):
    #Checks the OS string vs the JSON file. If supported goes, if explecitely not supported quits. If no match also quits

    with open("/etc/os-release") as os_release_file:
        os_release = {}
        for line in os_release_file:
            key,value = line.rstrip().split("=")
            os_release[key] = value.strip('"')

    error_message = RED + "QUIT: " + NOCOLOR + " " + os_release['PRETTY_NAME'] + " is not a supported OS for this tool\n"

    try:
        if os_dictionary[os_release['PRETTY_NAME']] == 'OK':
            print
            print(GREEN + "OK: "+ NOCOLOR + " " + os_release['PRETTY_NAME'] + " is a supported OS for this tool")
        else:
            print
            sys.exit(error_message)
    except:
        print
        sys.exit(error_message)

def get_json_versions(os_dictionary,sysctl_dictionary,packages_dictionary,ibm_power_packages_dictionary):
    #Gets the versions of the json files into a dictionary
    json_version = {}

    #Lets see if we can load version, if not quit
    try:
        json_version['supported_OS'] = os_dictionary['json_version']
    except:
        sys.exit(RED + "QUIT: " + NOCOLOR + "Cannot load version from supported OS JSON")

    try:
        json_version['sysctl'] = sysctl_dictionary['json_version']
    except:
        sys.exit(RED + "QUIT: " + NOCOLOR + "Cannot load version from sysctl JSON")

    try:
        json_version['packages'] = packages_dictionary['json_version']
    except:
        sys.exit(RED + "QUIT: " + NOCOLOR + "Cannot load version from packages JSON")

    try:
        json_version['ibm_power_packages'] = ibm_power_packages_dictionary['json_version']
    except:
        sys.exit(RED + "QUIT: " + NOCOLOR + "Cannot load version from IBM Power packages JSON")

    #If we made it this far lets return the dictionary. This was being stored in its own file before
    return json_version

def saptune_check():
    #It uses saptune command to check the solution and show the avaialble notes. Changes version to version of saptune, we are just calling saptune
    errors = 0
    print
    print("Checking if saptune solution is set to HANA")
    print
    try:
        return_code = subprocess.call(['saptune','solution','verify','HANA'])
        if return_code == 0:
            print(GREEN + "OK: " + NOCOLOR + "saptune is using the solution HANA")
            print
        else:
            print(RED + "ERROR: " + NOCOLOR + "saptune is *NOT* fully using the solution HANA")
            print
            errors = errors + 1
    except:
        sys.exit(RED + "QUIT: " + NOCOLOR + "cannot run saptune") # Not installed or else. On SuSE for SAP it is installed by default

    print("The following individual SAP notes recommendations are avaialble via sapnote")
    print("Consider enabling ALL of them, including 2161991 as only sets NOOP as I/O scheduler")
    print
    #subprocess.check_output(['saptune','note','list'])
    os.system("saptune note list")
    print
    return errors

def sysctl_check(sysctl_dictionary):
    #Runs checks versus values on sysctl on JSON file
    errors = 0
    print("Checking sysctl settings:")
    print
    for sysctl in sysctl_dictionary.keys():
        if sysctl != "json_version":
            recommended_value_str = str(sysctl_dictionary[sysctl])
            recommended_value = int(recommended_value_str.replace(" ", "")) #Need to clean the entries that have spaces or tabs for integer comparision
            try:
                current_value_str = subprocess.check_output(['sysctl','-n',sysctl], stderr=subprocess.STDOUT)
                current_value_str = current_value_str.replace("\t", " ").replace("\n", "")
                current_value = int(current_value_str.replace(" ", "")) #Need to clean the entries that have spaces for integer comparision
                #This creates an possible colision issue, might fix this in the future

                if recommended_value != current_value:
                    print (RED + "ERROR: " + NOCOLOR + sysctl + " is " + current_value_str + " and should be " + recommended_value_str)
                    errors = errors + 1
                else:
                    print(GREEN + "OK: " + NOCOLOR + sysctl + " it is set to the recommended value of " + recommended_value_str)
            except:
                    print(YELLOW + "WARNING: " + NOCOLOR + sysctl + "current value does not exists")
                    errors = errors + 1
    print
    return errors

def rpm_is_installed(rpm_package):
    #returns the RC of rpm -q rpm_package or quits if it cannot run rpm
    errors = 0
    try:
        return_code = subprocess.call(['rpm','-q',rpm_package],stdout=DEVNULL, stderr=DEVNULL)
    except:
        sys.exit(RED + "QUIT: " + NOCOLOR + "cannot run rpm")
    return return_code

def packages_check(packages_dictionary):
    #Checks if packages from JSON are installed or not based on the input data ont eh JSON
    errors = 0
    print("Checking packages install status:")
    print
    for package in packages_dictionary.keys():
        if package != "json_version":
            current_package_rc = rpm_is_installed(package)
            expected_package_rc = packages_dictionary[package]
            if current_package_rc == expected_package_rc:
                print(GREEN + "OK: " + NOCOLOR + package + " installation status is as expected")
            else:
                print(RED + "ERROR: " + NOCOLOR + package + " installation status is *NOT* as expected")
    print
    return(errors)

def ibm_power_package_check(ibm_power_packages_dictionary):
    errors = 1
    print("Checking IBM service and productivity tools packages install status:")
    print
    for package in ibm_power_packages_dictionary.keys():
        if package != "json_version":
            current_package_rc = rpm_is_installed(package)
            expected_package_rc = ibm_power_packages_dictionary[package]
            if current_package_rc == expected_package_rc == 0:
                print(GREEN + "OK: " + NOCOLOR + package + " installation status is installed")
                errors = 0
            elif current_package_rc == expected_package_rc == 1:
                print(GREEN + "OK: " + NOCOLOR + package + " installation status is not installed")
            else:
                print(YELLOW + "WARNING: " + NOCOLOR + package + " installation status is *NOT* as expected. Check that at least one package is installed")
    print
    return(errors)

def print_errors(saptune_errors,sysctl_errors,packages_errors,ibm_power_packages_errors):
    #End summary and say goodbye
    print
    print("The summary of this run:")
    if saptune_errors > 0:
        print(RED + "saptune reported deviations" + NOCOLOR)
    else:
        print(GREEN + "saptune reported no deviations" + NOCOLOR)

    if sysctl_errors > 0:
        print(RED + "sysctl reported " + str(sysctl_errors) + " deviations" + NOCOLOR)
    else:
        print(GREEN + "sysctl reported no deviations" + NOCOLOR)

    if packages_errors > 0:
        print(RED + "packages reported " + str(packages_errors) + " deviations" + NOCOLOR)
    else:
        print(GREEN + "packages reported no deviations" + NOCOLOR)

    if ibm_power_packages_errors > 0:
        print(RED + "IBM service and productivity tools packages reported " + str(sysctl_errors) + " deviations" + NOCOLOR)
    else:
        print(GREEN + "IBM service and productivity tools packages reported no deviations" + NOCOLOR)

def main():
    #Check parameters are passed
    storage = check_paramerters()

    #JSON loads
    os_dictionary = load_json("supported_OS.json")
    sysctl_dictionary = load_json(storage + "_sysctl.json")
    packages_dictionary = load_json("packages.json")
    ibm_power_packages_dictionary = load_json("ibm_power_packages.json")

    #Initial header and checks
    json_version = get_json_versions(os_dictionary,sysctl_dictionary,packages_dictionary,ibm_power_packages_dictionary)
    show_header(HOH_VERSION,json_version)
    check_processor()
    check_os(os_dictionary)

    #Run
    saptune_errors = saptune_check()
    sysctl_errors = sysctl_check(sysctl_dictionary)
    packages_errors = packages_check(packages_dictionary)
    ibm_power_packages_errors = ibm_power_package_check(ibm_power_packages_dictionary)

    #Exit protocol
    DEVNULL.close()
    print_errors(saptune_errors,sysctl_errors,packages_errors,ibm_power_packages_errors)
    print
    print

if __name__ == '__main__':
    main()
