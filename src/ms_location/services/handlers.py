from typing import Callable, Dict, List


# Пример обработчика для metric_id = 1
def handler_for_metric_1(attrs: Dict[str, List[str]]) -> Dict[str, str]:

    new_attrs: Dict[str, str] = {}
    for key, values in attrs.items():
        if "Профессия" in key:
            continue
        elif "Валюта" in key:
            # Ищем PPP
            ppp_found = any("PPP" in v for v in values)
            if ppp_found:
                new_attrs[key] = "Международный доллар 2021 года по паритету покупательной способности"
                continue
            
            us_dollars = any("U.S. dollars" in v for v in values)
            if us_dollars:
                new_attrs[key] = "Доллары США"
                continue

            # Удаляем "Местная валюта" и объединяем остальное
            filtered = [v for v in values if v != "Местная валюта"]
            if filtered:
                new_attrs[key] = ", ".join(filtered)
                
            else:
                # Если после удаления ничего не осталось (например, была только "Местная валюта")
                new_attrs[key] = values[0] if values else ""
        else:
            new_attrs[key] = values[0]

    return new_attrs


def handler_for_metric_2(attrs: Dict[str, List[str]]) -> Dict[str, str]:

    new_attrs: Dict[str, str] = {}
    for key, values in attrs.items():
        if "Уровень образования" in key:
            continue
        else:
            new_attrs[key] = values[0]

    return new_attrs

def handler_for_metric_3(attrs: Dict[str, List[str]]) -> Dict[str, str]:

    new_attrs: Dict[str, str] = {}
    for key, values in attrs.items():
        new_attrs[key] = values[0]

    return new_attrs


# Можно собрать словарь, где ключ — metric_id, значение — функция-обработчик
metric_handlers: Dict[int, Callable] = {
    1: handler_for_metric_1,
    2: handler_for_metric_2,
    3: handler_for_metric_3,
}
