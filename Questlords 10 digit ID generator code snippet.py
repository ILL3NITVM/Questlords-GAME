#Questlords 10 digit ID generator code snippet
#PYTHON 2.7.1

import random

def generate_10_digit_number():
    first_digit = random.randint(1, 9)  # avoid leading zero
    rest = ''.join(str(random.randint(0, 9)) for _ in range(9))
    return str(first_digit) + rest

#Loop of the ids - generates a batch of unique IDs (e.g. player/save IDs)
NUMBER_OF_IDS = 10

ids = []
while len(ids) < NUMBER_OF_IDS:
    new_id = generate_10_digit_number()
    if new_id not in ids:  # keep every ID unique
        ids.append(new_id)

for current_id in ids:
    print(current_id)  # e.g. 7175126514
