from usocket import socket
from machine import I2C,Pin,SPI
import ssd1306
import network
import time
import utime
import ntptime
# import urequests
import ujson
import mrequests

# setup the I2C communication
i2c = I2C(1, sda=Pin(6), scl=Pin(7))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

username = "Wiznet"
repository = "document_framework"
#token = "token_here"
UTC_OFFSET = 9 * 60 * 60

class MyResponse(mrequests.Response):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.headers = {}

    def add_header(self, data):
        # let base class handle headers, which influence response parsing
        self._parse_header(data)
        name, value = data.decode('utf-8').rstrip('\r\n').split(':', 1)
        self.headers[name.lower()] = value.strip()

def request(*args, **kw):
    kw.setdefault('response_class', MyResponse)
    return mrequests.request(*args, **kw)

#W5x00 chip init
def w5x00_init():
    spi=SPI(0,2_000_000, mosi=Pin(19),miso=Pin(16),sck=Pin(18))
    nic = network.WIZNET5K(spi,Pin(17),Pin(20)) #spi,cs,reset pin
    nic.active(True)
    nic.ifconfig(('192.168.11.30','255.255.255.0','192.168.11.1','8.8.8.8'))
    while not nic.isconnected():
        time.sleep(1)
        print(nic.regs())
    print(nic.ifconfig())

def github_req(year,month,day):    
    #url = "https://api.github.com/repos/"+username+"/"+repository+"/actions/workflows/deploy.yml/runs?created="+"{:04d}-{:02d}-{:02d}".format(year, month, day)
    url = "https://api.github.com/repos/"+username+"/"+repository+"/actions/workflows/deploy.yml/runs?per_page=1&page=1"
    
    # Define the headers for the request
    headers = {
        "Accept": "application/vnd.github.v+json",
        #"Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent:": "Micropython"
    }

    # Make the request
    response = request("GET", url, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        response_text = response.json()   
        
    else:
        print(f"Failed to retrieve workflow status. HTTP status code: {response.status_code}")

    # Close the response
    response.close()
    return response_text

# Define the rotation speed (delay in milliseconds)
rotation_speed = 500

# Define the rotation step (number of pixels to shift)
rotation_step = 2

request_interval = 300
# Create a function to rotate the text
def rotate_text(text, rotation_step):
    return text[rotation_step:] + text[:rotation_step]

def main():
    w5x00_init()
        
    ntptime.host = "2.asia.pool.ntp.org"
    
    print("Local time before synchronization：%s" %str(time.localtime()))
    #make sure to have internet connection
    ntptime.settime()
    
    year, month, day, hour, minute, second, _, _ = time.localtime(time.time() + UTC_OFFSET)
    
    print("Local time after synchronization：%s" %str(time.localtime()))
    previous_commit = None
    while True:
        display_text = github_req(year, month, day)
        new_commit_id = display_text["workflow_runs"][0]["id"]
        
        if new_commit_id != previous_commit:
                display.fill(0)
                display.text("New commit", 25, 20)
                display.text("found!", 40, 30)
                display.rotate(False)
                display.show()
                previous_commit = new_commit_id
                utime.sleep(1)
                
        print_text = [
            display_text["workflow_runs"][0]["display_title"] + " ",
            "By: " + display_text["workflow_runs"][0]["actor"]["login"] + " ",
            "Result:"+ display_text["workflow_runs"][0]["status"] + " ",
            "Deploy: " + display_text["workflow_runs"][0]["conclusion"] + " "
            ]
        
        start_time = utime.time()
        while utime.time() - start_time < request_interval:
            display.fill(0)
                            
            for i, line in enumerate(print_text):
                y_position = i * 10  # Adjust the vertical position for each line
                display.text(line, 0, y_position)
            
            # Rotate the specified lines
                if (len(line)>16):
                    print_text[i] = rotate_text(line, rotation_step)
 
            display.rotate(False)
            display.show()
            
            utime.sleep_ms(rotation_speed)
     
if __name__ == "__main__":
    main()

