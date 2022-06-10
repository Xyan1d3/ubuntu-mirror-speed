import sys
import time
import urllib3
import requests
import threading
from os import popen
import pdb
from tabulate import tabulate

# Colour Code's for styling the terminal
bold = "\033[1m"
green = "\033[32m"
white = "\033[37m"
purple = "\033[95m"
red = "\033[91m"
blue = "\033[34m"
orange = "\033[33m"
end = "\033[0m"

# This function creates a list of list's containing the uptodate ubuntu versions and their nicknames.
def list_valid_distributions():
    r = requests.get("https://launchpad.net/ubuntu/+series")
    extract1 = [each for each in r.text.split('\n') if '<strong><a href="' in each]
    extract2 = [each.split('">')[1].split('</a></strong>')[0] for each in extract1]
    flavour_nickname = [each.split(" ")[0] for each in extract2]
    flavour_version = [each.split("(")[1].split(")")[0] for each in extract2]
    chain = [[nickname.lower(),version] for nickname,version in zip(flavour_nickname,flavour_version)]
    return chain

# This function 3 pings to the mirror domain and appends the average of 3 response times into the last of the list
def check_icmp_response_times(mirror_domain,mirrors_list):
    # This try is for checking if the ping results any unexpected errors
    try:
        ping = int(float(popen(f"ping -c 3 {mirror_domain} 2> /dev/null").read().split("\n")[-2].split("/")[-3]))
        #print(f"{bold}[{green}+{white}] Avg ping for {mirror_domain} : {green}{ping}{end}")
        mirrors_list.append(ping)

    # In case of errors while pinging we add 999 as the response time of the mirror
    # It may also occur if ICMP is disabled or it has some temporary name resolution errors
    except IndexError:
        mirrors_list.append(999)

def check_updates_availability(mirror_url,mirrors_list,distro,arch,repo):
    for each_repo in repo:
        # $url/dists/$DIST/$REPO/binary-$ARCH/
        try:
            r = requests.get(f"{mirror_url}dists/{distro}/{each_repo}/binary-{arch}/",timeout=5)
            if r.status_code == 200:
                mirrors_list.append(f"{bold}{green}\u2714{end}")
            elif r.status_code == 404:
                mirrors_list.append(f"{bold}{red}\u2718{end}")
            else:
                mirrors_list.append(f"{bold}{purple}\u2754{end}")
        except requests.exceptions.ConnectionError:
            mirrors_list.append(f"{bold}{red}\u2718{end}")
        except requests.exceptions.HTTPError:
            mirrors_list.append(f"{bold}{red}\u2718{end}")
        except requests.exceptions.ReadTimeout:
            mirrors_list.append(f"{bold}{red}\u2718{end}")

# ==========> Argument Parser for feeding arguments
args_usage = "Usage : python3 ubuntu_mirror_tester.py [Ubuntu Distro Flavour] [Architecture]\nExample : python3 ubuntu_mirror_tester.py jammy amd64"
arg_flags = [
["-l,  --list-flavour","List the current top 15 Ubuntu Flavour's."],
["-a,  --all","[Optional] When combined with the [-l / --list-flavour] it lists all the Ubuntu Flavour's."],
["-h,  --help","Print's this help message"]
]
valid_arch = ["amd64","arm64","armhf","i386","ppc64el","s390x"]
if len(sys.argv) > 1:
    # Print help if --help or -h is only entered
    if sys.argv[1].lower() == "--help" or sys.argv[1].lower() == "-h":
        print(args_usage)
        print(tabulate(arg_flags))
        exit()
    # List all up-to-date distributions of Ubuntu with Version Numbers
    if ("--list-flavour" in sys.argv or "-l" in sys.argv) and ("--all" in sys.argv or "-a" in sys.argv) :
        print(tabulate(list_valid_distributions(),headers=["Flavour Nickname","Flavour Version"],tablefmt="grid"))
        exit()
    # Show only top 15 flavours of ubuntu with version numbers
    elif ("--list-flavour" in sys.argv or "-l" in sys.argv) :
        print(tabulate(list_valid_distributions()[:15],headers=["Flavour Nickname","Flavour Version"],tablefmt="grid"))
        exit()
    # Checking if the script is getting more than 2 arguments
    if any(sys.argv[1].lower() in each for each in list_valid_distributions()):
        distro = sys.argv[1].lower()
    # Printing error if it is not a valid distro nickname
    elif not any(sys.argv[1].lower() in each for each in list_valid_distributions()):
        print(f"{bold}[{red}-{white}] {red} Sorry, But I think you entered a wrong distro nickname.{end}")
        print(f"{bold}[{red}-{white}] {red} You could get the latest valid up-to-date list by running it with [--list-flavour].{end}")
        exit()
    # Checking if the 2nd argument is an valid ubuntu architecture
    if sys.argv[2].lower() in valid_arch:
        arch = sys.argv[2].lower()
    # Printing valid architectures if the arch supplied was not valid
    elif sys.argv[2].lower() not in valid_arch:
        print(f"{bold}[{red}-{white}] {red}{sys.argv[2].lower()} is not recognised as a valid architecture.{end}")
        print(f"{bold}[{red}-{white}] {red}Please pick one from this list {green}{valid_arch}{red}.{end}")
        exit()
