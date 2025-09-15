# no_var_rename.py
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
import astroid

class NoVarRenameChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = "no-var-rename"
    priority = -1
    msgs = {
        "E9002": (
            "variable renaming assignment detected",
            "no-var-rename",
            "Disallow foo = bar style variable renaming."
        ),
    }

    def visit_assign(self, node: astroid.Assign):
        if len(node.targets) == 1 and isinstance(node.targets[0], astroid.AssignName):
            if isinstance(node.value, astroid.Name):
                self.add_message("no-var-rename", node=node)

def register(linter):
    linter.register_checker(NoVarRenameChecker(linter))
