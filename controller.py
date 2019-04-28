from .arm_controller import ArmController
from .hand_controller import HandController

from cmd import Cmd

import time
import json
import threading

NOTES_BLACK = [126,
None,
123,
121,
None,
118,
116,
114,
None,
111,
109,
None,
106,
104,
102,
None,
99,
97,
None,
94,
92,
90,
None,
87,
85,
None,
82,
80,
78,
None,
75,
73,
None,
70,
68,
66,
None,
63,
61,
None,
58,
56,
54,
None,
51,
49,
None,
46,
44,
42,
None,
39,
37,
None,
34,
32,
30,
None,
27,
25,
None,
22]

def get_white_notes():
	result = []
	for i in range(127):
		if i not in NOTES_BLACK:
			result.append(i)

	return result

NOTES_WHITE = get_white_notes()


# TODO this is a little more complicated than just a constant?
finger_motion_full_delay = .300 # milliseconds
min_note_duration = .100

class MasterController():
	def __init__(self,hand_serial,hand_baud,arm_ip,arm_port):
		
		self.hand = HandController(hand_serial,hand_baud)
		# self.hand.listen(pt)

		self.arm = ArmController(arm_ip,arm_port) #'130.215.217.14',3000)
		self.arm.connect()

		self.thread = threading.Thread(target=self.loop)
		self.action_queue = []
		self.finger_states = [False,False,False,False,False]

	def play_note_simple(self,note):
		finger = 0
		state = True
		self.hand.cmd_raw(finger,state)
		self.arm.move_j([200,0,100])


	def play_stream(self,stream):
		self.stream = stream
		self.start_thread()


	def start_thread(self):
		self.thread.start()

	def execute_action(self,action):
		
	
		print('executing',action)

			

		if action.type == 'noop':
			pass

		if action.type == 'move':
			action.is_done = self.arm.move_c_auto(action.args[0:3]).is_complete # ,action.args[3]

		if action.type == 'finger_down':
			self.finger_set(action.args[0],True)

		if action.type == 'finger_up_all':
			self.fingers_reset()
		

	def execute_action_queue(self,time=0):
		while len(self.action_queue) > 0 and self.action_queue[0].is_ready(time):
			print('Executing at t='+str(time))
			self.execute_action(self.action_queue.pop(0))


	def add_action(self,action):
		self.action_queue.append(action)
		if action.delay == 'wait_prev':
			action.delay = 'wait_cond'
			action.ready_condition = self.action_queue[-2]
			print('wait_cond',self.action_queue,self.action_queue[-2],self.action_queue[-2].is_done)

	def arm_pos_for_range(self,r):
		if r.type == HandRange.TYPE_BLACK:
			index = NOTES_BLACK.index(r.start.pitch) - 38
			return [10 + index * 23.5, 40, -70]

		index = NOTES_WHITE.index(r.start.pitch) - 44
		return [index * 23.5,0,-85]

	def loop(self):

		window_size = 5

		predelay = 0

		current_range = HandRange.range_from_notes(self.stream.notes)
		print('range start',current_range.start)

		self.arm.move_j(self.arm_pos_for_range(current_range))
		time.sleep(1)

		prev_note = None

		start = time.time()


		while True:
			now = time.time() - start - predelay
			focus = now + window_size

			self.execute_action_queue(now)


			current_stream = self.stream.notes_in_window(now,focus)
			next_note = current_stream.next_unprocessed()




			if not next_note:
				if len(self.stream.notes_after(now).notes) > 0:
					continue
				break

			time_until_note = next_note.time - now

			next_note.processed = True


			if next_note in current_range:
				# Move the right finger at the right predelay
				
				inter_delay = 0
				if prev_note and next_note.pitch == prev_note.pitch:
					inter_delay = 0.5


				self.add_action(RobotAction('noop',time=now,delay=time_until_note-inter_delay))
				self.add_action(RobotAction('finger_up_all'))
				self.add_action(RobotAction('noop',time=next_note.time-inter_delay,delay=inter_delay))
				self.add_action(RobotAction('finger_down',args=[current_range.get_index(next_note)]))
				self.add_action(RobotAction('noop',time=next_note.time,delay=finger_motion_full_delay))

				print('action simple',time_until_note)

			else:

				new_range = HandRange.range_from_notes(current_stream.notes_starting_at(next_note).notes)

				if next_note not in new_range:
					print('not in new range')
					print(new_range.start.pitch,[n.pitch for n in current_stream.notes],now,next_note.pitch)
					# We are looking too far ahead
					continue


				estimated_delay = 0

				# Finger must go up from current position, and down at new position
				estimated_delay += finger_motion_full_delay
				estimated_delay += finger_motion_full_delay

				new_pos = self.arm_pos_for_range(new_range) # BIG TODO WTF

				arm_delay = self.arm.time_move_j(new_pos,250)

				# How long will the arm take to move?
				estimated_delay += arm_delay


				

				# It takes too long to move to the next note - we should delay everything
				if estimated_delay > time_until_note:
					predelay += estimated_delay - time_until_note + min_note_duration
					# self.stream.add_delay(estimated_delay - time_until_note + min_note_duration)
					self.add_action(RobotAction('noop',time=next_note.time-estimated_delay-min_note_duration,delay=min_note_duration))
				else:
					self.add_action(RobotAction('noop',time=now,delay=time_until_note-estimated_delay))

				self.add_action(RobotAction('finger_up_all'))
				self.add_action(RobotAction('noop',time=next_note.time-estimated_delay,delay=finger_motion_full_delay))
				self.add_action(RobotAction('move',args=new_pos))#+[next_note.velocity/127.0]))
				self.add_action(RobotAction('noop',time=next_note.time-estimated_delay+finger_motion_full_delay,delay='wait_prev'))#delay=arm_delay))
				self.add_action(RobotAction('finger_down',args=[new_range.get_index(next_note)]))
				self.add_action(RobotAction('noop',time=next_note.time-finger_motion_full_delay,delay=finger_motion_full_delay))

				print('action big',estimated_delay,new_pos)
				print('gonna play finger',new_range.get_index(next_note))

				
				# BIG TODO- if all predelay is too long to next note, add to stream delta s

				current_range = new_range
				print('range start',current_range.start)

			prev_note = next_note

			# TODO
			# 	Adjust focus range to accommodate upcoming notes (far ahead) -- only do this each time next note is outside range
			# 	Prepare motion ahead of time for next note (immediately upcoming, test if (now >= upcoming note time - movement delta) range is reached)
			# 	
			# 	Prepare motion with full understanding of finger motion time delay before arm can move
			# 	along with accurate timing for when arm is in place for finger depression


	def arm_move_j(self,pos):
		self.arm.move_j(pos)

	def finger_set(self,finger,state):
		self.finger_states[finger] = state
		self.hand.cmd_raw(finger,state)
		# self.arm.move_j([200,0,100])
	def fingers_reset(self):
		for i in range(len(self.finger_states)):
			if self.finger_states[i]:
				self.finger_set(i,False)

