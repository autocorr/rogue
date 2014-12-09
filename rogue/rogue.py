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
#   that as beat for the input


import random
from copy import deepcopy
from collections import deque
import numpy as np
from blessings import Terminal
term = Terminal()


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

    def __sub__(self, pos):
        return Position(self.x - pos.x, self.y - pos.y)

    def __eq__(self, pos):
        return (self.x == pos.x) & (self.y == pos.y)

    def __repr__(self):
        return 'Position({x:4n},{y:4n})'.format(x=self.x, y=self.y)

    def copy(self):
        return deepcopy(self)


cardinals = [
    Position(-1,  0),  # up
    Position( 1,  0),  # down
    Position( 0, -1),  # left
    Position( 0,  1),  # right
    ]


################################################################################
#                               Player Character
################################################################################

class Player(object):
    name = '@'
    face = '{t.bold}{t.yellow}{name}{t.normal}'.format(t=term, name=name)
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

    def rand_card(self):
        return random.choice(cardinals)

    def rand_step(self):
        return self.pos + self.rand_card()


class Bat(Monster):
    name = 'b'
    face = '{t.blue}{name}{t.normal}'.format(t=term, name=name)
    hp = 1
    score = 1
    base_hit = 1

    def __init__(self, pos):
        super(Bat, self).__init__(pos)
        self.move_until = 1

    def get_move(self):
        if self.move_until == 0:
            self.move_until = 1
            return self.rand_step()
        else:
            self.move_until -= 1
            return self.pos


class Zombie(Monster):
    name = 'z'
    face = '{t.green}{name}{t.normal}'.format(t=term, name=name)
    hp = 1
    score = 1
    base_hit = 1

    def __init__(self, pos):
        super(Zombie, self).__init__(pos)
        self.move_dir = self.rand_card()
        self.last_pos = pos

    def get_move(self):
        if self.last_pos == self.pos:
            self.move_dir = self.rand_card()
            self.last_pos = self.pos.copy()
            return self.pos + self.move_dir
        else:
            self.last_pos = self.pos.copy()
            return self.pos + self.move_dir


class GreenSlime(Monster):
    name = 's'
    face = '{t.green}{name}{t.normal}'.format(t=term, name=name)
    hp = 1
    score = 1
    base_hit = 1

    def get_move(self):
        return self.pos


class BlueSlime(Monster):
    name = 's'
    face = '{t.blue}{name}{t.normal}'.format(t=term, name=name)
    hp = 1
    score = 1
    base_hit = 1

    def __init__(self, pos):
        super(BlueSlime, self).__init__(pos)
        self.moves = deque([Position( 1, 0),
                            Position( 0, 0),
                            Position(-1, 0),
                            Position( 0, 0)])

    def get_move(self):
        self.moves.rotate()
        return self.pos + self.moves[0]


################################################################################
#                                 Game Board
################################################################################

class Board(object):
    def __init__(self, lboard):
        self._b = lboard
        # create array
        xmax = max([ii.pos.x for ii in sum(lboard, []) if ii.is_clear_view])
        ymax = max([ii.pos.y for ii in sum(lboard, []) if ii.is_clear_view])
        self._v = np.zeros((xmax, ymax))

    def __getitem__(self, pos):
        return self._b[pos.x][pos.y]

    def __str__(self):
        return '\n'.join([''.join([ti.face for ti in row])
                          for row in self._b])

    def __repr__(self):
        return 'Board(\n' + self.__str__() + '\n)'

    def __setitem__(self, pos, tile):
        self._b[pos.x][pos.y] = tile

    def flatten(self):
        return sum(self._b, [])

    def is_valid_move(self, pos):
        return self[pos].is_passable

    def copy(self):
        return deepcopy(self)


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
    is_passable = False
    is_breakable = False
    is_swimmable = False
    is_clear_view = False

    def __init__(self, pos):
        self.pos = pos

    def __repr__(self):
        return self.face


class BlankSpaceTile(Tile):
    name = ' '
    face = name


class DirtTile(Tile):
    name = '.'
    face = '{t.dim}{t.gray}{name}{t.normal}'.format(t=term, name=name)
    is_passable = True
    is_clear_view = True


class StoneWallTile(Tile):
    name = '#'
    face = '{t.dim}{t.gray}{name}{t.normal}'.format(t=term, name=name)


class WaterTile(Tile):
    name = '~'
    face = '{t.blue}{name}{t.normal}'.format(t=term, name=name)
    is_swimmable = True
    is_clear_view = True


class LavaTile(Tile):
    name = '~'
    face = '{t.red}{name}{t.normal}'.format(t=term, name=name)
    is_clear_view = True


_concrete_tiles = [DirtTile,
                   StoneWallTile,
                   WaterTile,
                   BlankSpaceTile,
                  ]

_tiles = {ti.name : ti for ti in _concrete_tiles}


################################################################################
#                               Event Loop
################################################################################

valid_keys = list('qwasd+')
move_commands = {
    'w': Position(-1,  0),  # up
    's': Position( 1,  0),  # down
    'a': Position( 0, -1),  # left
    'd': Position( 0,  1),   # right
    }


class Screen(object):
    stats_str = \
"""----------------
Score  : {pl.score:7n}
Health : {pl.hp:2n} / 10
Coins  : {pl.coins:7n}
----------------"""
    stats_pos = Position(0, 1)
    map_pos = Position(6, 2)

    def draw_stats(self, pl):
        with term.location():
            pos = self.stats_pos
            for ii, line in enumerate(self.stats_str.split('\n')):
                print term.move(pos.x + ii, pos.y) + line.format(pl=pl)

    def draw_board(self, board):
        with term.location():
            for tile in board.flatten():
                pos = self.map_pos + tile.pos
                print term.move(pos.x, pos.y) + tile.face

    def draw_player(self, pl):
        with term.location():
            pos = self.map_pos + pl.pos
            print term.move(pos.x, pos.y) + pl.face

    def draw_mobs(self, mobs):
        with term.location():
            for mob in mobs:
                pos = self.map_pos + mob.pos
                print term.move(pos.x, pos.y) + mob.face

    def get_keypress(self):
        while True:
            kp = raw_input(term.move(term.height - 2, 1) +
                           term.clear_eol + term.clear_bol + '> ')
            if kp in valid_keys:
                return kp


class Game(object):
    kp = None

    def __init__(self, board, pl, mobs, screen):
        self.board = board
        self.pl = pl
        self.mobs = mobs
        self.screen = screen

    def draw(self):
        print term.clear()
        self.screen.draw_stats(self.pl)
        self.screen.draw_board(self.board)
        self.screen.draw_mobs(self.mobs)
        self.screen.draw_player(self.pl)

    def handle_keypress(self):
        kp = self.screen.get_keypress()
        if kp == 'q':
            raise GameOver()
        elif kp == '+':
            import ipdb
            ipdb.set_trace()
        self.kp = kp

    def player_turn(self):
        if move_commands.has_key(self.kp):
            new_pos = self.pl.pos + move_commands[self.kp]
            valid_move = self.board.is_valid_move(new_pos)
            if new_pos in [mm.pos for mm in self.mobs]:
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


if __name__ == '__main__':
    screen = Screen()
    board = read_board('test_map.txt')
    pl = Player(Position(2, 5))
    mobs = [Bat(Position(1, 3)),
            Zombie(Position(3, 7)),
            BlueSlime(Position(4, 16))]
    game = Game(board, pl, mobs, screen)
    while True:
        try:
            game.draw()
            game.handle_keypress()
            game.player_turn()
            game.mob_turn()
        except GameOver:
            print 'Game Over'
            break


