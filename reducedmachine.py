#   ReducedMachine - a command-line simulator of the Reduced Machine,
#   a minimised version of the Manchester Mark I, as described by Alan Turing:
#   http://archive.computerhistory.org/resources/text/Knuth_Don_X4100/PDF_index/k-4-pdf/k-4-u2780-Manchester-Mark-I-manual.pdf
#   Copyright (C) 2018 Edward Salkield

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.



import math, argparse, sys
from textwrap import wrap

# Global machine settings
symbols = ['/', 'E', '@', 'A', ':', 'S', 'I', 'U', '8', 'D', 'R',
           'J', 'N', 'F', 'C', 'K', 'T', 'Z', 'L', 'W', 'H', 'Y',
           'P', 'Q', 'O', 'B', 'G', '"', 'M', 'X', 'V', '£']

# The number of bits a symbol represents
symbolvalue = 5

# The number of bits in a line
linesize            = 20
shortlinesize       = 10
max_acc_symbols     = 8

max_acc_size        = math.pow(2, max_acc_symbols * symbolvalue)
max_line_size       = math.pow(2, linesize)
max_short_line_size = math.pow(2, shortlinesize)


# Converts an integer into its symbolic representation of up to size symbols
def int_to_symbols(n, size):
    n = n%(math.pow(2, linesize))

    out = ''
    while n != 0:
        (n, m) = divmod(n, len(symbols))
        out += symbols[int(m)]

    return out.ljust(size, symbols[0])


# Converts a symbolic representation of a number to integer form
def symbols_to_int(sym):
    i = 0
    out = 0
    for s in sym:
        out += symbols.index(s)*math.pow(2, i)
        i += symbolvalue

    return int(out)


# Emulates the electronic store of the Mark I computer
class EStore():
    memory = {} # Maps memory address to contents

    # Loads the memory location on initialisation, if supplied
    def init(self, location=None):
        if location != None:
            self.load(location)


    # Tests if 'val' is correctly formatted data, and has length no greater than 'length'
    def valid(self, val, length):
        correct = len(val) <= length
        if correct:
            for v in val:
                correct = correct and v in symbols
        return correct


    # Sets memory location 'loc' to value 'val', overflowing if 'val' exceeds linesize in length
    def set(self, loc, val):
        assert(self.valid(loc, int(shortlinesize/symbolvalue)))
        assert(self.valid(val, int(linesize/symbolvalue)*2))
        val = wrap(val, int(linesize/symbolvalue))
        loc_int = symbols_to_int(loc)
        for i, v in enumerate(val):
            newloc = int_to_symbols((loc_int + i) % max_short_line_size, int(shortlinesize/symbolvalue))
            self.memory[newloc] = v.ljust(int(linesize/symbolvalue), symbols[0])


    # Gets 'lines' consecutive lines from memory, starting from position 'loc'
    def get(self, loc, lines=1):
        returnstring = True
        if isinstance(loc, int) or isinstance(loc, float):
            returnstring = False    # Return an int instead
            loc_int = int(loc)
            loc = int_to_symbols(loc, int(shortlinesize/symbolvalue))
        else:
            loc_int = symbols_to_int(loc)

        assert(self.valid(loc, int(shortlinesize/symbolvalue)))
        assert(isinstance(lines, int) and lines >= 1)

        output = ''
        for i in range(lines):
            newloc = int_to_symbols((loc_int + i) % max_short_line_size, int(shortlinesize/symbolvalue))

            if newloc not in self.memory.keys():
                self.memory[newloc] = "////"

            output += self.memory[newloc]

        if not returnstring:
            output = symbols_to_int(output)

        return output


    # Load memory contents from a location 'location'
    def load(self, location):
        with open(location, 'r') as memfile:
            for line in memfile:
                if not line.isspace() and line[0] != '#':
                    args = line.split()
                    self.set(args[0], args[1])


    # Dumps the list of all viewed/written lines in memory
    def dump(self):
        return map(lambda x: x[0] + " " + x[1], self.memory.items())



# The complete state of a Reduced Machine
class State():
    A = 0               # Accumulator value (residue modulo 40)
    e_store = EStore()  # Electronic Store
    C = 0               # Instruction number in symbolic representation
    S = 0               # Present instruction in symbolic representation

    def __init__(self, A, e_store, C=max_short_line_size-1, S=0):
        self.A = A
        self.e_store = e_store
        self.C = C
        self.S = S



# The error returned if the ReducedMachine comes across an unrecognised instruction
class InvalidInstructionError(Exception):
    pass



