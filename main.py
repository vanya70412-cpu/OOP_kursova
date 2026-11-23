import time
from models import (
    ProjectManager,
    Project,
    Employee,
    Task,
    TaskPriority,
    TaskStatus,
    DevelopmentTask,
    BugTask,
    TestingTask,
    TaskStatusTransaction,
)


def show_menu() -> None:
    """Виводить головне інтерактивне меню консольного інтерфейсу (CLI)."""
    print("\n" + "=" * 72)
    print("   СИСТЕМА УПРАВЛІННЯ ЗАВДАННЯМИ ПРОЄКТУ (PROJECT MANAGER CLI v1.0)")
    print("=" * 72)
    print(" 1. Показати всі завдання проєкту та технічний вивід (__str__ / __repr__)")
    print(" 2. Додати завдання на розробку (DevelopmentTask)")
    print(" 3. Додати завдання на виправлення багу (BugTask)")
    print(" 4. Додати завдання на тестування (TestingTask)")
    print(" 5. Пошук за прізвищем виконавця, редагування та математика (__add__)")
    print(" 6. Вивести невиконані завдання за пріоритетом (Ітератор PendingTaskIterator)")
    print(" 7. Фільтрація прострочених або за прізвищем (Генератори yield)")
    print(" 8. Зміна статусу завдання через транзакцію (пошук за прізвищем)")
    print(" 9. Статистика бюджету (Функтор) та експорт звіту (CSV)")
    print("10. Зберегти / Відновити стан (Pickle) або перечитати налаштування (JSON)")
    print(" 0. Безпечний вихід із програми (автозбереження)")
    print("=" * 72)


def choose_priority() -> TaskPriority:
    print("Оберіть пріоритет: 1 - Низький | 2 - Середній | 3 - Високий | 4 - Критичний")
    p_choice = input("Ваш вибір (1-4, Enter=Середній): ").strip()
    mapping = {
        "1": TaskPriority.LOW,
        "2": TaskPriority.MEDIUM,
        "3": TaskPriority.HIGH,
        "4": TaskPriority.CRITICAL,
        "": TaskPriority.MEDIUM,
    }
    if p_choice not in mapping:
        raise ValueError("Некоректний код пріоритету! Доступні значення: 1, 2, 3 або 4.")
    return mapping[p_choice]


def choose_status() -> TaskStatus:
    print("Оберіть цільовий статус: 1 - До виконання | 2 - У роботі | 3 - Виконано")
    s_choice = input("Ваш вибір (1-3): ").strip()
    mapping = {
        "1": TaskStatus.TODO,
        "2": TaskStatus.IN_PROGRESS,
        "3": TaskStatus.DONE,
    }
    if s_choice not in mapping:
        raise ValueError("Некоректний код статусу! Доступні значення: 1, 2 або 3.")
    return mapping[s_choice]


def choose_employee(default_emp: Employee) -> Employee:
    """Дозволяє вказати прізвище виконавця або залишити виконавця за замовчуванням."""
    name = input(f"Виконавець (Прізвище І. Б., Enter={default_emp.full_name}): ").strip()
    if not name or name.lower() == default_emp.full_name.lower():
        return default_emp
    emp_code = f"E-{abs(hash(name)) % 90 + 10}"
    return Employee(emp_code, name, default_emp.role, default_emp.hourly_rate)


def choose_task_by_surname(
    manager: ProjectManager,
    prompt_label: str = "Введіть прізвище виконавця",
) -> Task:
    """
    Зручний UX-пошук завдання за прізвищем виконавця:
    показує підказку доступних виконавців, знаходить усі їхні завдання
    та дає обрати потрібне за порядковим номером без запам'ятовування ID.
    """
    assignees = manager.get_available_assignees()
    if assignees:
        print(f"Доступні виконавці: {', '.join(assignees)}")
    surname = input(f"{prompt_label} (напр. Ісайкін): ").strip()
    matches = manager.find_by_surname(surname)
    if not matches:
        raise KeyError(f"Завдань для виконавця з прізвищем '{surname}' не знайдено!")

    print(f"\nЗнайдено завдань за прізвищем '{surname}': {len(matches)}")
    for idx, t in enumerate(matches, 1):
        print(f"  {idx}. {t}")

    if len(matches) == 1:
        print("Автоматично обрано єдине знайдене завдання.")
        return matches[0]

    raw_num = input(f"Оберіть номер завдання зі списку (1-{len(matches)}): ").strip()
    if not raw_num.isdigit():
        raise ValueError("Номер завдання має бути цілим числом!")
    pos = int(raw_num)
    if not (1 <= pos <= len(matches)):
        raise IndexError(f"Некоректний номер! Оберіть значення від 1 до {len(matches)}.")
    return matches[pos - 1]