class RobotAction(object):


	def __init__(self, type, **kwargs):
		self.type = type
		self.time = kwargs.get('time',None)
		self.args = kwargs.get('args',None)
		self.delay = kwargs.get('delay',None)
		self.is_done = kwargs.get('is_done',None)
		self.prev_action = kwargs.get('prev_action',None)
		self.ready_condition = kwargs.get('ready_condition',None)
		self.delay_start = 1e12
		self.arm_cmd = None

	def __str__(self):
		s = 'RobotAction '+self.type+' '
		if self.args:
			if list(self.args):
				s += ' '.join([str(x) for x in list(self.args)]) +' '

		if hasattr(self,'time'):
			s += 'time='+str(self.time) + ' '

		if hasattr(self,'delay'):
			s += 'delay='+str(self.delay) + ' '
		return s


	def is_ready(self,time):

		ready = True

		if self.type == 'noop':
			if self.delay == 'wait_cond':
				if callable(self.ready_condition):
					return self.ready_condition()

				if isinstance(self.ready_condition,RobotAction):
					return self.ready_condition.is_done()

				return False

			return time > self.time + self.delay

		if self.type == 'waitfor':
			return self.ready_condition()

		return ready

		# BIG TODO -- must be able to wait for a command, then once it is done, ADD a FIXED time delay to wait before this action is ready to execute


		if hasattr(self,'ready_condition') and self.ready_condition != None:
			ready = self.ready_condition()
			if not ready:
				return False
			self.delay_start = time
			self.ready_condition = None

		if hasattr(self,'prev_action') and self.prev_action != None:
			ready = self.prev_action.is_ready()
			if not ready:
				return False
			self.delay_start = time
			self.prev_action = None

		# DELAY after above conditions met
		if hasattr(self,'delay') and self.delay != None:
			ready = time - self.delay_start > self.delay

		# FIXED time
		if hasattr(self,'time') and self.time != None:
			ready = ready or self.time > time

		

		

		return ready
		


