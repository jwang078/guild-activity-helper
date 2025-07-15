# guild-activity-helper

First, fill out the files in the `data` folder according to the pushed template.

Then, to start from scratch, run:

```
python activity_tracker.py
```

If you want to use a saved log file instead of re-downloading from discord API, use:

```
python activity_tracker.py --log_file logs/name_of_log_file.txt
```

The activity tracker produces `output/active_igns.txt`. Then, you can update discord roles with:

```
python update_active_roles.py
```