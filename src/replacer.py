import yaml
from pathlib import Path
from clipboard import Clip

from rules import Rule, RULES_MAPPING

import logging

logger = logging.getLogger(__name__)


class Replacer:
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
            rule_class = RULES_MAPPING.get(rule_type)
            if not rule_class:
                raise ValueError(f"Unknown rule type: {rule_type}")
            instance: Rule = rule_class(**rule)
            if not instance.enabled:
                logger.warning(f"Rule {instance.name} is disabled and will not be applied.")
                continue
            compiled_rules.append(instance)
            logger.info(f"Loaded rule: {instance.name} ({rule_type})")
            logger.debug(f"Rule details: {instance}")

        return compiled_rules

    def apply_rules(self, clip: Clip) -> str:
        text = clip.value
        for rule in self.rules:
            text = rule.apply(text)
        return Clip(clip.type, text)