PITCH_MAX = 90
PITCH_MIN = 30

class NoteStream():
	
	@classmethod
	def load_file(self,filename):
		with open(filename,'r') as f:
			notes = []
			line = f.readline()
			while line != '':
				data = json.loads(line)
				notes.append(Note(data['note'],data['time']))
				line = f.readline()

			return NoteStream(notes)

	def __init__(self, notes=[]):
		self.notes = []
		for n in notes:
			self.add_note(n)

	def add_note(self, note):
		self.notes.append(note)
		self.notes.sort(key=lambda n: n.time)

	def notes_in_window(self, start, end):
		result = []
		for n in self.notes:
			if n.time > start and n.time < end:
				result.append(n)

		return NoteStream(result)

	def notes_after(self, time):
		result = []
		for n in self.notes:
			if n.time > time:
				result.append(n)

		return NoteStream(result)

	def notes_starting_at(self, note):
		result = []
		for n in self.notes:
			if n.time >= note.time:
				result.append(n)

		return NoteStream(result)


	def next_unprocessed(self):
		notes = [n for n in self.notes if not n.processed]
		if len(notes) == 0:
			return None
		return notes[0]

	def add_delay(self,delay):
		for n in self.notes:
			n.time += delay

	def multiply_time(self,mul):
		for n in self.notes:
			n.time *= mul

	def min_pitch(self):
		val = PITCH_MAX
		for n in self.notes:
			val = min(val,n.pitch)
		return val

	def max_pitch(self):
		val = PITCH_MIN
		for n in self.notes:
			val = max(val,n.pitch)
		return val



class HandRange():
	TYPE_BLACK = "black"
	TYPE_WHITE = "white"

	def __init__(self, start):
		self.start = start
		self.type = self.note_type(start)

	@classmethod
	def range_from_notes(cls,notes):
		if len(notes) == 1:
			return HandRange(notes[0])

		subarr = notes[:-1]
		last = notes[-1]
		r = cls.range_from_notes(subarr)
		r2 = HandRange(last)

		if subarr in r2:
			return r2

		return r
		

	def __contains__(self,note):
		if isinstance(note,list):
			return self.are_inside(note)

		return self.is_inside(note)

	def get_index(self,note):
		if note not in self: return None
		
		try:
			result = self.get_span().index(note.pitch)
			return result
		except:
			return None

	def is_inside(self,note):
		if self.type != self.note_type(note):
			return False

		return note.pitch in self.get_span()

	def are_inside(self,notes):
		for n  in notes:
			if not self.is_inside(n):
				return False
		return True

	def get_span(self,size=5):
		space = self.get_space()
		start_index = space.index(self.start.pitch)
		
		return space[start_index:start_index + size]


	def get_space(self):

		if self.type == self.TYPE_BLACK:
			return NOTES_BLACK
		return NOTES_WHITE

	def note_type(self,note):
		if note.pitch in NOTES_BLACK:
			return self.TYPE_BLACK
		return self.TYPE_WHITE


		

class Note():
	def __init__(self, pitch, time, velocity=100):
		self.pitch = pitch
		self.time = time
		self.processed = False
		self.velocity = velocity



def pt(data):
	print(str(data) + " -- " + ", ".join([str(a) for a in data])) 

 
class ControllerPrompt(Cmd):
	prompt = 'ROBOT> '


	def set_controller(self,controller):
		self.controller = controller

	def do_exit(self, inp):
		print('Exiting')
		return True

	def do_armmove(self, inp):
		tok = inp.split(' ')
		if len(tok) == 4:
			print('Need exactly 3 arguments for position X, Y, and Z')
			return False

		pos = [float(n) for n in tok]
		self.controller.arm_move_j(pos)

	def do_armmarc(self, inp):
		tok = inp.split(' ')
		if len(tok) == 7:
			print('Need exactly 6 arguments for 2 positions, each X, Y, and Z')
			return False

		pos = [float(n) for n in tok]
		self.controller.arm_move_c(pos[1:4],pos[5:7])


	def do_armzero(self, inp):
		self.controller.arm.move_zero()

	def do_fingerdown(self, inp):
		finger = int(inp)
		self.controller.finger_set(finger,True)

	def do_fingerup(self, inp):
		finger = int(inp)
		self.controller.finger_set(finger,False)

	do_EOF = do_exit




