class TableSettings:
    NICK = 'Ник'
    TAG = 'тэг тг'
    SHEET_1 = 'феникс'
    SHEET_2 = 'слеза'
    EVOS = [0, 1, 2, 3, 4, 5]


class CallbackData:
    def __init__(self, fl=None, character=None, evo=None):
        self.fl = fl
        self.character = character
        self.evo = evo

    def encode(self):
        parts = [str(value) for value in self.__dict__.values() if value is not None]
        return '_'.join(parts) if len(parts) > 1 else parts[0]

    @staticmethod
    def decode(callback_data: str):
        if '_' in callback_data:
            parts = callback_data.split("_")
            fl = parts[0]
            character = parts[1]
            evo = parts[2] if len(parts) == 3 else None
            return CallbackData(fl=fl, character=character, evo=evo)
        else:
            return CallbackData(character=callback_data)
