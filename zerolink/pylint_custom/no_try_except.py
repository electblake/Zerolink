# no_try_except.py
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

class NoTryExceptChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = "no-try-except"
    priority = -1
    msgs = {
        "E9001": ("try/except blocks are not allowed", "no-try-except", "Disallow try/except usage."),
    }

    def visit_tryexcept(self, node):
        self.add_message("no-try-except", node=node)

def register(linter):
    linter.register_checker(NoTryExceptChecker(linter))
