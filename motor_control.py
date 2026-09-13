import gc
import time
from drivers.sensor.gy271 import Magnetometer
from drivers.sensor.uln2003 import Stepper, HALF_STEP


class HeadingMotorController:
    FULL_ROTATION_STEPS = 509

    def __init__(self, compass, stepper):
        self.compass = compass
        self.stepper = stepper

        # Коэффициент перевода градусов в шаги (509 шагов / 360 градусов)
        self.steps_per_degree = self.FULL_ROTATION_STEPS / 360.0

        # 1. Захватываем начальный курс при старте
        self.start_heading = self.compass.compass_2d()
        print(f"[START] Начальный курс: {self.start_heading}°")

        # Внутреннее отслеживание физического положения мотора (в градусах)
        self.current_motor_degrees = 0.0

        # Мертвая зона (в градусах). Если разница меньше, мотор не дергается,
        # что спасает от дребезга показаний сенсора.
        self.deadzone = 3.0

        # Максимальное количество шагов за ОДИН цикл обновления.
        # Это ключевой параметр для предотвращения накопления!
        # Даже если ошибка 90 градусов, мотор сделает только этот лимит шагов за цикл,
        # а на следующем цикле пересчитает цель заново.
        self.max_steps_per_cycle = 15

    @staticmethod
    def get_shortest_angle_diff(target, current):
        """
        Вычисляет кратчайшую разницу между двумя углами.
        Возвращает значение от -180 до +180.
        """
        diff = (target - current + 180) % 360 - 180
        return diff

    def update(self):
        # 1. Получаем самый свежий курс с компаса
        current_heading = self.compass.compass_2d()

        # 2. Вычисляем, на сколько градусов мотор должен отклониться от старта
        desired_motor_diff = self.get_shortest_angle_diff(current_heading, self.start_heading)

        # 3. Вычисляем ошибку: где мотор сейчас vs где он должен быть
        error = self.get_shortest_angle_diff(desired_motor_diff, self.current_motor_degrees)

        # 4. Проверка мертвой зоны (защита от дрожания)
        if abs(error) < self.deadzone:
            return

        # 5. Вычисляем, сколько шагов нужно сделать для коррекции
        required_steps = abs(error) * self.steps_per_degree

        # 6. ОГРАНИЧИТЕЛЬ (Anti-Backlog): берем не более max_steps_per_cycle
        # Это гарантирует, что мы всегда реагируем на ПОСЛЕДНЕЕ состояние компаса,
        # а не отрабатываем старую очередь.
        steps_to_take = int(min(required_steps, self.max_steps_per_cycle))

        if steps_to_take > 0:
            direction = 1 if error > 0 else -1

            # Поворачиваем мотор
            self.stepper.step(steps_to_take, direction)

            # Обновляем наше представление о текущем положении мотора
            step_degrees = steps_to_take / self.steps_per_degree
            self.current_motor_degrees += step_degrees * direction

            # Отладочный вывод (можно убрать в продакшене)
            print(f"H:{current_heading}° | Err:{error:.1f}° | Step:{steps_to_take} ({direction})")


def motor_set_compass():
    print("Инициализация оборудования...")
    gc.collect()  # Принудительно освобождаем память
    print("Свободно памяти:", gc.mem_free())

    # Инициализация компаса (укажите ваши реальные пины SCL и SDA)
    # Например, для Pyboard: SCL='X9', SDA='X10' или 'Y9'/'Y10'
    compass = Magnetometer(scl='X9', sda='X10')
    compass.calibrate()

    # Инициализация мотора (укажите ваши реальные пины ULN2003)
    # Например, для Pyboard: 'X1', 'X2', 'X3', 'X4'
    stepper = Stepper(HALF_STEP, 'X1', 'X2', 'X3', 'X4', delay=3)

    print("Запуск цикла слежения. Вращайте компас, мотор будет следовать за изменением угла.")
    # Создание контроллера
    controller = HeadingMotorController(compass, stepper)

    print("Нажмите Ctrl+C для остановки.")

    try:
        while True:
            # Вызываем update() как можно чаще.
            # Он сам решит, нужно ли двигать мотор и насколько, без накопления очереди.
            controller.update()

            # Небольшая задержка, чтобы не нагружать шину I2C и дать мотору физически сдвинуться
            time.sleep_ms(50)

    except KeyboardInterrupt:
        print("\nОстановка программы.")
        stepper.reset()
