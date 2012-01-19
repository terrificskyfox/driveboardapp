
import sys
import time
import serial
from collections import deque



class SerialManagerClass:
    
    def __init__(self):
        self.device = None

        self.rx_buffer = ""
        self.tx_buffer = ""        
        self.remoteXON = True

        # TX_CHUNK_SIZE - this is the number of bytes to be 
        # written to the device in one go.
        # IMPORTANT: The remote device is required to send an
        # XOFF if TX_CHUNK_SIZE bytes would overflow it's buffer.
        self.TX_CHUNK_SIZE = 16
        self.RX_CHUNK_SIZE = 256
        
        # used for calculating percentage done
        self.job_size = 0    



    def connect(self, port, baudrate):
        self.rx_buffer = ""
        self.tx_buffer = ""        
        self.remoteXON = True
        self.job_size = 0
        # Create serial device with both read timeout set to 0.
        # This results in the read() being non-blocking
        self.device = serial.Serial(port, baudrate, timeout=0)
        
        # I would like to use write with a timeout but it appears from checking
        # serialposix.py that the write function does not correctly report the
        # number of bytes actually written. It appears to simply report back
        # the number of bytes passed to the function.
        # self.device = serial.Serial(port, baudrate, timeout=0, writeTimeout=0)

    def close(self):
        if self.device:
            self.device.flushOutput()
            self.device.flushInput()
            self.device.close()
            self.device = None
            return True
        else:
            return False
                    
    def is_connected(self):
        return bool(self.device)

    def flush_input(self):
        if self.device:
            self.device.flushInput()

    def flush_output(self):
        if self.device:
            self.device.flushOutput()


    def queue_for_sending(self, gcode):
        if gcode:
            gcode = gcode.strip()
    
            if gcode[:4] == 'M112':
              # cancel current job
              self.tx_buffer = ""
              self.job_size = 0
            elif gcode[0] == '%':
                return
                    
            self.tx_buffer += gcode + '\n'
            self.job_size += len(gcode) + 1

    def is_queue_empty(self):
        return len(self.tx_buffer) == 0
        
    
    def get_queue_percentage_done(self):
        if self.job_size == 0:
            return ""
        return str(100-100*len(self.tx_buffer)/self.job_size)


    
    def send_queue_as_ready(self):
        """Continuously call this to keep processing queue."""    
        if self.device:
            try:
                chars = self.device.read(self.RX_CHUNK_SIZE)
                if len(chars) > 0:
                    ## check for flow control chars
                    iXON = chars.rfind('>')
                    iXOFF = chars.rfind('<')
                    if iXON != -1 or iXOFF != -1:
                        if iXON > iXOFF:
                            print "=========================== XON"
                            self.remoteXON = True
                        else:
                            print "=========================== XOFF"
                            self.remoteXON = False
                        #remove control chars
                        for c in '>'+'<': 
                            chars = chars.replace(c, "")
                    ## assemble lines
                    self.rx_buffer += chars
                    posNewline = self.rx_buffer.find('\n')
                    if posNewline >= 0:  # we got a line
                        line = self.rx_buffer[:posNewline]
                        self.rx_buffer = self.rx_buffer[posNewline+1:]
                        # if line.find('error') > -1:
                        print "grbl: " + line
                
                if self.tx_buffer and self.remoteXON:
                    actuallySent = self.device.write(self.tx_buffer[:self.TX_CHUNK_SIZE])
                    # sys.stdout.write(self.tx_buffer[:actuallySent])  # print w/ newline
                    self.tx_buffer = self.tx_buffer[actuallySent:]  
                else:
                    self.job_size = 0
            except OSError:
                # Serial port appears closed => reset
                close()
            except ValueError:
                # Serial port appears closed => reset
                close()            

            
# singelton
SerialManager = SerialManagerClass()
