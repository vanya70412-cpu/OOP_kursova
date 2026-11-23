from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import time
import uuid
import pickle
import csv
import json
import os
import logging


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_path(filename: str) -> str:
    """Повертає абсолютний шлях відносно папки програми, якщо шлях відносний."""
    return filename if os.path.isabs(filename) else os.path.join(BASE_DIR, filename)


logging.basicConfig(
    filename=resolve_path("history.log"),
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)


class TaskPriority(Enum):
    """Перелічуваний тип для суворої типізації рівнів пріоритету завдань."""
    LOW = (1, "Низький")
    MEDIUM = (2, "Середній")
    HIGH = (3, "Високий")
    CRITICAL = (4, "Критичний")

    def __init__(self, level: int, label: str):
        self.level = level
        self.label = label


class TaskStatus(Enum):
    """Перелічуваний тип для фіксації життєвого циклу завдання."""
    TODO = "До виконання"
    IN_PROGRESS = "У роботі"
    DONE = "Виконано"
    EXPIRED = "Прострочено"


@dataclass
class Employee:
    """Дата-клас для зберігання інформації про виконавця завдання."""
    emp_id: str
    full_name: str
    role: str
    hourly_rate: float = 500.0


@dataclass
class Project:
    """Дата-клас для зберігання паспортних даних програмного проєкту."""
    code: str
    title: str
    department: str = "Департамент розробки"


