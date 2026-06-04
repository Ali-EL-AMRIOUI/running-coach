import re

# Lire le fichier actuel
with open('api/plans.py', 'r') as f:
    content = f.read()

# Remplacer la classe WorkoutSession
old_class = '''class WorkoutSession(BaseModel):
    day: int
    type: str
    km: float
    pace: str = "5:30"
    details: str = ""'''

new_class = '''class WorkoutSession(BaseModel):
    day: Union[int, str]
    type: str
    km: float
    pace: str = "5:30"
    details: str = ""

    @field_validator('day', mode='before')
    @classmethod
    def convert_day(cls, v):
        day_map = {
            'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4,
            'friday': 5, 'saturday': 6, 'sunday': 7,
            'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4,
            'Friday': 5, 'Saturday': 6, 'Sunday': 7
        }
        if isinstance(v, str):
            return day_map.get(v, v)
        return v'''

content = content.replace(old_class, new_class)

# Ajouter l'import Union si nécessaire
if 'from typing import Union' not in content:
    content = content.replace('from typing import List', 'from typing import List, Union')

with open('api/plans.py', 'w') as f:
    f.write(content)

print("✅ Schéma mis à jour")
