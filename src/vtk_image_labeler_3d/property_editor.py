from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt


class PropertyEditor(QTreeWidget):
    def __init__(self, obj, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderLabels(["Property", "Value"])
        self.setObject(obj)
        self.itemChanged.connect(self.update_object_value)  # Listen for edits

    def setObject(self, obj):
        """Populate the widget with properties of the given object"""
        self.clear()
        self.obj = obj  # Store reference to the object
        for attr in dir(obj):
            if attr.startswith("__"):  # Skip private/magic attributes
                continue
            value = getattr(obj, attr)
            item = QTreeWidgetItem(self, [attr, str(value)])
            item.setFlags(item.flags() | Qt.ItemIsEditable)  # Allow editing
            item.setData(0, Qt.UserRole, attr)  # Store attribute name

        self.expandAll()  # Expand all items

    def update_object_value(self, item, column):
        """Update the object's attribute when an item is edited"""
        if column == 1:  # Only update value column
            attr_name = item.data(0, Qt.UserRole)  # Retrieve attribute name
            new_value = item.text(1)  # Get new value as string

            # Attempt to convert the value to the appropriate type
            current_value = getattr(self.obj, attr_name)
            try:
                if isinstance(current_value, int):
                    new_value = int(new_value)
                elif isinstance(current_value, float):
                    new_value = float(new_value)
                elif isinstance(current_value, bool):
                    new_value = new_value.lower() in ["true", "1", "yes"]
                # Add more type conversions if needed
            except ValueError:
                return  # Ignore invalid input

            setattr(self.obj, attr_name, new_value)  # Update object


# Example usage
class ExampleObject:
    def __init__(self):
        self.name = "My Object"
        self.value = 42
        self.enabled = True


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    obj = ExampleObject()
    
    main_win = QWidget()
    layout = QVBoxLayout(main_win)

    property_editor = PropertyEditor(obj)
    layout.addWidget(property_editor)

    main_win.show()
    sys.exit(app.exec_())
