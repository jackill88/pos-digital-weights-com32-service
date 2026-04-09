# ensure you have python environment with all the packages installed:
```
pip install -r requirements.txt
pip install -r _win_build\build_requirements.txt
```

# Run this command (having virtualenv or conda env activated) in the root of the project:

```
pyinstaller --onefile --windowed --name "Legacy COM32 Scales service" --icon "icon.ico" --add-data "icon.ico;." --add-data "settings.ini;." win_main.py
```