else:
    print(args_usage)
    print(tabulate(arg_flags))
    exit()
print(f"{bold}[{green}+{white}] Target Distribution {orange}Ubuntu{white} {green}{distro}{white} and architecture {green}{arch}{end}")
print(f"{bold}[{purple}*{white}] Getting latest list of {orange}Ubuntu{white} Mirrors{blue}...{end}")
r = requests.get("https://launchpad.net/ubuntu/+archivemirrors")

mirrors = []
# This script checks for the arm64 architecture.
#arch = "arm64"

# The distribution tag name like 22.04 LTS is Focal.
#distro = "jammy"

# The type of updates supported by ubuntu
updates_repo = ["main", "restricted", "universe", "multiverse"]



# Spliting by line breaks on the and then adding the Mirror URL and Mirror Domain as a list into a the mirrors list
for each in list(r.text.split("\n")):
    if "http</a>" in each:
        temp = [each[19:-10],each[19:-10].split("/")[2]]
        mirrors.append(temp)

print(f"{bold}[{green}+{white}] Congratulations found {green}{len(mirrors)}{white} Mirrors.{end}")

head = ["Mirror Domain","ICMP Latency"]
head.extend(updates_repo)

print(f"{bold}[{purple}*{white}] Calculating Latency to each of {green}{len(mirrors)}{white} Mirrors{blue}...{end}")
threads = []
# Extracting each list containing pair of the mirror URL and the mirror domain
for each_mirror in mirrors:
    mirror_domain = each_mirror[1]
    # Creating each threading objects and putting the objects into the threads list
    t = threading.Thread(target=check_icmp_response_times,args=(mirror_domain,each_mirror))
    threads.append(t)

# Attempting to start all the threads
for each_thread in threads:
    each_thread.start()

# Joining each threads back to the parent process
for each_thread in threads:
    each_thread.join()

print(f"{bold}[{green}+{white}] Latency calculation complete{blue}...{end}")
# Sorting the http mirrors based on the lowest ping to the server
mirrors.sort(key = lambda x: x[2])

print(f"{bold}[{purple}*{white}] Starting availability check of {blue}{updates_repo}{white} in each of the Mirrors{blue}...{end}")
threads = []
for each_mirror in mirrors:
    threads.append(threading.Thread(target=check_updates_availability,args=(each_mirror[0], each_mirror, distro, arch, updates_repo,)))

# Atttempting to start all the threads
for each_thread in threads:
    each_thread.start()

# Joining each threads back to the parent process
for each_thread in threads:
    each_thread.join()

print(f"{bold}[{green}+{white}] Availability Check Completed{blue}...{end}")

print(f"{bold}[{green}*{white}] Filtering Mirrors which has all the types of updates available{blue}...{end}")

final_mirrors_list = []
# Filtering the repos that have all crosses
for i in range(len(mirrors)):
    if mirrors[i].count(f"{bold}{green}\u2714{end}") == 4:
        mirrors[i].pop(0)
        final_mirrors_list.append(mirrors[i])
print(f"{bold}[{green}+{white}] {orange}Bada Bing Bada Boooom{blue}...{end}")

print(tabulate(final_mirrors_list,headers=head,tablefmt="grid"))