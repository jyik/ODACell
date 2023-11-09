from statemachine import State, StateMachine
import polars as pl

class CrimperState(StateMachine):
    state_idle = State('Idle', initial=True)
    state_crimping = State('Crimping')

    start_crimp = state_idle.to(state_crimping)
    finish_crimp = state_crimping.to(state_idle)

    def before_start_crimp(self):
        print("Crimping starting...")
    def before_finish_crimp(self):
        print("Crimping finished.")

class Stack_id(StateMachine):
    stack0 = State('0', value=0, initial=True)
    stack1 = State('1', value=1)
    stack_list = [stack0, stack1]

    to_stack0 = stack0.from_(*stack_list)
    to_stack1 = stack1.from_(*stack_list)

    cycle = stack0.to(stack1) | stack1.to(stack0)

    #def on_enter_stack0(self):
    #    print("Currently using Stack 0")
    #def on_enter_stack1(self):
    #    print("Currently using Stack 1")

class Tray_id(StateMachine):
    tray_num1 = State('1', value=1)
    tray_num2 = State('2', value=2)
    tray_num3 = State('3', value=3)
    tray_num4 = State('4', value=4)
    tray_num5 = State('5', value=5)
    tray_num6 = State('6', value=6)
    tray_num7 = State('7', value=7)
    tray_num8 = State('8', value=8)
    tray_num9 = State('9', value=9)
    tray_num10 = State('10', value=10, initial=True)

    remove_one = tray_num10.to(tray_num9) | tray_num9.to(tray_num8) | tray_num8.to(tray_num7) | tray_num7.to(tray_num6) | tray_num6.to(tray_num5) | tray_num5.to(tray_num4) | tray_num4.to(tray_num3) | tray_num3.to(tray_num2) | tray_num2.to(tray_num1) | tray_num1.to(tray_num10)

    def before_remove_one(self, event: str, source: State, target: State, message: str = ""):
        message = ". " + message if message else ""
        return f"Loading active site. {target.value} trays remaining {message}"
    def set_state(self, num_trays):
        cycling = True
        while cycling:
            if num_trays == self.current_state_value:
                break
            self.send('remove_one')

class Row_id(StateMachine):
    row1 = State('1', value=1, initial=True)
    row2 = State('2', value=2)
    row3 = State('3', value=3)
    row4 = State('4', value=4)

    change_row = row1.to(row2) | row2.to(row3) | row3.to(row4) | row4.to(row1)

    def set_row(self, row_id):
        cycling = True
        while cycling:
            if row_id == self.current_state_value:
                break
            self.send('change_row')

class ComponentHolderState(StateMachine):
    has_empty = State('Empty', value=0, initial=True)
    has_pccs = State('Contains positive casing, cathode, and separator', value=1)
    has_electrolyte = State('Contains positive casing, cathode, separator, and electrolyte', value=2)
    has_asnc = State('Contains all components', value=3)
    has_crimped = State('Contains closed coin cell', value=4)

    collect = has_empty.to(has_pccs) | has_pccs.to(has_electrolyte) | has_electrolyte.to(has_asnc) | has_asnc.to(has_crimped) | has_crimped.to(has_empty)

class CyclingStation(StateMachine):
    not_full = State('Has empty channel(s)', value=1, initial=True)
    full = State('No empty channels available', value=0)

    cycle = not_full.to(full) | full.to(not_full)

class Trackables:
    def __init__(self):
        self.crimper_state = CrimperState()
        self.stackID = Stack_id()
        self.numTrays = Tray_id()
        self.rowID = Row_id()
        self.componentholder = ComponentHolderState()
        self.CyclingState = CyclingStation()
        self.small_pipette_int = 0 #next pipette tip to take
        self.large_pipette_int = 0 #next pipette tip to take
        self.wellIndex_int = 0 #next free well to use
        self.electrolyte_vol_int = 45
        self.working_area_loaded_int = 0

    def write_to_file(self):
        df = pl.DataFrame({key:value.current_state_value for key, value in self.__dict__.items() if not key.startswith('__') and not callable(key) and not key.endswith('_int')})
        df.hstack(pl.DataFrame({key:value for key, value in self.__dict__.items() if key.endswith('_int') and not callable(key)})).write_parquet('track_objs.parquet')
    
    def load(self):
        exclusion_list = ['crimper_state', 'CyclingState']
        df = pl.read_parquet('track_objs.parquet')
        for var_name in df.select(pl.exclude(exclusion_list)).columns:
            if var_name.endswith('_int'):
                if vars(self)[var_name] == df[var_name][0]:
                    pass
                else:
                    vars(self)[var_name] = df[var_name][0]
            else:
                if vars(self)[var_name].current_state_value == df[var_name][0]:
                    pass
                else:
                    if var_name == 'stackID':
                        self.stackID = Stack_id(start_value=df[var_name][0])
                    elif var_name == 'numTrays':
                        self.numTrays = Tray_id(start_value=df[var_name][0])
                    elif var_name == 'rowID':
                        self.rowID = Row_id(start_value=df[var_name][0])
                    elif var_name == 'componentholder':
                        self.componentholder = ComponentHolderState(start_value=df[var_name][0])
                    
    def to_pl(self):
        df = pl.DataFrame({key:value.current_state_value for key, value in self.__dict__.items() if not key.startswith('__') and not callable(key) and not key.endswith('_int')})
        return df.hstack(pl.DataFrame({key:value for key, value in self.__dict__.items() if key.endswith('_int') and not callable(key)}))