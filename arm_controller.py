# load additional Python module
import socket
import time
import threading
#import fcntl, os
import errno
import math

SPEED_DEFAULT = 5000
DELAY_NETWORK = 0.4

class ArmController():
	
	def __init__(self, host='localhost', port=3000):
		self.host = host
		self.port = port
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.settimeout(10000)

		#fcntl.fcntl(self.sock, fcntl.F_SETFL, os.O_NONBLOCK)

		self.seq_num = 1
		self.commands = []

		self.current_pos = None

	def connect(self):
		server_address = (self.host, self.port)
		print ('Connecting on %s port %s' % server_address)

		self.sock.connect(server_address)

		print('Connected!')
		print('')

		threading.Thread(target=self.listen).start()

	def listen(self):
		while True:

			try:
				msg = self.sock.recv(4)
			except socket.error as e:
				err = e.args[0]
				if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
					time.sleep(1)
					print('No data available')
					continue
				else:
					# a "real" error occurred
					print(e)
					return
			else:
				# got a message, do something :)
				print("GOT",msg)
				seq_num = int(msg[0]) - 48
				print("GOOTTA",seq_num)

				for c in self.commands:
					if c.seq_num == seq_num:
						c.complete = True
						self.current_pos = c.args[0:3]


	def move_default():
		pass

	def move_zero(self):
		print('CMD: Reset zeros')
		return self.cmd_raw(2)

	def move_j(self,pos,speed=-1):
		print('CMD: MoveJ')
		if speed < 0: speed = SPEED_DEFAULT

		self.bounds_check(pos)

		return self.cmd_raw(1,pos+[speed])

	def move_c(self,pos_c,pos_d,speed=-1):
		print('CMD: MoveC')
		if speed < 0: speed = SPEED_DEFAULT

		self.bounds_check(pos_c)
		self.bounds_check(pos_d)

		return self.cmd_raw(4,pos_c+pos_d+[speed])

	def move_c_auto(self,pos,speed=-1):
		if not self.current_pos:
			raise Exception("Cannot move_c_auto without knowing current position")

		if dist(pos,self.current_pos) < 15:
			return self.move_j(pos,speed)

		pos_c = [
			(self.current_pos[0] + pos[0])/2,
			(self.current_pos[1] + pos[1])/2,
			pos[2]+abs(self.current_pos[0] - pos[0])/2
		]
		print('auto circle',self.current_pos,pos_c,pos)
		return self.move_c(pos_c,pos,speed)

	def move_c_h(self,pos,height,speed=-1):
		if not self.current_pos:
			raise Exception("Cannot move_c_auto without knowing current position")


		pos_c = [
			(self.current_pos[0] + pos[0])/2,
			(self.current_pos[1] + pos[1])/2,
			pos[2]+ abs(self.current_pos[0] - pos[0]) * height/2
		]
		return self.move_c(pos_c,pos,speed)

	def time_move_j(self,pos,speed):
		if not self.current_pos:
			return None

		cp = self.current_pos
		np = pos
		dx = cp[0]-np[0]
		dy = cp[1]-np[1]
		dz = cp[2]-np[2]

		return math.sqrt(dx*dx + dy*dy + dz*dz) / speed + DELAY_NETWORK  # + 1 for network delay


	def bounds_check(self,pos):
		if pos[0] < -200 or pos[0] > 600:
			raise Exception('Safety warning: Position out of bounds')
		if pos[1] < -200 or pos[1] > 100:
			raise Exception('Safety warning: Position out of bounds')
		if pos[2] < -100 or pos[2] > 100:
			raise Exception('Safety warning: Position out of bounds')

	def cmd_raw(self,cmd,args=[]):
		payload = " ".join([str(cmd),str(self.seq_num)] + [str(a) for a in args] + ["#"])


		self.sock.send(bytes(payload,"utf-8"))

		print('Sending command type = '+str(cmd)+' with payload = '+payload)


		command = ArmCommand(self.seq_num,args)
		self.commands.append(command)

		self.seq_num = (self.seq_num + 1) % 10

		return command

	def disconnect(self):
		self.sock.close()

def dist(p1,p2):
	d0 = p1[0] - p2[0]
	d1 = p1[1] - p2[1]
	d2 = p1[2] - p2[2]

	return math.sqrt(d0*d0 + d1*d1 + d2*d2)

class ArmCommand():
	def __init__(self,seq_num,args):
		self.complete = False
		self.seq_num = seq_num
		self.args = args

	def is_complete(self):
		return self.complete

def main():

	print('Master Controller Interface v0.1')
	print('')

	controller = ArmController('192.168.100.100',3000) # 130.215.217.14
	controller.connect()

	controller.move_j([0,0,0])


	# controller.move_zero()
	# time.sleep(3)
	# controller.cmd_raw(1,[0,0,100])
	# time.sleep(3)
	# controller.move_j([100,0,100])
	
	# time.sleep(7)
	# controller.move_c([200,0,130],[300,0,100])
	# time.sleep(7)
	# controller.move_c([450,0,190],[600,0,100])
	# time.sleep(30)


if __name__ == '__main__':
	main()