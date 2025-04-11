from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from typing import Callable
import importlib

import logging

logger = logging.getLogger(__name__)


@dataclass
class Rule(ABC):
    name: str
    description: str
    enabled: bool

    @abstractmethod
    def apply(self, text: str) -> str:
        """Implemented by subclasses to perform specific replacements."""
        pass


@dataclass
class RegexRule(Rule):
    pattern: str
    replacement: str
    compiled_pattern: re.Pattern = None

    def __post_init__(self):
        self.compiled_pattern = re.compile(self.pattern)

    def apply(self, text: str) -> str:
        return self.compiled_pattern.sub(self.replacement, text)


@dataclass
class ReplaceRule(Rule):
    find: str
    replace: str

    def apply(self, text: str) -> str:
        return text.replace(self.find, self.replace)


@dataclass
class StringMethodRule(Rule):
    method_name: str
    method: Callable = None

    def __post_init__(self):
        self.method = getattr(str, self.method_name, None)
        if not self.method:
            raise ValueError(f"Invalid string method: {self.method_name}")

    def apply(self, text):
        return self.method(text)


@dataclass
class ClassImportRule(Rule):
    module: str
    class_name: str
    init: dict
    method_name: str
    method: Callable = None

    def __post_init__(self):
        module = importlib.import_module(self.module)
        cls = getattr(module, self.class_name)
        if self.init is None:
            # This indicates a class method
            self.method = getattr(cls, self.method_name, None)
        else:
            # Bound method
            init_args = self.init.get("args", [])
            init_kwargs = self.init.get("kwargs", {})
            instance = cls(*init_args, **init_kwargs)
            self.method = getattr(instance, self.method_name, None)
        if not self.method:
            raise ValueError(
                f"Invalid method: {self.method_name} in {self.class_name} of {self.module}"
            )

    def apply(self, text):
        return self.method(text)


@dataclass
class FunctionImportRule(Rule):
    module: str
    function_name: str
    function: Callable = None

    def __post_init__(self):
        module = importlib.import_module(self.module)
        self.function = getattr(module, self.function_name, None)
        if not self.function:
            raise ValueError(f"Invalid function: {self.function_name} in {self.module}")

    def apply(self, text):
        return self.function(text)
    

RULES_MAPPING = {
    "regex": RegexRule,
    "replace": ReplaceRule,
    "str_method": StringMethodRule,
    "class_method": ClassImportRule,
    "function": FunctionImportRule,
}
