#Questlords resource collection view code snippet (command line version)
#PYTHON 2.7.1

import time

wood = 0
stone = 0
water = 0
iron = 0
food = 0
elixir = 0

while True:

    wood += 1.1
    stone += 0.7
    water += 0.9
    iron += 0.5
    food += 0.8
    elixir += 0.4
    time.sleep(0.7)

    print('Wood = ' + str(int(wood)) + ' Stone = ' + str(int(stone)) + ' Water = ' + str(
        int(water)) + ' Iron = ' + str(int(iron)) + ' Food = ' + str(int(food)) + ' Elixir = ' + str(
        int(elixir)))



