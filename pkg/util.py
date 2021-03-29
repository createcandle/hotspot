"""Utility functions."""



import re
import time
import shutil
import socket
import random
import string
import requests
from requests.adapters import HTTPAdapter
import subprocess


def get_own_mac(interface):

  try:
    mac = open('/sys/class/net/'+interface+'/address').readline()
  except:
    mac = "00:00:00:00:00:00"

  return mac[0:17]
  
  
def get_own_hostname():
    try:
        hostname = subprocess.check_output(['hostname'])
        hostname = hostname.decode("utf-8")
        hostname = hostname.replace("\n","")
        return hostname
    except Exception as ex:
        print("Error while checking own hostname! Will default to 'gateway'. Error was: " + str(ex) )
        return "gateway"


def get_own_ip():
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = None
    finally:
        s.close()
    return IP



def extract_mac(line):
    p = re.compile(r'(?:[0-9a-fA-F]:?){12}')
    return str(re.findall(p, line)[0])


def extract_ip(line):
    #p = re.compile(r"((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)([ (\[]?(\.|dot)[ )\]]?(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3})")
    p = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
    return str(re.findall(p, line)[0])


def valid_ip(ip):
    return ip.count('.') == 3 and \
        all(0 <= int(num) < 256 for num in ip.rstrip().split('.')) and \
        len(ip) < 16 and \
        all(num.isdigit() for num in ip.rstrip().split('.'))


def valid_mac(mac):
    return mac.count(':') == 5 and \
        all(0 <= int(num, 16) < 256 for num in mac.rstrip().split(':')) and \
        not all(int(num, 16) == 255 for num in mac.rstrip().split(':'))


def is_a_number(s):
    """ Returns True is string is a number. """
    try:
        float(s)
        return True
    except ValueError:
        return False
    
    
def get_int_or_float(v):
    number_as_float = float(v)
    number_as_int = int(number_as_float)
    #print("number_as_float=" + str(number_as_float))
    #print("number_as_int=" + str(number_as_int))
    
    if round(v) != v:
        #print("vvvv float")
        return float( int( number_as_float * 100) / 100) 
    else:
        #print("vvvv int")
        return number_as_int
    
    if str(number_as_float) == str(number_as_int):
        #print("--int was same as float")
        return number_as_int
    else:
        #print("--int was NOT the same as float")
        #tamed_float = float( int(number_as_float * 100) / 100)
        
        return float( int( number_as_float * 100) / 100) 
        #return  float('%.2f' % number_as_float).rstrip('0').rstrip('.')
        #return  round(number_as_float,2)



def get_api_url(link_list):
    for link in link_list:
        #print("link item = " + str(link))
        if link['rel'] == 'property':
            return link['href']
    return None





  
def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stderr.readline, ""):
        yield stdout_line 
    popen.stderr.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)




def run_command(cmd, timeout_seconds=20):
    try:
        p = subprocess.run(cmd, timeout=timeout_seconds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)

        if p.returncode == 0:
            return p.stdout # + '\n' + "Command success" #.decode('utf-8')
            #yield("Command success")
        else:
            if p.stderr:
                return "Error: " + str(p.stderr) # + '\n' + "Command failed"   #.decode('utf-8'))

    except Exception as e:
        print("Error running command: "  + str(e))




def run_command_with_lines(command):
    try:
        p = subprocess.Popen(command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)
        # Read stdout from subprocess until the buffer is empty !
        for bline in iter(p.stdout.readline, b''):
            line = bline.decode('utf-8') #decodedLine = lines.decode('ISO-8859-1')
            line = line.rstrip()
            if line: # Don't print blank lines
                yield line
                
        # This ensures the process has completed, AND sets the 'returncode' attr
        while p.poll() is None:                                                                                                                                        
            sleep(.1) #Don't waste CPU-cycles
        # Empty STDERR buffer
        err = p.stderr.read()
        if p.returncode == 0:
            yield("Command success")
            return True
        else:
            # The run_command() function is responsible for logging STDERR 
            if len(err) > 1:
                yield("Command failed with error: " + str(err.decode('utf-8')))
                return False
            yield("Command failed")
            return False
            #return False
    except Exception as ex:
        print("Error running shell command: " + str(ex))









def generate_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))





#
#  A quick scan of the network.
#
def arpa_detect_gateways(quick=True):
    command = "arp -a"
    gateway_list = []
    try:
        
        s = requests.Session()
        s.mount('http://', HTTPAdapter(max_retries=0))
        s.mount('https://', HTTPAdapter(max_retries=0))
        
        result = subprocess.run(command, shell=True, universal_newlines=True, stdout=subprocess.PIPE) #.decode())
        for line in result.stdout.split('\n'):
            #print(str(line))
            if len(line) > 10:
                
                if quick and "<incomplete>" in line:
                    #print("skipping incomplete ip")
                    continue
                    
                #print("--useable")
                #name = "?"

                try:
                    ip_address_list = re.findall(r'(?:\d{1,3}\.)+(?:\d{1,3})', str(line))
                    #print("ip_address_list = " + str(ip_address_list))
                    ip_address = str(ip_address_list[0])
                    if not valid_ip(ip_address):
                        continue
                        
                    #print("found valid IP address: " + str(ip_address))
                    try:
                        test_url_a = 'http://' + str(ip_address) + "/"
                        test_url_b = 'https://' + str(ip_address) + "/"
                        html = ""
                        try:
                            response = s.get(test_url_a, allow_redirects=True, timeout=1)
                            #print("http response: " + str(response.content.decode('utf-8')))
                            html += response.content.decode('utf-8').lower()
                        except Exception as ex:
                            #print("Error scanning network for gateway using http: " + str(ex))
                            
                            
                            try:
                                response = s.get(test_url_b, allow_redirects=True, timeout=1)
                                #print("https response: " + str(response.content.decode('utf-8')))
                                html += response.content.decode('utf-8').lower()
                            except Exception as ex:
                                #print("Error scanning network for gateway using https: " + str(ex))
                                pass
                            
                        if 'webthings' in html:
                            #print("arp: WebThings controller spotted at: " + str(ip_address))
                            #print(str(response.content.decode('utf-8')))
                            if ip_address not in gateway_list:
                                gateway_list.append(ip_address) #[ip_address] = "option"
                    
                    except Exception as ex:
                        print("Error: could not analyse IP from arp -a line: " + str(ex))
                        
                except Exception as ex:
                    print("no IP address in line: " + str(ex))
                    
               
                
    except Exception as ex:
        print("Arp -a error: " + str(ex))
        
    return gateway_list
    
