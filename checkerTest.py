# pip install imparaai-checkers
#run above to get necessary import

from checkers import Game
from arm_controller import ArmController
import random
game = Game.Game()
arm = ArmController('192.168.100.100',3000) #'130.215.217.14',3000)
arm.connect()
game.consecutive_noncapture_move_limit = 50
while True:
	
	
	
	if game.whose_turn() == 1:
		if game.is_over():
			break
		print("\nYour possible moves: ")
		move_num = input( game.get_possible_moves() )
		print(game.get_possible_moves()[int(move_num)])
		game.move(game.get_possible_moves()[int(move_num)])
	
	if game.whose_turn() == 2:
		if game.is_over():
			break
		new_moves = game.get_possible_moves()
		index = random.randint(0,len(new_moves)-1)
		game.move(new_moves[index])
		print("\nThe computer made the move: ")
		print(new_moves[index])
	
print(game.get_winner())