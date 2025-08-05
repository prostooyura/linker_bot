# states.py
from aiogram.fsm.state import StatesGroup, State

class LinkStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_link = State()

class DeleteStates(StatesGroup):
    waiting_for_index = State()
    
class CategoryStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_choice = State()