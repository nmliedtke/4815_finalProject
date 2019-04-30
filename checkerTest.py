# pip install imparaai-checkers
#run above to get necessary import

from checkers import Game
from arm_controller import ArmController
import random
import time
import math
#from cmd import Cmd

def base32To64(cell_num):
	a = cell_num -1
	val = a%8

	if val >= 4:
		return (cell_num*2 - 1)
	else:
		return (cell_num*2)

def send_move(move, arm):
	move1 = base32To64(move[0])
	move2 = base32To64(move[1])

	print("move1: " + str(move1))
	print("move2: " + str(move2))

	arm.move_j([move1,0,1])
	arm.move_j([move2, 1, 1])

	if(abs(move1-move2) >= 14):
		val = (move2-move1)/2
		pickup = move1+val
		stop = input("tell when to go")
		arm.move_j([pickup,0,1])
		arm.move_j([pickup,1,0])







game = Game.Game()
arm = ArmController('192.168.125.1',3000) #'130.215.217.14',3000) #192.168.100.100
arm.connect()
game.consecutive_noncapture_move_limit = 50
#arm.move_j([8,0,1])
while True:
	
	
	
	if game.whose_turn() == 1:
		if game.is_over():
			break
		print("\nYour possible moves: ")
		move_num = input( game.get_possible_moves() )
		print(game.get_possible_moves()[int(move_num[:1])])
		move = game.get_possible_moves()[int(move_num)]
		game.move(game.get_possible_moves()[int(move_num)])
		send_move(move,arm)


	
	if game.whose_turn() == 2:
		if game.is_over():
			break
		stop = input("tell when to go")
		new_moves = game.get_possible_moves()
		index = random.randint(0,len(new_moves)-1)
		game.move(new_moves[index])
		send_move(new_moves[index],arm)
		print("\nThe computer made the move: ")
		print(new_moves[index])
	
print(game.get_winner())