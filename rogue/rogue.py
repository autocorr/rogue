#!/usr/bin/env python2
"""
=====
Rogue
=====

A simple console rogue-like game.

"""
# TODO
# doors
# generate maps
# vision
# unit pathing
# lighting
# loot and items
# synchronous rhythmic input and indicator, generate a bass-line or drum
#   beat using a given tempo
# vertical levels, stairs
# boss mobs
# shopkeeper & store
# read in MP3, FFT to get beats, then use
#   that as beat for the input

import random
import subprocess
import numpy as np
from copy import deepcopy
from collections import deque
from blessings import Terminal


term = Terminal()


################################################################################
#                                 Exceptions
################################################################################

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
    hp = 2
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
        # Set vision arrays
        xmax = max([ii.pos.x for ii in lboard]) + 1
        ymax = max([ii.pos.y for ii in lboard]) + 1
        self._v = np.zeros((xmax, ymax))
        self._m = np.zeros((xmax, ymax))
        for tile in lboard:
            if tile.is_clear_view:
                self._v[tile.pos.x, tile.pos.y] = 1
            if tile.is_passable:
                self._m[tile.pos.x, tile.pos.y] = 1
        # Set stairs
        self.upstairs = [tt for tt in lboard if tt.name == '<'][0]
        self.downstairs = [tt for tt in lboard if tt.name == '>'][0]

    def __getitem__(self, pos):
        return self._b[pos.y + 50 * pos.x]

    def __str__(self):
        return '\n'.join([''.join([ti.face for ti in row])
                          for row in self._b])

    def __repr__(self):
        return 'Board(\n' + self.__str__() + '\n)'

    def __setitem__(self, pos, tile):
        self._b[pos.y + 50 * pos.x] = tile

    def tiles(self):
        return self._b

    def copy(self):
        return deepcopy(self)


def get_floor():
    floor = subprocess.Popen(['./map_generator'],
                             stdout=subprocess.PIPE).communicate()[0]
    floor = floor.replace('X', ' ')
    floor = [floor[ii:ii+50] for ii in range(0, 15 * 50, 50)]
    lboard = []
    for ii, row in enumerate(floor):
        for jj, ctile in enumerate(row):
            tile = _tiles[ctile](Position(ii, jj))
            lboard.append(tile)
    board = Board(lboard)
    return board


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
    is_openable = False
    is_stairs = False

    def __init__(self, pos):
        self.pos = pos

    def __repr__(self):
        return self.face


class DirtWallTile(Tile):
    name = ' '
    face = name


class DirtFloorTile(Tile):
    name = '.'
    face = '{t.dim}{t.gray}{name}{t.normal}'.format(t=term, name=name)
    is_passable = True
    is_clear_view = True


class StoneWallTile(Tile):
    name = '#'
    face = '{t.dim}{t.gray}{name}{t.normal}'.format(t=term, name=name)


class DoorTile(Tile):
    name = '+'
    face = '{t.dim}{t.gray}{name}{t.normal}'.format(t=term, name=name)
    is_openable = True

    def opened(self):
        self.name = DirtFloorTile.name
        self.face = DirtFloorTile.face
        self.is_passable = True
        self.is_clear_view = True
        self.is_openable = False


class UpStairsTile(Tile):
    name = '<'
    face = '{t.dim}{t.gray}{name}{t.normal}'.format(t=term, name=name)
    is_clear_view = True
    is_passable = True
    is_stairs = True
    delta_z = +1


class DownStairsTile(Tile):
    name = '>'
    face = '{t.dim}{t.gray}{name}{t.normal}'.format(t=term, name=name)
    is_clear_view = True
    is_passable = True
    is_stairs = True
    delta_z = -1


_concrete_tiles = [DirtWallTile,
                   DirtFloorTile,
                   StoneWallTile,
                   DoorTile,
                   UpStairsTile,
                   DownStairsTile,
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
            for tile in board.tiles():
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
            move_tile = self.board[new_pos]
            if new_pos in [mm.pos for mm in self.mobs]:
                mob = [mm for mm in self.mobs if mm.pos == new_pos][0]
                self.pl.attack(mob)
                if mob.hp <= 0:
                    self.pl.move(new_pos)
            elif move_tile.is_openable:
                self.board[new_pos].opened()
            elif move_tile.is_passable:
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
            elif self.board[new_pos].is_passable:
                mob.move(new_pos)
        if self.pl.hp <= 0:
            raise GameOver()


if __name__ == '__main__':
    screen = Screen()
    board = get_floor()
    pl = Player(board.upstairs.pos.copy())
    mobs = []
    #pl = Player(Position(2, 5))
    #mobs = [Bat(Position(1, 3)),
    #        Zombie(Position(3, 7)),
    #        GreenSlime(Position(1, 7)),
    #        BlueSlime(Position(4, 16))]
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


