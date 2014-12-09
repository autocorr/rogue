#!/usr/bin/env python2
"""
=====
Rogue
=====

A simple console rogue-like game.
"""
# TODO
# Generate maps
# color
# synchronous rhythmic input and indicator, generate a bass-line or drum
#   beat using a given tempo
# more mobs
# doors
# vision and lighting
# loot and items
# vertical levels, stairs
# boss mobs
# store
# read in MP3, FFT to get beats, then use
#   that as input for the input


import random
from copy import deepcopy


class GameOver(Exception):
    pass


################################################################################
#                                  Position
################################################################################

class Position(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, pos):
        return Position(self.x + pos.x, self.y + pos.y)

    def __eq__(self, pos):
        return (self.x == pos.x) & (self.y == pos.y)

    def __repr__(self):
        return 'Position({x:4n},{y:4n})'.format(x=self.x, y=self.y)


cardinals = [
    Position(-1,  0),  # up
    Position( 1,  0),  # down
    Position( 0, -1),  # left
    Position( 0,  1),   # right
    ]


################################################################################
#                               Player Character
################################################################################

class Player(object):
    face = '@'
    color = None
    hp = 10
    coins = 0
    score = 0
    base_hit = 1
    
    def __init__(self, pos):
        self.pos = pos

    def move(self, pos):
        self.pos = pos

    def __repr__(self):
        return self.face

    def attack(self, mob):
        mob.hp -= self.base_hit

    def use_item(self, item):
        pass


################################################################################
#                                  Monsters
################################################################################

class Monster(object):
    face = None
    color = None
    hp = None
    score = None
    base_hit = None
    
    def __init__(self, pos):
        self.pos = pos

    def __repr__(self):
        return self.face

    def move(self, pos):
        self.pos = pos

    def attack(self, pl):
        pl.hp -= self.base_hit


class Bat(Monster):
    face = 'b'
    hp = 1
    score = 1
    base_hit = 1
    def get_move(self):
        return self.pos + random.choice(cardinals)


class Zombie(Monster):
    face = 'z'
    hp = 1
    score = 1
    base_hit = 1

    def __init__(self, pos):
        super(Zombie, self).__init__(pos)
        self.move_dir = random.choice(cardinals)
        self.old_pos = pos

    def get_move(self):
        if self.old_pos != self.pos:
            return self.pos + self.move_dir
        else:
            return self.pos + random.choice(cardinals)


################################################################################
#                                 Game Board
################################################################################

class Board(object):
    def __init__(self, lboard):
        self._b = lboard

    def __getitem__(self, pos):
        return self._b[pos.x][pos.y]

    def __str__(self):
        return '\n'.join([''.join([ti.face for ti in row])
                          for row in self._b]) 

    def __repr__(self):
        return 'Board(\n' + self.__str__() + '\n)'

    def __setitem__(self, pos, tile):
        self._b[pos.x][pos.y] = tile

    def is_valid_move(self, pos):
        return self[pos].is_passable


def read_board(fname):
    with open(fname, 'r') as ff:
        lboard = [[_tiles[cc](Position(ii, jj))
                   for jj, cc in enumerate(row.rstrip('\n'))]
                  for ii, row in enumerate(ff.readlines())]
    return Board(lboard)


################################################################################
#                                Board Tiles
################################################################################

class Tile(object):
    face = None
    color = None
    is_passable = False
    is_breakable = False
    is_swimmable = False

    def __init__(self, pos):
        self.pos = pos

    def __repr__(self):
        return self.face


class BlankSpaceTile(Tile):
    face = ' '


class DirtTile(Tile):
    face = '.'
    is_passable = True
     

class StoneWallTile(Tile):
    face = '#'


class WaterTile(Tile):
    face = '~'
    is_swimmable = True


_concrete_tiles = [DirtTile,
                   StoneWallTile,
                   WaterTile,
                   BlankSpaceTile,
                  ]

_tiles = {ti.face: ti for ti in _concrete_tiles}


################################################################################
#                               Event Loop
################################################################################

valid_keys = list('qwasd')
move_commands = {
    'w': Position(-1,  0),  # up
    's': Position( 1,  0),  # down
    'a': Position( 0, -1),  # left
    'd': Position( 0,  1),   # right
    }


class Game(object):
    kp = None

    def __init__(self, board, pl, mobs):
        self.board = board
        self.pl = pl
        self.mobs = mobs

    def handle_keypress(self):
        kp = None
        while True:
            kp = raw_input('> ')
            if kp in valid_keys:
                break
        if kp == 'q':
            raise GameOver()
        self.kp = kp

    def player_turn(self):
        if move_commands.has_key(self.kp):
            new_pos = self.pl.pos + move_commands[self.kp]
            valid_move = self.board.is_valid_move(new_pos)
            if new_pos in [mm.pos for mm in mobs]:
                mob = [mm for mm in self.mobs if mm.pos == new_pos][0]
                self.pl.attack(mob)
                if mob.hp <= 0:
                    self.pl.move(new_pos)
            elif valid_move:
                self.pl.move(new_pos)

    def mob_turn(self):
        for ii, mob in enumerate(self.mobs):
            if mob.hp <= 0:
                # TODO add loot
                #self.loot.append(mob.drop())
                self.pl.score += mob.score
                del(self.mobs[ii])
                continue
            new_pos = mob.get_move()
            if new_pos == self.pl.pos:
                mob.attack(pl)
            # TODO mobs cant occupy same space
            elif self.board.is_valid_move(new_pos):
                mob.move(new_pos)
        if self.pl.hp <= 0:
            raise GameOver()

    def draw(self):
        board = deepcopy(self.board)
        print '---------------'
        print 'Score  : {0:7n}'.format(self.pl.score)
        print 'Health : {0:2n} / 10'.format(self.pl.hp)
        print 'Coins  : {0:7n}'.format(self.pl.coins)
        board[self.pl.pos] = self.pl
        for mob in self.mobs:
            board[mob.pos] = mob
        print board


if __name__ == '__main__':
    board = read_board('test_map.txt')
    pl = Player(Position(2, 5))
    mobs = [Bat(Position(1, 3)), Zombie(Position(3, 7))]
    game = Game(board, pl, mobs)
    while True:
        try:
            game.draw()
            game.handle_keypress()
            game.player_turn()
            game.mob_turn()
        except GameOver:
            print 'Game Over'
            break