class Task:
    """Базовий клас завдання програмного проєкту з інкапсуляцією та магічними методами."""

    def __init__(
        self,
        task_id: str,
        title: str,
        project: Project,
        assignee: Employee,
        priority: TaskPriority,
        base_hours: float,
        status: TaskStatus = TaskStatus.TODO,
        is_overdue: bool = False,
    ):
        self._task_id = None
        self._title = None
        self._base_hours = 0.0
        self._priority = None
        self._status = None

        self.task_id = task_id if task_id else f"T-{str(uuid.uuid4())[:4].upper()}"
        self.title = title
        self.project = project
        self.assignee = assignee
        self.priority = priority
        self.base_hours = base_hours
        self.status = status
        self.is_overdue = bool(is_overdue)
        self.created_at = datetime.now()

    @property
    def task_id(self) -> str:
        return self._task_id

    @task_id.setter
    def task_id(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Ідентифікатор завдання (ID) не може бути порожнім!")
        self._task_id = value.strip()

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Назва завдання повинна бути текстовим рядком!")
        if not value.strip():
            raise ValueError("Назва завдання не може бути порожнім рядком!")
        self._title = value.strip()

    @property
    def base_hours(self) -> float:
        return self._base_hours

    @base_hours.setter
    def base_hours(self, value: float) -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("Базова оцінка часу повинна бути числом!")
        if float(value) <= 0:
            raise ValueError("Базова оцінка часу має бути строго більшою за 0 годин!")
        self._base_hours = float(value)

    @property
    def priority(self) -> TaskPriority:
        return self._priority

    @priority.setter
    def priority(self, value: TaskPriority) -> None:
        if not isinstance(value, TaskPriority):
            raise ValueError("Пріоритет має бути екземпляром перелічення TaskPriority!")
        self._priority = value

    @property
    def status(self) -> TaskStatus:
        return self._status

    @status.setter
    def status(self, value: TaskStatus) -> None:
        if not isinstance(value, TaskStatus):
            raise ValueError("Статус має бути екземпляром перелічення TaskStatus!")
        self._status = value

    def estimate_hours(self) -> float:
        """Базовий поліморфний метод оцінки трудовитрат у годинах."""
        return round(self._base_hours, 2)

    def get_task_category(self) -> str:
        return "Загальне завдання"

    def get_info(self) -> str:
        overdue_mark = " [ПРОСТРОЧЕНО]" if (self.is_overdue or self.status == TaskStatus.EXPIRED) else ""
        return (
            f"[{self._task_id}] ({self.get_task_category()}) '{self._title}' | "
            f"Проєкт: {self.project.code} | Виконавець: {self.assignee.full_name} | "
            f"Пріоритет: {self.priority.label} | Статус: {self.status.value} | "
            f"Оцінка: {self.estimate_hours()} год{overdue_mark}"
        )

    def __str__(self) -> str:
        return self.get_info()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(task_id='{self._task_id}', title='{self._title}', "
            f"priority=TaskPriority.{self.priority.name}, status=TaskStatus.{self.status.name}, "
            f"hours={self.estimate_hours()})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return False
        return (
            self.priority.level == other.priority.level
            and self.estimate_hours() == other.estimate_hours()
        )

    def __lt__(self, other: "Task") -> bool:
        """Порівняння завдань за рівнем пріоритету, а за рівності — за тривалістю."""
        if not isinstance(other, Task):
            raise TypeError("Порівнювати можна лише об'єкти класу Task!")
        if self.priority.level != other.priority.level:
            return self.priority.level < other.priority.level
        return self.estimate_hours() < other.estimate_hours()

    def __add__(self, other: "Task | int | float") -> "Task":
        """Математика бізнесу: додавання буферного часу або об'єднання двох завдань."""
        if isinstance(other, (int, float)) and not isinstance(other, bool):
            if other < 0:
                raise ValueError("Додатковий резерв часу не може бути від'ємним!")
            new_task = deepcopy(self)
            new_task.base_hours = self.base_hours + float(other)
            return new_task
        if isinstance(other, Task):
            max_prio = self.priority if self.priority.level >= other.priority.level else other.priority
            total_hours = self.estimate_hours() + other.estimate_hours()
            combined_id = f"{self.task_id}+{other.task_id}"
            combined_title = f"{self.title} + {other.title}"
            return Task(
                task_id=combined_id,
                title=combined_title,
                project=self.project,
                assignee=self.assignee,
                priority=max_prio,
                base_hours=total_hours,
                status=TaskStatus.TODO,
                is_overdue=(self.is_overdue or other.is_overdue),
            )
        raise TypeError("До завдання можна додавати лише інше завдання (Task) або число годин!")


class DevelopmentTask(Task):
    """Клас-нащадок: завдання на розробку нової функціональності."""

    def __init__(
        self,
        task_id: str,
        title: str,
        project: Project,
        assignee: Employee,
        priority: TaskPriority,
        base_hours: float,
        complexity_coeff: float,
        tech_stack: str = "Python/FastAPI",
        status: TaskStatus = TaskStatus.TODO,
        is_overdue: bool = False,
    ):
        super().__init__(task_id, title, project, assignee, priority, base_hours, status, is_overdue)
        self.complexity_coeff = complexity_coeff
        self.tech_stack = tech_stack.strip() if tech_stack else "Python"

    @property
    def complexity_coeff(self) -> float:
        return self._complexity_coeff

    @complexity_coeff.setter
    def complexity_coeff(self, value: float) -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("Коефіцієнт складності має бути числом!")
        if float(value) < 1.0:
            raise ValueError("Коефіцієнт складності розробки не може бути меншим за 1.0!")
        self._complexity_coeff = float(value)

    def estimate_hours(self) -> float:
        return round(self.base_hours * self._complexity_coeff, 2)

    def get_task_category(self) -> str:
        return f"Розробка ({self.tech_stack})"


class BugTask(Task):
    """Клас-нащадок: завдання на виправлення програмного дефекту (багу)."""

    def __init__(
        self,
        task_id: str,
        title: str,
        project: Project,
        assignee: Employee,
        priority: TaskPriority,
        base_hours: float,
        severity_level: int,
        environment: str = "Production",
        status: TaskStatus = TaskStatus.TODO,
        is_overdue: bool = False,
    ):
        super().__init__(task_id, title, project, assignee, priority, base_hours, status, is_overdue)
        self.severity_level = severity_level
        self.environment = environment.strip() if environment else "Production"

    @property
    def severity_level(self) -> int:
        return self._severity_level

    @severity_level.setter
    def severity_level(self, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("Рівень серйозності багу має бути цілим числом!")
        if not (1 <= value <= 5):
            raise ValueError("Рівень серйозності багу має бути в діапазоні від 1 до 5!")
        self._severity_level = value

    def estimate_hours(self) -> float:
        return round(self.base_hours + (self._severity_level * 1.5), 2)

    def get_task_category(self) -> str:
        return f"Виправлення багу (Sev-{self._severity_level})"


class TestingTask(Task):
    """Клас-нащадок: завдання на перевірку якості та тестування (QA)."""

    def __init__(
        self,
        task_id: str,
        title: str,
        project: Project,
        assignee: Employee,
        priority: TaskPriority,
        base_hours: float,
        test_cases_count: int,
        is_automated: bool = True,
        status: TaskStatus = TaskStatus.TODO,
        is_overdue: bool = False,
    ):
        super().__init__(task_id, title, project, assignee, priority, base_hours, status, is_overdue)
        self.test_cases_count = test_cases_count
        self.is_automated = bool(is_automated)

    @property
    def test_cases_count(self) -> int:
        return self._test_cases_count

    @test_cases_count.setter
    def test_cases_count(self, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("Кількість тест-кейсів має бути цілим числом!")
        if value <= 0:
            raise ValueError("Кількість тест-кейсів має бути строго більшою за 0!")
        self._test_cases_count = value

    def estimate_hours(self) -> float:
        factor = 0.15 if self.is_automated else 0.35
        return round(self.base_hours + (self._test_cases_count * factor), 2)

    def get_task_category(self) -> str:
        mode = "Auto" if self.is_automated else "Manual"
        return f"Тестування QA ({mode})"


class TaskCostEstimator:
    """Клас-функтор зі збереженням стану для розрахунку вартості та аудиту бюджету."""

    def __init__(self, default_rate: float = 500.0):
        self.default_rate = float(default_rate)
        self.calls_count = 0
        self.total_estimated_cost = 0.0
        self.history: list[str] = []

    def __call__(self, task: Task) -> float:
        self.calls_count += 1
        multipliers = {
            TaskPriority.LOW: 1.0,
            TaskPriority.MEDIUM: 1.2,
            TaskPriority.HIGH: 1.5,
            TaskPriority.CRITICAL: 2.0,
        }
        weight = multipliers.get(task.priority, 1.0)
        rate = task.assignee.hourly_rate if task.assignee else self.default_rate
        hours = task.estimate_hours()
        cost = round(hours * rate * weight, 2)
        self.total_estimated_cost = round(self.total_estimated_cost + cost, 2)
        record = (
            f"Виклик #{self.calls_count}: [{task.task_id}] '{task.title}' "
            f"({hours} год * {rate} грн * x{weight}) -> {cost} грн"
        )
        self.history.append(record)
        return cost

    def get_stats(self) -> str:
        lines = [
            f"Кількість оцінених завдань (викликів функтора): {self.calls_count}",
            f"Накопичений розрахунковий бюджет проєкту: {self.total_estimated_cost} грн",
            "Журнал фінансових розрахунків:",
        ]
        if not self.history:
            lines.append("  (Журнал порожній)")
        for item in self.history:
            lines.append(f"  - {item}")
        return "\n".join(lines)


class PendingTaskIterator:
    """Власний ітератор для обходу лише невиконаних завдань за спаданням пріоритету."""

    def __init__(self, tasks: list[Task]):
        active = [t for t in tasks if t.status != TaskStatus.DONE]
        self._sorted_tasks = sorted(active, reverse=True)
        self.index = 0

    def __iter__(self) -> "PendingTaskIterator":
        return self

    def __next__(self) -> Task:
        if self.index < len(self._sorted_tasks):
            current_task = self._sorted_tasks[self.index]
            self.index += 1
            return current_task
        raise StopIteration


class TaskStatusTransaction:
    """Контекстний менеджер для безпечної зміни статусу завдання з контролем Time-Out і Rollback."""

    def __init__(self, task: Task, target_status: TaskStatus, timeout_sec: float = 2.0, user: str = "operator"):
        self.task = task
        self.target_status = target_status
        self.timeout_sec = timeout_sec
        self.user = user
        self.previous_status = task.status
        self.start_time = 0.0

    def __enter__(self) -> Task:
        self.previous_status = self.task.status
        self.start_time = time.time()
        print(f"-> [ENTER] Початок транзакції для [{self.task.task_id}] '{self.task.title}'.")
        print(f"   Попередній статус: '{self.previous_status.value}'. Ліміт часу: {self.timeout_sec} с.")
        self.task.status = TaskStatus.IN_PROGRESS
        return self.task

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        elapsed = round(time.time() - self.start_time, 2)
        if exc_type is not None:
            self.task.status = self.previous_status
            logging.error(
                f"[ROLLBACK] user='{self.user}' | task='{self.task.task_id}' | error='{exc_val}' | "
                f"відновлено статус '{self.previous_status.value}'"
            )
            print(f"<- [EXIT | ПОМИЛКА] Збій: {exc_val} Відкат (Rollback) до '{self.task.status.value}'.")
            return False

        if elapsed > self.timeout_sec:
            self.task.status = TaskStatus.EXPIRED
            self.task.is_overdue = True
            logging.warning(
                f"[TIME-OUT] user='{self.user}' | task='{self.task.task_id}' | elapsed={elapsed}s > {self.timeout_sec}s"
            )
            print(f"<- [EXIT | TIME-OUT] Час ({elapsed} с) перевищив ліміт ({self.timeout_sec} с)!")
            print(f"   Статус автоматично переведено у: '{self.task.status.value}'.")
        else:
            self.task.status = self.target_status
            logging.info(
                f"[STATUS_CHANGE] user='{self.user}' | task='{self.task.task_id}' | "
                f"'{self.previous_status.value}' -> '{self.target_status.value}' ({elapsed}s)"
            )
            print(f"<- [EXIT | УСПІХ] Транзакція виконана за {elapsed} с. Новий статус: '{self.task.status.value}'.")
        return False


class ProjectManager:
    """Клас-менеджер для управління колекцією завдань проєкту, аналітикою та файловою системою."""

    def __init__(self, config_path: str = "config.json"):
        self._tasks: list[Task] = []
        self.config_path = resolve_path(config_path)
        self.config = {
            "company_name": "SoftLine Ukraine",
            "max_hours_limit": 80.0,
            "default_hourly_rate": 500.0,
            "backup_file": "project_state.pkl",
            "report_file": "project_report.csv",
            "csv_delimiter": ";"
        }
        self.estimator = TaskCostEstimator(default_rate=500.0)
        self.load_config(self.config_path)

    def load_config(self, filepath: str | None = None) -> None:
        target = resolve_path(filepath or self.config_path)
        if not os.path.exists(target):
            self.save_config(target)
            print(f"[JSON] Створено базовий файл налаштувань '{os.path.basename(target)}'.")
        else:
            try:
                with open(target, "r", encoding="utf-8") as file:
                    loaded_data = json.load(file)
                    self.config.update(loaded_data)
                print(
                    f"[JSON] Налаштування завантажено: компанія='{self.config['company_name']}', "
                    f"ліміт трудомісткості={self.config['max_hours_limit']} год."
                )
            except (json.JSONDecodeError, OSError) as err:
                print(f"[Помилка JSON] Не вдалося прочитати '{target}': {err}")
        self.recalculate_budget()

    def save_config(self, filepath: str | None = None) -> None:
        target = resolve_path(filepath or self.config_path)
        with open(target, "w", encoding="utf-8") as file:
            json.dump(self.config, file, ensure_ascii=False, indent=4)

    def recalculate_budget(self) -> None:
        """Синхронізує стан функтора бюджету після редагування, видалення або перечитування конфігурації."""
        self.estimator = TaskCostEstimator(
            default_rate=float(self.config.get("default_hourly_rate", 500.0))
        )
        for task in self._tasks:
            self.estimator(task)

    def add_task(self, task: Task) -> float:
        max_limit = float(self.config.get("max_hours_limit", 80.0))
        calc_hours = task.estimate_hours()
        if calc_hours > max_limit:
            raise ValueError(
                f"Оцінка часу ({calc_hours} год) перевищує ліміт з config.json ({max_limit} год)!"
            )
        for existing in self._tasks:
            if existing.task_id.lower() == task.task_id.lower():
                raise ValueError(f"Завдання з ID '{task.task_id}' вже існує у системі!")
        self._tasks.append(task)
        cost = self.estimator(task)
        logging.info(f"[ADD_TASK] id='{task.task_id}' | title='{task.title}' | hours={calc_hours} | cost={cost}")
        print(f"[Успіх] Додано: {task.get_info()} | Оціночна вартість: {cost} грн")
        return cost

    def remove_task(self, key: "Task | str | int") -> Task:
        target = key if isinstance(key, Task) else self[key]
        if target not in self._tasks:
            raise KeyError(f"Завдання '{target.title}' відсутнє у колекції!")
        self._tasks.remove(target)
        self.recalculate_budget()
        logging.info(f"[REMOVE_TASK] id='{target.task_id}' | title='{target.title}'")
        return target

    def find_by_surname(self, surname: str) -> list[Task]:
        """Пошук усіх завдань за прізвищем виконавця (без урахування регістру)."""
        query = surname.strip().lower()
        if not query:
            raise ValueError("Прізвище виконавця для пошуку не може бути порожнім!")
        return [t for t in self._tasks if query in t.assignee.full_name.lower()]

    def get_available_assignees(self) -> list[str]:
        """Повертає унікальний список виконавців, закріплених за завданнями."""
        seen = []
        for t in self._tasks:
            name = t.assignee.full_name
            if name not in seen:
                seen.append(name)
        return seen

    def __len__(self) -> int:
        return len(self._tasks)

    def __getitem__(self, key: int | str) -> Task:
        if isinstance(key, int):
            if 0 <= key < len(self._tasks):
                return self._tasks[key]
            raise IndexError(f"Завдання з порядковим індексом {key} не існує!")
        if isinstance(key, str):
            query = key.strip().lower()
            if not query:
                raise ValueError("Рядок пошуку не може бути порожнім!")
            for task in self._tasks:
                if query in task.assignee.full_name.lower():
                    return task
            for task in self._tasks:
                if task.task_id.lower() == query:
                    return task
            raise KeyError(f"Завдань для виконавця з прізвищем '{key}' не знайдено!")
        raise TypeError("Ключем пошуку має бути цілий індекс (int) або прізвище виконавця (str)!")

    def __iter__(self) -> PendingTaskIterator:
        """Повертає власний ітератор по невиконаних завданнях за спаданням пріоритету."""
        return PendingTaskIterator(self._tasks)

    def get_pending_tasks(self) -> PendingTaskIterator:
        return PendingTaskIterator(self._tasks)

    def generate_overdue_tasks(self):
        """Генератор (yield): ліниво видає прострочені завдання проєкту."""
        for task in self._tasks:
            if task.is_overdue or task.status == TaskStatus.EXPIRED:
                yield task

    def generate_tasks_by_assignee(self, assignee_query: str):
        """Генератор (yield): ліниво видає завдання конкретного виконавця."""
        target = assignee_query.strip().lower()
        for task in self._tasks:
            if target in task.assignee.full_name.lower():
                yield task

    def calculate_total_effort(self) -> float:
        return round(sum(t.estimate_hours() for t in self._tasks), 2)

    def show_all_tasks(self) -> None:
        print("\n" + "=" * 92)
        print(f" СПИСОК ЗАВДАНЬ ПРОЄКТУ ({self.config.get('company_name')}) — Всього: {len(self._tasks)}")
        print("=" * 92)
        if not self._tasks:
            print("  Колекція завдань наразі порожня.")
        else:
            for idx, item in enumerate(self._tasks, 1):
                print(f"  {idx}. {item.get_info()}")
            print("-" * 92)
            print(
                f"  Сумарна трудомісткість: {self.calculate_total_effort()} год | "
                f"Накопичений бюджет (Функтор): {self.estimator.total_estimated_cost} грн"
            )
        print("=" * 92)

    def save_system_state(self, filepath: str | None = None) -> None:
        raw_name = filepath or self.config.get("backup_file", "project_state.pkl")
        target = resolve_path(raw_name)
        with open(target, "wb") as file:
            pickle.dump(self._tasks, file)
        print(f"[Pickle] Стан системи ({len(self._tasks)} об'єктів) збережено у '{os.path.basename(target)}'.")

    def load_system_state(self, filepath: str | None = None) -> None:
        raw_name = filepath or self.config.get("backup_file", "project_state.pkl")
        target = resolve_path(raw_name)
        try:
            with open(target, "rb") as file:
                self._tasks = pickle.load(file)
            self.recalculate_budget()
            print(f"[Pickle] Успішно відновлено об'єктів із '{os.path.basename(target)}': {len(self._tasks)} шт.")
        except FileNotFoundError:
            print(f"[Інфо Pickle] Файл резервної копії '{os.path.basename(target)}' ще не створено (нова сесія).")
        except (pickle.UnpicklingError, EOFError, OSError) as err:
            print(f"[Помилка Pickle] Не вдалося відновити файл '{os.path.basename(target)}': {err}")

    def export_csv_report(self, filepath: str | None = None) -> None:
        raw_name = filepath or self.config.get("report_file", "project_report.csv")
        target = resolve_path(raw_name)
        delimiter = self.config.get("csv_delimiter", ";")
        multipliers = {
            TaskPriority.LOW: 1.0,
            TaskPriority.MEDIUM: 1.2,
            TaskPriority.HIGH: 1.5,
            TaskPriority.CRITICAL: 2.0,
        }
        with open(target, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=delimiter)
            writer.writerow([
                "ID завдання", "Категорія", "Назва завдання", "Код проєкту",
                "Виконавець", "Пріоритет", "Статус", "Трудомісткість (год)", "Вартість (грн)"
            ])
            for t in self._tasks:
                hours = t.estimate_hours()
                weight = multipliers.get(t.priority, 1.0)
                cost = round(hours * t.assignee.hourly_rate * weight, 2)
                writer.writerow([
                    t.task_id, t.get_task_category(), t.title, t.project.code,
                    t.assignee.full_name, t.priority.label, t.status.value, hours, cost
                ])
        print(f"[CSV] Звіт успішно експортовано у '{os.path.basename(target)}' (записано рядків: {len(self._tasks)}).")
