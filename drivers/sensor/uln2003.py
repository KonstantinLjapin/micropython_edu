from pyb import Pin
import time

"""
 # Инициализация двух двигателей
    # Двигатель 1 подключен к пинам X-порта Pyboard
    s1 = Stepper(HALF_STEP, 'X1', 'X2', 'X3', 'X4', delay=5)
    # Двигатель 2 подключен к пинам Y-порта Pyboard
    s2 = Stepper(HALF_STEP, 'Y1', 'Y2', 'Y3', 'Y4', delay=5)

    # --- Пример 1: Простое вращение одного мотора ---
    # s1.step(100)      # 100 шагов по часовой стрелке
    # pyb.delay(1000)   # Пауза 1 секунда
    # s1.step(100, -1)  # 100 шагов против часовой стрелки

    # --- Пример 2: Одновременное (интерливинг) вращение двух моторов ---
    # Создаем команды: 
    # c1: полный оборот по часовой стрелке
    # c2: половина оборота против часовой стрелки
    c1 = Command(s1, FULL_ROTATION, 1)
    c2 = Command(s2, FULL_ROTATION / 2, -1)

    # Запускаем драйвер, который будет чередовать шаги между s1 и s2
    runner = Driver()
    runner.run([c1, c2])
"""


LOW = 0
HIGH = 1
# Полный оборот для 28BYJ-48 составляет примерно 509 шагов (в режиме HALF_STEP)
FULL_ROTATION = int(4075.7728395061727 / 8)

HALF_STEP = [
    [LOW, LOW, LOW, HIGH],
    [LOW, LOW, HIGH, HIGH],
    [LOW, LOW, HIGH, LOW],
    [LOW, HIGH, HIGH, LOW],
    [LOW, HIGH, LOW, LOW],
    [HIGH, HIGH, LOW, LOW],
    [HIGH, LOW, LOW, LOW],
    [HIGH, LOW, LOW, HIGH],
]

FULL_STEP = [
    [HIGH, LOW, HIGH, LOW],
    [LOW, HIGH, HIGH, LOW],
    [LOW, HIGH, LOW, HIGH],
    [HIGH, LOW, LOW, HIGH]
]


class Command:
    """Команда для шагового двигателя: переместить на X шагов в заданном направлении"""

    def __init__(self, stepper, steps, direction=1):
        self.stepper = stepper
        self.steps = int(steps)  # Гарантируем целочисленное значение
        self.direction = direction


class Driver:
    """Управляет набором двигателей, чередуя их шаги для кажущегося одновременного движения"""

    @staticmethod
    def run(commands):
        max_steps = sum(c.steps for c in commands)
        count = 0
        while count < max_steps:
            for command in commands:
                if command.steps > 0:
                    command.stepper.step(1, command.direction)
                    command.steps -= 1
                    count += 1


class Stepper:
    def __init__(self, mode, pin1_name, pin2_name, pin3_name, pin4_name, delay=2):
        self.mode = mode
        self.delay = delay
        self.pin1 = Pin(pin1_name, Pin.OUT_PP)
        self.pin2 = Pin(pin2_name, Pin.OUT_PP)
        self.pin3 = Pin(pin3_name, Pin.OUT_PP)
        self.pin4 = Pin(pin4_name, Pin.OUT_PP)

        # === НОВОЕ: Внутреннее состояние ===
        self.current_pos = 0  # Текущая абсолютная позиция в шагах
        self.reset()

    def step(self, count, direction=1):
        """Низкоуровневый метод: делает физическое движение"""
        if count <= 0:
            return
        step_sequence = self.mode[::direction]
        for _ in range(count):
            for bit in step_sequence:
                self.pin1.value(bit[0])
                self.pin2.value(bit[1])
                self.pin3.value(bit[2])
                self.pin4.value(bit[3])
                time.sleep_ms(self.delay)
        self.reset()

    def reset(self):
        self.pin1.value(0);
        self.pin2.value(0);
        self.pin3.value(0);
        self.pin4.value(0)

    # === НОВОЕ: Высокоуровневый метод без дублирования логики ===
    def move_to(self, target_pos, max_steps_per_cycle=15):
        """
        Плавно двигается к целевой позиции.
        Если цель изменилась, мгновенно пересчитывает направление.
        Никакого накопления очереди!
        """
        # 1. Вычисляем, сколько шагов осталось сделать
        error = target_pos - self.current_pos

        # 2. Если мы уже на месте, ничего не делаем (защита от дрожания)
        if error == 0:
            return

        # 3. Определяем направление и ограничиваем скорость (anti-backlog)
        direction = 1 if error > 0 else -1
        steps_to_take = min(abs(error), max_steps_per_cycle)

        # 4. Делаем шаг и ОБНОВЛЯЕМ внутреннее состояние
        self.step(steps_to_take, direction)
        self.current_pos += steps_to_take * direction


def driver_test(step, in1, in2, in3, in4):
    if step == 'h':
        step_data = HALF_STEP
        delay = 5
    elif step == 'f':
        step_data = FULL_STEP
        delay = 10
    # Двигатель 1 подключен к пинам X-порта Pyboard
    s1 = Stepper(mode=step_data, pin1_name=in1, pin2_name=in2, pin3_name=in3, pin4_name=in4, delay=delay)
    # Двигатель 2 подключен к пинам Y-порта Pyboard


    # --- Пример 1: Простое вращение одного мотора ---
    # s1.step(100)      # 100 шагов по часовой стрелке
    # pyb.delay(1000)   # Пауза 1 секунда
    # s1.step(100, -1)  # 100 шагов против часовой стрелки

    # --- Пример 2: Одновременное (интерливинг) вращение двух моторов ---
    # Создаем команды:
    # c1: полный оборот по часовой стрелке
    # c2: половина оборота против часовой стрелки
    c1 = Command(s1, FULL_ROTATION, 1)

    # Запускаем драйвер, который будет чередовать шаги между s1 и s2
    runner = Driver()
    runner.run([c1])