def run_cli() -> None:
    """Головна точка входу та життєвий цикл консольного інтерфейсу."""
    manager = ProjectManager()
    manager.load_system_state()

    default_project = Project("PRJ-20", "CRM Cloud Platform v2.0", "Департамент розробки")
    emp_dev = Employee("E-01", "Ісайкін І. М.", "Backend Developer", 650.0)
    emp_qa = Employee("E-02", "Коваленко О. В.", "QA Automation Engineer", 500.0)

    print(f"Ласкаво просимо до Project Task Management System ({manager.config.get('company_name')})")

    while True:
        show_menu()
        try:
            choice = input("Оберіть дію (0-10): ").strip()

            match choice:
                case "1":
                    manager.show_all_tasks()
                    if len(manager) > 0:
                        sub = input("Показати налагоджувальне представлення __repr__? (так/ні): ").strip().lower()
                        if sub == "так":
                            print("\n--- Технічний вивід колекції (__repr__) ---")
                            for i in range(len(manager)):
                                print("  " + repr(manager[i]))

                case "2":
                    print("\n--- ДОДАВАННЯ ЗАВДАННЯ НА РОЗРОБКУ (DevelopmentTask) ---")
                    tid = input("ID завдання (напр. T-101): ").strip()
                    title = input("Назва завдання: ").strip()
                    assignee = choose_employee(emp_dev)
                    hours = float(input("Базовий час розробки (год): ").strip())
                    coeff = float(input("Коефіцієнт складності (>= 1.0, напр. 1.5): ").strip())
                    stack = input("Технологічний стек (Enter=Python/FastAPI): ").strip() or "Python/FastAPI"
                    prio = choose_priority()
                    overdue = input("Чи прострочене завдання? (так/ні, Enter=ні): ").strip().lower() == "так"
                    task = DevelopmentTask(
                        tid, title, default_project, assignee, prio, hours, coeff, stack,
                        TaskStatus.TODO, overdue
                    )
                    manager.add_task(task)

                case "3":
                    print("\n--- ДОДАВАННЯ ЗАВДАННЯ НА ВИПРАВЛЕННЯ БАГУ (BugTask) ---")
                    tid = input("ID багу (напр. B-202): ").strip()
                    title = input("Опис дефекту: ").strip()
                    assignee = choose_employee(emp_dev)
                    hours = float(input("Базовий час усунення (год): ").strip())
                    sev = int(input("Рівень серйозності (1-5): ").strip())
                    env = input("Середовище (Prod/Stage, Enter=Production): ").strip() or "Production"
                    prio = choose_priority()
                    overdue = input("Чи прострочене завдання? (так/ні, Enter=ні): ").strip().lower() == "так"
                    task = BugTask(
                        tid, title, default_project, assignee, prio, hours, sev, env,
                        TaskStatus.IN_PROGRESS, overdue
                    )
                    manager.add_task(task)

                case "4":
                    print("\n--- ДОДАВАННЯ ЗАВДАННЯ НА ТЕСТУВАННЯ (TestingTask) ---")
                    tid = input("ID тестування (напр. Q-303): ").strip()
                    title = input("Назва перевірки: ").strip()
                    assignee = choose_employee(emp_qa)
                    hours = float(input("Базовий час підготовки (год): ").strip())
                    cases = int(input("Кількість тест-кейсів (> 0): ").strip())
                    auto = input("Автоматизоване тестування? (так/ні, Enter=так): ").strip().lower() != "ні"
                    prio = choose_priority()
                    overdue = input("Чи прострочене завдання? (так/ні, Enter=ні): ").strip().lower() == "так"
                    task = TestingTask(
                        tid, title, default_project, assignee, prio, hours, cases, auto,
                        TaskStatus.TODO, overdue
                    )
                    manager.add_task(task)

                case "5":
                    print("\n--- ПОШУК ЗА ПРІЗВИЩЕМ ВИКОНАВЦЯ, РЕДАГУВАННЯ ТА МАТЕМАТИКА (__add__) ---")
                    found_task = choose_task_by_surname(manager)
                    print(f"\nОбрано завдання: {found_task}")
                    print("Дія: 1 - Редагувати | 2 - Додати резерв (+ год) | 3 - Об'єднати 2 задачі (task1 + task2) | 4 - Видалити")
                    act = input("Ваш вибір (1-4): ").strip()
                    if act == "1":
                        new_title = input(f"Нова назва (Enter='{found_task.title}'): ").strip()
                        if new_title:
                            found_task.title = new_title
                        new_h = input(f"Новий базовий час (Enter={found_task.base_hours}): ").strip()
                        if new_h:
                            found_task.base_hours = float(new_h)
                        manager.recalculate_budget()
                        print(f"[Оновлено]: {found_task}")
                    elif act == "2":
                        buf = float(input("Введіть резерв часу для додавання (год): ").strip())
                        buffered_task = found_task + buf
                        print(f"Оригінальне завдання (без змін): {found_task}")
                        print(f"Новий об'єкт із резервом (__add__): {buffered_task}")
                    elif act == "3":
                        second_task = choose_task_by_surname(
                            manager, "Введіть прізвище виконавця другого завдання"
                        )
                        merged_task = found_task + second_task
                        print(f"Об'єднане завдання (__add__): {merged_task}")
                    elif act == "4":
                        removed = manager.remove_task(found_task)
                        print(f"[Видалено] Завдання [{removed.task_id}] '{removed.title}' вилучено зі списку.")
                    else:
                        print("[Warning] Некоректний вибір дії! Оберіть від 1 до 4.")

                case "6":
                    print("\n--- НЕВИКОНАНІ ЗАВДАННЯ ЗА СПАДАННЯМ ПРІОРИТЕТУ (PendingTaskIterator) ---")
                    pending_list = list(manager.get_pending_tasks())
                    if not pending_list:
                        print("  Активних (невиконаних) завдань немає.")
                    else:
                        for idx, pt in enumerate(pending_list, 1):
                            print(f"  {idx}. {pt}")

                case "7":
                    print("\n--- ЛІНИВА ФІЛЬТРАЦІЯ ЧЕРЕЗ ГЕНЕРАТОР (yield) ---")
                    print("1 - Показати лише прострочені завдання | 2 - Показати завдання за прізвищем виконавця")
                    g_sub = input("Ваш вибір (1-2): ").strip()
                    if g_sub == "1":
                        overdue_items = list(manager.generate_overdue_tasks())
                        if not overdue_items:
                            print("  Прострочених завдань не виявлено.")
                        for item in overdue_items:
                            print("  " + str(item))
                    elif g_sub == "2":
                        assignees = manager.get_available_assignees()
                        if assignees:
                            print(f"Доступні виконавці: {', '.join(assignees)}")
                        query = input("Введіть прізвище виконавця: ").strip()
                        assigned_items = list(manager.generate_tasks_by_assignee(query))
                        if not assigned_items:
                            print(f"  Завдань для виконавця з прізвищем '{query}' не знайдено.")
                        for idx, item in enumerate(assigned_items, 1):
                            print(f"  {idx}. {item}")
                    else:
                        print("[Warning] Оберіть 1 або 2.")

                case "8":
                    print("\n--- ТРАНЗАКЦІЙНА ЗМІНА СТАТУСУ (ПОШУК ЗА ПРІЗВИЩЕМ) ---")
                    target_task = choose_task_by_surname(manager, "Введіть прізвище виконавця завдання")
                    new_status = choose_status()
                    print("Режим: 1 - Штатна транзакція | 2 - Тест Time-Out | 3 - Тест помилки з Rollback")
                    mode = input("Оберіть режим (1-3, Enter=1): ").strip() or "1"
                    if mode == "1":
                        with TaskStatusTransaction(target_task, new_status, timeout_sec=2.0, user="Ісайкін І.М."):
                            time.sleep(0.2)
                    elif mode == "2":
                        with TaskStatusTransaction(target_task, new_status, timeout_sec=1.0, user="Ісайкін І.М."):
                            print("   [Імітація тривалої перевірки 1.5 с...]")
                            time.sleep(1.5)
                    elif mode == "3":
                        try:
                            with TaskStatusTransaction(target_task, new_status, timeout_sec=3.0, user="Ісайкін І.М."):
                                raise RuntimeError("Збій доступу до віддаленого репозиторію під час фіксації статусу!")
                        except RuntimeError as r_err:
                            print(f"   [Перехоплено виняток транзакції]: {r_err}")
                    else:
                        print("[Warning] Оберіть режим 1, 2 або 3.")

                case "9":
                    print("\n--- АНАЛІТИКА ФУНКТОРА ТА ЕКСПОРТ ЗВІТУ CSV ---")
                    print(manager.estimator.get_stats())
                    manager.export_csv_report()

                case "10":
                    print("\n--- КЕРУВАННЯ СТАНОМ (PICKLE) ТА НАЛАШТУВАННЯМИ (JSON) ---")
                    print("1 - Зберегти у Pickle | 2 - Відновити з Pickle | 3 - Перечитати config.json")
                    p_sub = input("Ваш вибір (1-3): ").strip()
                    if p_sub == "1":
                        manager.save_system_state()
                    elif p_sub == "2":
                        manager.load_system_state()
                    elif p_sub == "3":
                        manager.load_config()
                    else:
                        print("[Warning] Некоректний вибір! Введіть 1, 2 або 3.")

                case "0":
                    print("\nЗавершення роботи. Автоматичне збереження стану системи...")
                    manager.save_system_state()
                    print("Роботу успішно завершено. До побачення!")
                    break

                case _:
                    print(f"[Warning] Невідома команда '{choice}'! Будь ласка, оберіть пункт від 0 до 10.")

        except (KeyboardInterrupt, EOFError):
            print("\nПереривання сеансу. Автоматичне збереження стану...")
            manager.save_system_state()
            break
        except (ValueError, TypeError, KeyError, IndexError) as err:
            print(f"[Помилка валідації або пошуку даних]: {err}")
            print("Система продовжує роботу. Перевірте вхідні дані та спробуйте ще раз.")
        except Exception as err:
            print(f"[Критична помилка інтерфейсу]: {err}")


if __name__ == "__main__":
    run_cli()