# Defines the functions of the reduced machine
class ReducedMachine():
    def __init__(self, state, verbose=False, quiet=False, memdump=None):
        assert(isinstance(state, State))
        assert(isinstance(verbose, int))

        self.state = state
        self.verbose = verbose
        self.quiet = quiet
        self.memdump = memdump


    # Verbose print
    def printv(self, msg):
        if self.verbose:
            print(msg)


    # Normal print
    def printn(self, msg):
        if not self.verbose and not self.quiet:
            print(msg)


    # Quiet print
    def printq(self, msg):
        if self.quiet():
            print(msg)


    # Fetches the "content of the P.I. line", aka the next instruction
    def I(self):
        # Increment C
        self.state.C = (self.state.C + 1) % max_short_line_size
        self.state.S = self.state.e_store.get(self.state.C)
        return self.state


    # Maps the current state onto the next state, printing using line number 'n'
    def applyInstruction(self, n):
        # Decode instruction and relevant data
        instr     = int_to_symbols(self.state.S, int(linesize/symbolvalue))
        line_pair = instr[:int(shortlinesize/symbolvalue)]
        func_sym  = instr[int(shortlinesize/symbolvalue):]
        s_data = self.state.e_store.get(self.state.S % max_short_line_size)
        s_pair_data = self.state.e_store.get(self.state.S % max_short_line_size, 2)
        
        line_no = int_to_symbols(self.state.C, int(shortlinesize/symbolvalue))

        # Variables for printing purposes
        changed_memory = ''
        acc_symbols = int_to_symbols(self.state.A, max_acc_symbols)

        # The case split representing each instruction in the Reduced Machine
        if func_sym == "/H":    # C' = C+1(mod 2^10) if 2^40 > A > 2^39, else C' = S (mod 2^10)
            if not(math.pow(2, 40) > self.state.A and self.state.A >= math.pow(2, 39)):
                self.state.C = s_data % max_short_line_size

        elif func_sym =="/P":   # C' = S
            self.state.C = s_data % max_short_line_size

        elif func_sym =="/S":   # S' = A
            self.state.S = self.state.A % max_line_size
            self.state.e_store.set(line_pair, acc_symbols)
            changed_memory = line_pair + "   " + acc_symbols

        elif func_sym =="T/":   # A' = S
            self.state.A = s_pair_data % max_acc_size

        elif func_sym =="T:":   # A' = 0
            self.state.A = 0

        elif func_sym =="TI":   # A' = A+S
            self.state.A += s_pair_data % max_acc_size

        elif func_sym =="TN":   # A' = A-S
            self.state.A -= s_pair_data % max_acc_size

        elif func_sym =="TF":   # A' = -S
            raise InvalidInstructionError("TF currently unimplemented")

        elif func_sym =="TK":   # A' = 2S
            self.state.A = (s_pair_data * 2) % max_acc_size
            
        elif func_sym =="T£":   # (no effect)
            pass
        
        else:
            raise InvalidInstructionError("Instruction " + instr + " does not exist!")

        self.printn(str(n).ljust(5) + " " + line_no + "   " + instr + "   " + acc_symbols + "     " + changed_memory )

            
    # Fetches and applies the next instruction
    def next(self, n):
        self.I()
        self.applyInstruction(n)


    # Run Reduced Machine for 'steps' steps or until halting loop detected
    def run(self, steps=-1):
        states_list = []

        self.printn("Step  Addr Instr  Accumulator  Addr ChangedMemory")
        
        n = 0
        while(n < steps or steps == 0):
            if self.memdump != None:
                with open(self.memdump, 'a') as fd:
                    fd.write("Step " + str(n) + '\n')
                    for line in state.e_store.dump():
                        fd.write(line + '\n')
                    fd.write('\n')

            C = self.state.C
            self.next(n)

            if C == self.state.C:
                print("Halting loop detected.")
                break

            n += 1

        print("HALT")


# Argument parsing and initialisation
parser = argparse.ArgumentParser(description="A simulator of Turing's Reduced Machine, based on the Manchester Mark I.\nA description of the computer can be found here:\nhttp://archive.computerhistory.org/resources/text/Knuth_Don_X4100/PDF_index/k-4-pdf/k-4-u2780-Manchester-Mark-I-manual.pdf")
parser.add_argument("codefile", nargs='?', type=str, help="location of a machine code file to be loaded into memory")
parser.add_argument("-v", "--verbose", action='store_true', help="print more detailed information")
parser.add_argument("-q", "--quiet", action='store_true', help="output only memory locations as specified in codefile")
parser.add_argument("--max-steps", type=int, help="number of steps the simulator should terminate after. Defalt 0 (no limit)", default=0)
parser.add_argument("-m", "--memdump", type=str, help="dump memory at each step of the prodecude to MEMDUMP")
parser.add_argument("-l", "--licence", action='store_true', help="display licence")

args = parser.parse_args()

if args.licence:
    print("Copyright (C) 2018 Edward Salkield\nThis program comes with ABSOLUTELY NO WARRANTY.\nThis is free software, and you are welcome to redistribute it\nunder certain conditions. Licenced under GNU GPL v3.")
    sys.exit(0)

if args.verbose and args.quiet:
    print("Error: Can't be both verbose and quiet!")
    sys.exit(1)

if args.codefile == None:
    print("Error: Must supply a codefile!")
    sys.exit(1)

# Load and run Reduced Machine
e_store = EStore()
e_store.load(args.codefile)
state = State(0, e_store)
rm = ReducedMachine(state, verbose=args.verbose, quiet=args.quiet, memdump=args.memdump)
rm.run(args.max_steps)
