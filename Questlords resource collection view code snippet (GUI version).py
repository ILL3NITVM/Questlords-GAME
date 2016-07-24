#Questlords resource collection view code snippet (GUI version)
#PYTHON 2.7.1

from Tkinter import *
root = Tk()
root.title('Questlords')

import time

wood = 0
stone = 0
water = 0
iron = 0
food = 0
elixir = 0

while True:

    Label(root, text= 'Wood = ' + str(int(wood))).grid(row=1, sticky=W)
    Label(root, text='Stone = ' + str(int(stone))).grid(row=2, sticky=W)
    Label(root, text='Water = ' + str(int(water))).grid(row=3, sticky=W)
    Label(root, text='Iron = ' + str(int(iron))).grid(row=4, sticky=W)
    Label(root, text='Food = ' + str(int(food))).grid(row=5, sticky=W)
    Label(root, text='Elixir = ' + str(int(elixir))).grid(row=6, sticky=W)

    wood += 1.1
    stone += 0.7
    water += 0.9
    iron += 0.5
    food += 0.8
    elixir += 0.4
    time.sleep(0.7)

    #print('Wood = ' + str(int(wood)) + ' Stone = ' + str(int(stone)) + ' Water = ' + str(int(water)) + ' Iron = ' + str(int(iron)) + ' Food = ' + str(int(food)) + ' Elixir = ' + str(int(elixir)))
    root.update()




