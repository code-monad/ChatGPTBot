import csv
from pathlib import Path


class GPTMemory:
    def __init__(self, name, coversation_id, parent_id):
        self.name = name
        self.conversation_id = coversation_id
        self.parent_id = parent_id


def LoadMemoryFromRow(csv_row) -> GPTMemory:
    return GPTMemory(csv_row[0], csv_row[1], csv_row[2])


def LoadMemories(filename):
    memories = {}
    path = Path(filename)
    if path.is_file():
        with open(path, mode='r') as f:
            reader = csv.reader(f, delimiter=',')
            for row in reader:
                memories[row[0]] = LoadMemoryFromRow(row)
    else:
        path.touch()
    return memories
