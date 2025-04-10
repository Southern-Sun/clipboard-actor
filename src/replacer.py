from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
import yaml
from pathlib import Path
from typing import Callable
from clipboard import Clip

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


class Replacer:
    RULES = {
        "regex": RegexRule,
        "replace": ReplaceRule,
        "str_method": StringMethodRule,
    }

    def __init__(self, rules_path: str | Path = None):
        rules_path = Path(rules_path or "~/.clipboard-actor/rules.yaml")
        rules_path = rules_path.expanduser()
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        self._rules_path = rules_path
        self._rules = self.load_rules()

    @property
    def rules(self) -> list[Rule]:
        return self._rules
    
    @rules.setter
    def rules(self, rules: list[Rule]):
        self._rules = rules

    def load_rules(self):
        with open(self._rules_path, "r", encoding="utf-8") as f:
            rules: list[dict] = yaml.safe_load(f)
        compiled_rules = []
        for rule in rules:
            rule_type = rule.pop("type")
            rule_class = Replacer.RULES.get(rule_type)
            if not rule_class:
                raise ValueError(f"Unknown rule type: {rule_type}")
            compiled_rules.append(rule_class(**rule))

        return compiled_rules
    
    def apply_rules(self, clip: Clip) -> str:
        text = clip.value
        for rule in self.rules:
            if not rule.enabled:
                continue
            text = rule.apply(text)
        return Clip(clip.type, text)

