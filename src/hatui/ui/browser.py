from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Input, Static

from hatui.ui.catalog import ModuleSpec
from hatui.ui.messages import ActivateObject, SelectionChanged


class ObjectBrowser(Vertical):
    def __init__(self, spec: ModuleSpec, backend: object) -> None:
        super().__init__()
        self.spec = spec
        self.backend = backend
        self.rows: dict[str, object] = {}
        self.selected_key: str | None = None

    def compose(self) -> ComposeResult:
        yield Static(self.spec.title.upper(), id="view-title")
        with Vertical(id="filter-bar"):
            yield Input(placeholder="filter  —  type to search this view", id="filter")
        with Vertical(id="table-wrap"):
            yield DataTable(id="table", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_columns(*[col.label for col in self.spec.columns])
        self.reload()

    def reload(self, query: str | None = None) -> None:
        if query is None:
            query = self.query_one("#filter", Input).value
        table = self.query_one("#table", DataTable)
        table.clear()
        self.rows.clear()
        items = self.spec.loader(self.backend, query)
        for item in items:
            key = str(self.spec.key(item))
            self.rows[key] = item
            cells = [str(c) for c in self.spec.row(item)]
            table.add_row(*cells, key=key)
        self.query_one("#view-title", Static).update(f"{self.spec.title.upper()}   [{len(items)}]")
        if items:
            table.cursor_coordinate = (0, 0)
            self._emit_key(str(self.spec.key(items[0])))

    def _emit_key(self, key: str) -> None:
        obj = self.rows.get(key)
        if obj is None:
            return
        self.selected_key = key
        fields = self.spec.inspect(obj, self.backend)
        self.post_message(SelectionChanged(fields, obj, self.spec.id))

    def selected(self) -> object | None:
        if self.selected_key:
            return self.rows.get(self.selected_key)
        return None

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter":
            self.reload(event.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        key = str(event.row_key.value if hasattr(event.row_key, "value") else event.row_key)
        self._emit_key(key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter or a second click on the highlighted row (double-click) opens actions."""
        event.stop()
        if event.row_key is None:
            return
        key = str(event.row_key.value if hasattr(event.row_key, "value") else event.row_key)
        self._emit_key(key)
        obj = self.rows.get(key)
        if obj is not None:
            self.post_message(ActivateObject(obj, self.spec.id))
