import json
import re
import shutil

"""
Преобразует JSON с номерами точек в INI-файл.

С сайта с интерактивной картой: https://genshin-impact-map.appsample.com/
По эндпоинту: https://firestore.googleapis.com/google.firestore.v1.Firestore/Listen/channel?gsessionid=
"""

# Пути к файлам
JSON_FILE = "genshin_web_save.json"
INI_FILE = "d3dx_user.ini"

# 1. Читаем JSON
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Извлекаем номера точек для активации
points_to_activate = {int(item["stringValue"]) for item in data.get("values", [])}
print(f"Активируем точки: {sorted(points_to_activate)}")

# 2. Читаем INI и собираем существующие точки
with open(INI_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

pattern = re.compile(r"^(\$\\adventuremap\\pointdata\\point)(\d+)\s*=\s*(\d+)$")

existing_points = {}  # номер -> строка
other_lines = []

for line in lines:
    match = pattern.match(line.strip())
    if match:
        prefix, number, value = match.groups()
        existing_points[int(number)] = {"prefix": prefix, "value": value, "line": line}
    else:
        other_lines.append(line)

print(f"Существующих точек: {len(existing_points)}")

# 3. Создаем обновленный список всех точек
all_numbers = set(existing_points.keys()) | points_to_activate
sorted_numbers = sorted(all_numbers)

new_point_lines = []
modified = 0
added = 0

for number in sorted_numbers:
    prefix = "$\\adventuremap\\pointdata\\point"
    new_value = "1" if number in points_to_activate else "0"
    new_line = f"{prefix}{number} = {new_value}\n"

    if number in existing_points:
        if new_line != existing_points[number]["line"]:
            modified += 1
    else:
        added += 1

    new_point_lines.append(new_line)

# 4. Сохраняем результат
final_lines = other_lines + new_point_lines

# Создаем резервную копию
shutil.copy2(INI_FILE, "d3dx_user_updated.ini")

# Сохраняем обновленный файл
with open("d3dx_user_updated.ini", "w", encoding="utf-8") as f:
    f.writelines(final_lines)

print(f"\nРезультат:")
print(f"  - Обновлено: {modified}")
print(f"  - Добавлено: {added}")
print(f"  - Всего точек: {len(new_point_lines)}")
print("Готово!")
