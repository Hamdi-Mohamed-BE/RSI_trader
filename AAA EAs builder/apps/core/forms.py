from typing import Any


class TailwindFormMixin:
    """Apply the shared customer-facing form styles in one place."""

    input_classes = (
        "w-full rounded-lg border border-grid bg-panel px-4 py-3 text-sm text-primary "
        "outline-none transition placeholder:text-muted/60 focus:border-neon-cyan "
        "focus:ring-2 focus:ring-neon-cyan/20"
    )
    checkbox_classes = "size-4 rounded border-grid bg-panel text-neon-cyan focus:ring-neon-cyan/30"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for field in getattr(self, "fields", {}).values():
            widget = field.widget
            css_class = (
                self.checkbox_classes
                if getattr(widget, "input_type", None) == "checkbox"
                else self.input_classes
            )
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()
            if field.help_text:
                widget.attrs.setdefault("aria-describedby", f"help-{field.label}")
