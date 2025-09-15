# min_var_length.py
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
import astroid

class MinVarLengthChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = "min-var-length"
    priority = -1
    msgs = {
        "E9003": (
            "variable name too short",
            "min-var-length",
            "Disallow variable names shorter than 3 chars (except loop vars and 'i')."
        ),
    }

    def visit_assignname(self, node: astroid.AssignName):
        # Skip 'i' and >=3 chars are fine
        if node.name == "i" or len(node.name) >= 3:
            return
        # Skip loop variables
        if isinstance(node.scope(), astroid.For):
            return
        self.add_message("min-var-length", node=node)

def register(linter):
    linter.register_checker(MinVarLengthChecker(linter))
