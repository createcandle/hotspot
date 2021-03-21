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



def clean_up_string_for_speaking(sentence):
    sentence = sentence.replace('/', ' ').replace('\\', ' ').replace('+', ' plus ').replace('#', ' number ').replace('-', ' ').replace('&', ' and ').replace('  ', ' ')
    sentence = sentence.replace('  ', ' ')
    return sentence



def split_sentences(st):
    sentences = re.split(r'[.?!]\s*', st)
    if sentences[-1]:
        return sentences
    else:
        return sentences[:-1]

        

def is_color(color_name):
    if color_name in color_dictionary:
        return True
    return False



def color_name_to_hex(target_color):
    print("target color: " + str(target_color))
    try:
        #hx = next(hex_color for hex_color, value in color_dictionary if value == color_name)
        for current_name,current_hx in color_dictionary:
            if str(current_name) == str(target_color):
                print(str(target_color) + " matched " + str(current_hx))
                return str(current_hx)
    except:
        print("couldn't match spoken color to a hex value. Returning red.")
        return '#ff0000'                                   



def hex_to_color_name(target_hx):
    #hx = next(hex_color for hex_color, value in color_dictionary if value == color_name)
    #print("__hex_to_color_name: hex to work with: " + str(target_hx))
    if len(target_hx) == 7 and target_hx.startswith('#'):
        #print("very likely a hex color")

        try:
            # if color is found in dict
            try:
                #quick_color_name = next(current_color for current_color, current_hx in color_dictionary if current_hx == target_hx)
                quick_color_name = next(key for key, value in color_dictionary.items() if value == str(target_hx))
                
                #if str(quick_color_name) != "sorry":
                #print("quick color match: " + str(quick_color_name))
                return str(quick_color_name)

            except:
                pass
                #print("Was not able to get a quick hex-to-color match, will try to find a neighbouring color.")

            target_hx = target_hx.replace("#", "")

            # return the closest available color
            m = 16777215
            k = '000000'
            for current_color_name, current_hx in color_dictionary.items():
            #for key in color_dictionary.keys():
                current_hx = current_hx.replace("#", "")

                a = int(target_hx[:2],16)-int(current_hx[:2],16)
                b = int(target_hx[2:4],16)-int(current_hx[2:4],16)
                c = int(target_hx[4:],16)-int(current_hx[4:],16)

                v = a*a+b*b+c*c # simple measure for distance between colors

                # v = (r1 - r2)^2 + (g1 - g2)^2 + (b1 - b2)^2

                if v <= m:
                    #print("smaller hex distance: " + str(v))
                    m = v
                    k = current_color_name

            #print("__hex_to_color_name: matched color: " + str(color_dictionary[k]))
            #print("__hex_to_color_name: closest matching hex color: " + str(k))
            #slow_color_name = next(key for key, value in color_dictionary.items() if value == str(target_hx))
            return str(k)
        except Exception as ex:
            print("Error while translating hex color to human readable name: " + str(ex))
            return "red"
    else:
        #print("String was not a hex color?")
        return target_hx


def download_file(url, target_file):
    #print("File to download: " + str(url))
    #print("File to save to:  " + str(target_file))
    try:
        #if intended_filename == None:
        intended_filename = target_file.split('/')[-1]
        with requests.get(url, stream=True) as r:
            with open(target_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
    except Exception as ex:
        print("ERROR downloading file: " + str(ex))
        return False
    #print("download_file: returning. Filename = " + str(intended_filename))
    return True



#def run_command(command, cwd=None):
#    try:
#        return_code = subprocess.call(command, shell=True, cwd=cwd)
#        return return_code
#
#    except Exception as ex:
#        print("Error running shell command: " + str(ex))
        

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



def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = None
    finally:
        s.close()
    return IP



def valid_ip(ip):
    return ip.count('.') == 3 and \
        all(0 <= int(num) < 256 for num in ip.rstrip().split('.')) and \
        len(ip) < 16 and \
        all(num.isdigit() for num in ip.rstrip().split('.'))



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
    
