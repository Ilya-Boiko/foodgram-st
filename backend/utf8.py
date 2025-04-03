import json

# Загрузите данные из вашего файла
with open('ingredients.json', 'r', encoding='utf-8') as f:
    ingredients = json.load(f)

# Преобразуйте данные в нужный формат
formatted_data = []
for i, ingredient in enumerate(ingredients):
    formatted_data.append({
        "model": "ingredients.ingredient",
        "pk": i + 1,
        "fields": {
            "name": ingredient["name"],
            "measurement_unit": ingredient["measurement_unit"]
        }
    })

# Сохраните преобразованные данные в новый файл
with open('ingredients_formatted.json', 'w', encoding='utf-8') as f:
    json.dump(formatted_data, f, ensure_ascii=False, indent=4)
