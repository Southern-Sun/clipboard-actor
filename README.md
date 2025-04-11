# clipboard-actor
Windows utility for taking actions when the clipboard is modified

## Config
Create a rules.yaml file at the path `~/.clipboard-actor/rules.yaml`
An example file can be found under `examples/rules.yaml`

This file is used to configure the rules that will be applied when an object is copied onto the
clipboard. Currently, the `main.py` script is configured only to act on text data -- images and file
clips will be ignored. This can be change by editing the callbacks within `main.py`.

The rules file accepts five rule types (as defined in `rules.py`):
- `regex` for applying `re.sub`
- `replace` for applying `str.replace`
- `str_method` for applying any single argument `str` class method
- `class_method` for instantiating and running any class and one of its methods
- `function` for applying any function

`class_method` and `function` are imported dynamically at runtime based on the module path given.


## Usage
Run with `python src/main.py`

The script will listen to Windows events and trigger your configured rules 
