from textual.message import Message


class Navigate(Message):
    def __init__(self, module_id: str) -> None:
        super().__init__()
        self.module_id = module_id


class SelectionChanged(Message):
    def __init__(self, fields: list[tuple[str, str]], obj: object, module_id: str) -> None:
        super().__init__()
        self.fields = fields
        self.obj = obj
        self.module_id = module_id


class ActivateObject(Message):
    """Posted when a row is activated (Enter or double-click)."""

    def __init__(self, obj: object, module_id: str) -> None:
        super().__init__()
        self.obj = obj
        self.module_id = module_id


class StatusPulse(Message):
    pass
