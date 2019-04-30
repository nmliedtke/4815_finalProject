# pip install imparaai-checkers
# run above to get necessary import

from checkers import Game
from arm_controller import ArmController
import random
import time
import math
#from cmd import Cmd

# converts 32 board numbering system to 64 numbering system
def base32To64(cell_num):
	a = cell_num -1
	val = a%8

	if val >= 4:
		return (cell_num*2 - 1)
	else:
		return (cell_num*2)

def send_move(move, arm):
	#convert from 32 type number to 64 type
	move1 = base32To64(move[0])
	move2 = base32To64(move[1])

	print("move1: " + str(move1))
	print("move2: " + str(move2))

	#sends cell number, pickup/put down, meant to be trashed
	#[cell number in 64 cell notation, 0 = pick up | 1 = put down, 0 = trash]
	arm.move_j([move1,0,1])
	arm.move_j([move2, 1, 1])

	#logic for determining if move jumped a piece
	if(abs(move1-move2) >= 14):
		val = (move2-move1)/2
		pickup = move1+val
		#waits til human says to continue gameplay
		stop = input("tell when to go")
		
		#pickup and trash jumped piece
		arm.move_j([pickup,0,1])
		arm.move_j([pickup,1,0])

# initialize game object
game = Game.Game()
# set ip and port
arm = ArmController('192.168.125.1',3000) #'130.215.217.14',3000) #192.168.100.100
#attempt to connect
arm.connect()
game.consecutive_noncapture_move_limit = 50

while True:
	
	
	#human player turn
	if game.whose_turn() == 1:
		#breaks loop if game is over
		if game.is_over():
			break
		print("\nYour possible moves: ")
		move_num = input( game.get_possible_moves() ) #prints possible moves
		print(game.get_possible_moves()[int(move_num[:1])])
		move = game.get_possible_moves()[int(move_num)]
		game.move(game.get_possible_moves()[int(move_num)]) #sends move
		send_move(move,arm)

	#AI turn
	if game.whose_turn() == 2:
		#breaks loop if game is over
		if game.is_over():
			break
		#waits til human says to continue gameplay
		stop = input("tell when to go")
		new_moves = game.get_possible_moves()
		index = random.randint(0,len(new_moves)-1) # pick random move index
		game.move(new_moves[index])
		send_move(new_moves[index],arm) #sends move
		print("\nThe computer made the move: ")
		print(new_moves[index])
	
print(game.get_winner()) # prints 1 if human won, 2 if AI won
