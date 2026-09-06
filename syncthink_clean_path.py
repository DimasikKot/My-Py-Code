from pathlib import Path
import re

PATTERN = re.compile(r"\.sync-conflict-[^.]+-[^.]+-[^.]+")

count_errors = 0
errors = []

count_created = 0
conflicts = []

SYNC_DIR = Path("C:/Syncthink/")

TEMP_DIR = Path("K:/Desktop/Temp/")
WORK_DIR = Path("C:/Users/DKot/Documents/WORK/")
OBSIDIAN_DIR = Path("K:/Obsidian/")
VUC_DIR = Path("K:/ВУЦ/")
MULTIMC_DIR = Path("K:/MultiMC")
SHAREX_DIR = Path("C:/Users/DKot/Documents/ShareX")

for path in SYNC_DIR.rglob("*"):
    if path.is_file() and PATTERN.search(path.name):
        new_name = PATTERN.sub("", path.name)
        new_path = path.with_name(new_name)

        # защита от перезаписи существующего файла
        if not new_path.exists():
            errors.append(path)
            count_errors += 1
            print(f"{count_errors}.\t ✅ Найден: {path}")
        else:
            conflicts.append(path)
            count_created += 1

count_errors = 0
for path in errors:
    new_name = PATTERN.sub("", path.name)
    new_path = path.with_name(new_name)
    path.rename(new_path)
    count_errors += 1
    print(f"{count_errors}.\t ✅ Переименован: {path} -> {new_path}")

DELETE_DIRS = {
    ".minecraft/config/",
    ".minecraft/xaero/",
    ".minecraft/shaderpacks/"
}  # папки, при наличии которых файл удаляется

count_created = 0
for path in conflicts:
    new_name = PATTERN.sub("", path.name)
    new_path = path.with_name(new_name)
    path_str = str(path).replace("\\", "/")
    count_created += 1

    if any(pattern in path_str for pattern in DELETE_DIRS):
        path.unlink()
        print(f"{count_created}.\t ✅ Удалён (по пути): {path}")
        continue

    print(f"{count_created}.\t ⚠️  Пропущен (уже существует): {path}")

# from pathlib import Path

# ROOT_DIR = Path("k:/Desktop/Temp/")
# CONFLICT_STR = ".sync-conflict-20260705-093310-TIXI47V"

# count = 0

# created = []

# for path in ROOT_DIR.rglob("*"):
#     if path.is_file() and CONFLICT_STR in path.name:
#         new_name = path.name.replace(CONFLICT_STR, "")
#         new_path = path.with_name(new_name)

#         # защита от перезаписи существующего файла
#         if not new_path.exists():
#             path.rename(new_path)
#             count += 1
#             print(f"{count}. ✅ Переименован: {path} -> {new_path}")
#         else:
#             created.append(new_path)

# for path in created:
#     print(f"⚠️ Пропущен (уже существует): {path}")
