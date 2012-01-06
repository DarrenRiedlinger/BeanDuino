from Queue import Queue
from threading import Thread
import time
import serial

COM_PORT = 'COM7'

def recieving(s, q):
	while True:
		q.put(s.readline().strip())

class SerialData(object):
	def __init__(self):
		try:
        		self.ser = ser = serial.Serial(
        	                port=COM_PORT,
        	                baudrate=9600,
        	                bytesize=serial.EIGHTBITS,
        	                parity=serial.PARITY_NONE,
        	                stopbits=serial.STOPBITS_ONE,
        	                timeout=None,
        	                xonxoff=0,
        	                rtscts=0,
        	                interCharTimeout=None
        	            )
		except serial.serialutil.SerialException:

			#no serial connection
              	        print 'No Serial Connection'
              	        self.ser = None
        	else:
        	        self.queue = Queue()
			Thread(target=recieving, args=(self.ser, self.queue,)).start()
			time.sleep(5) # Give arduino a chance to reset



	def next(self):

		#See if there is new data in queue
		if self.queue.empty():
			return False
		else:
			try:
				time_s,temp = self.queue.get().split(' ')
				time_m = float(time_s)/60.0
				temp = float(temp)
			#If there arent two values or if they cant be 
			#converted to floats
			except ValueError:
				return False
			else:
				return (time_m, temp)
	def __del__(self):
		if self.ser:
			self.ser.close()

if __name__=='__main__':
	s = SerialData()

	while True:
		vals = s.next()
		if vals:
			print u'%.2F min: %.2F\u00B0' % vals
		time.sleep(.01) # Just to prevent CPU from maxing out








	
