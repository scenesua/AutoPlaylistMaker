import tkinter as tk
import unittest

from ui_state import capture_pages, restore_pages


class ExamplePage:
    def __init__(self, master):
        self.selected_group = 3
        self.name_var = tk.StringVar(master, value="before")
        self.enabled_var = tk.BooleanVar(master, value=True)


class UIStateTests(unittest.TestCase):
    def test_page_variables_survive_reconstruction(self):
        interpreter = tk.Tcl()
        old = ExamplePage(interpreter)
        states = capture_pages([old])
        new = ExamplePage(interpreter)
        new.selected_group = 0
        new.name_var.set("reset")
        new.enabled_var.set(False)
        restore_pages([new], states)
        self.assertEqual(new.selected_group, 3)
        self.assertEqual(new.name_var.get(), "before")
        self.assertTrue(new.enabled_var.get())


if __name__ == "__main__":
    unittest.main()