cmd1 = 0
cmd2 = 0
def loop():
	global cmd1
	global cmd2
	c = 1
	d = 1e9
	e = 1e9
	start = time.time()
	while True:
		now = time.time() - start
		if c == 1:
			cmd1 = controller.arm.move_j([0,0,0])
			c = 2

		if cmd1 != 0 and cmd1.complete and c == 2:
			print('cmd1.complete!!!!',now)
			controller.finger_set(0,True)
			c = 3

		if c == 3:
			time.sleep(0.5)
			controller.finger_set(0,False)
			c = 4
			time.sleep(0.1) # finger motion full delay

		if c == 4:
			d = now
			cmd2 = controller.arm.move_j([400,0,0])
			e = time.time()-start
			c = 5

		if cmd2 != 0 and cmd2.complete and c == 5:
			print('cmd2.complete!!!!',now)
			controller.finger_set(4,True)
			print('finger is DOWNNNNN',time.time()-start)
			time.sleep(0.5)
			controller.finger_set(4,False)
			c = 6

		if now - d >= 1.6:
			print("I THINK IT'S DONE",now)
			d = 1e9

		if now - e >= 1.6:
			print("I THINK IT'S DONE v2",now)
			e = 1e9

def main():

	# global controller
	controller = MasterController(
		'/dev/tty.usbmodem1411',
		9600,
		'192.168.100.100', #'130.215.217.14', #'192.168.100.100',
		3000
	)
	# controller = MasterController(
	# 	'/dev/tty.usbmodem1421',
	# 	9600,
	# 	'130.215.120.237', #'130.215.217.14', #'192.168.100.100',
	# 	3000
	# )

	# threading.Thread(target=loop).start()

	# time.sleep(30)

	# armcommand = controller.arm.move_j([0,0,0])
	# print(armcommand.complete)
	# time.sleep(5)
	# print(armcommand.complete)
	# time.sleep(2)
	# armcommand = controller.arm.move_j([200,0,0])
	# print(armcommand.complete)
	# time.sleep(5)
	# print(armcommand.complete)


	# controller.finger_set(2,True)
	# time.sleep(1)
	# controller.finger_set(2,False)
	# time.sleep(0.1)
	# controller.arm.move_c([-200,0,100],[-400,0,0])
	# time.sleep(2)
	# controller.finger_set(0,True)
	# time.sleep(1)
	# controller.finger_set(0,False)

	notes = [
		Note(2,1),
		Note(1,2),
		Note(0,3),
		Note(1,4),
		Note(2,5),
		Note(2,6),
		Note(2,7),

		Note(1,9),
		Note(1,10),
		Note(1,11),

		Note(2,13),
		Note(4,14),
		Note(4,15)


	]

	notes2 = [ # twinkle
		Note(0,1), # C
		Note(0,2), # C
		Note(4,3),  # G
		Note(4,4), # G
		Note(5,5), # A
		Note(5,6), # A
		Note(4,7), # G
		Note(3,10), # G
		Note(3,11), # G
		Note(2,12), # G
		Note(2,13), # G
		Note(1,14), # G
		Note(1,15), # C
		Note(0,16) # C
	]

	notes2 = [
		Note(0,2), # C
		Note(1,3), # D
		Note(2,4),  # e
		Note(3,5), # f
		Note(4,6), # g
		Note(5,9), # C
		Note(6,10), # C
		Note(7,11.5) # C
	]

	# notes2 = [
	# 	Note(0,0), # C
	# 	Note(1,3), # D
	# 	Note(7,5),  # C
	# 	Note(9,6), # E
	# 	Note(0,9) # C
	# ]
	stream = NoteStream(notes2)
	controller.fingers_reset()
	controller.arm.move_j([0,0,-85])
	time.sleep(3)
	controller.play_stream(stream)

	# time.sleep(10)

	controller.fingers_reset()


	prompt = ControllerPrompt()
	prompt.set_controller(controller)
	prompt.cmdloop()



	return
	# controller = MasterController()
	controller.finger_set(4,True)
	time.sleep(1)
	controller.finger_set(4,False)
	time.sleep(1)
	controller.finger_set(3,True)
	time.sleep(1)
	controller.finger_set(3,False)
	# controller.finger_set(2,True)

if __name__ == '__main__':
	main()