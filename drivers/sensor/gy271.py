from machine import SoftI2C, Pin
from math import atan2, pi
import struct, time

from machine import SoftI2C, Pin
from math import atan2, pi
import struct, time


class Magnetometer:
    """
    Драйвер для магнитометра QMC5883P (часто встречается на модуле GY-271).

    Требуемые параметры при инициализации: номера пинов SCL и SDA.

    Чип настраивается на следующие параметры:
     - Обычный режим питания (Normal power mode)
     - Частота обновления данных 200 Гц
     - 4-кратное усреднение показаний сенсора на один выходной результат
     - Без даунсэмплинга (down sampling = 0, вывод каждого измерения)
     - Диапазон измерений: 2 Гаусса (чувствительность 15000 LSB/G)
     - Режим Set and Reset включен (для компенсации температурного дрейфа)

    Основные методы:
        getdata_raw()
            Возвращает сырые показания магнитометра в Гауссах в виде списка [x, y, z].

        compass_2d(declination=0)
            Возвращает курс (heading), округленный до ближайшего градуса.
            Не учитывает крен и тангаж (работает точно только в горизонтальном положении).

        compass_3d_from_accel(ax, ay, az, declination=0)
            3D-компас с компенсацией наклона, использующий сырые данные акселерометра.

        calibrate(calibrationrotations=2)
            Калибровка сенсора для устранения эффектов "жесткого" и "мягкого" железа.
            Выводит подробные пошаговые инструкции в консоль. Оптимизировано для MicroPython (O(1) памяти).
    """

    def __init__(self, scl, sda):
        self.qmc5883p = SoftI2C(scl=Pin(scl), sda=Pin(sda), freq=400000)
        self.qmc5883p_address = 0x2C

        self.registers = {
            "chipid": 0x00,
            "x-axis data": 0x01,
            "y-axis data": 0x03,
            "z-axis data": 0x05,
            "axis invert": 0x29,
            "status": 0x09,
            "control1": 0x0A,
            "control2": 0x0B,
        }

        self.data = [0, 0, 0]
        self.softcal = [1.0, 1.0, 1.0]
        self.hardcal = [0.0, 0.0, 0.0]

        time.sleep_us(250)
        self._modulesetup()

    def _log(self, string):
        print(string)

    def _modulesetup(self):
        self.qmc5883p.writeto_mem(self.qmc5883p_address, self.registers["control1"], bytes([0x1D]))
        self.qmc5883p.writeto_mem(self.qmc5883p_address, self.registers["control2"], bytes([0x0C]))
        self._log("[OK] Модуль QMC5883P настроен и готов к работе.")

    @micropython.native
    def _update_data(self):
        counter = 0
        status_reg = self.registers["status"]

        while not (self.qmc5883p.readfrom_mem(self.qmc5883p_address, status_reg, 1)[0] & 0x01):
            time.sleep_us(5)
            counter += 1
            if counter > 2:
                return None

        data = self.qmc5883p.readfrom_mem(self.qmc5883p_address, self.registers["x-axis data"], 6)

        x_axis = struct.unpack("<h", data[:2])[0] / 15000
        y_axis = struct.unpack("<h", data[2:4])[0] / 15000
        z_axis = struct.unpack("<h", data[4:])[0] / 15000

        self.data[0] = (x_axis - self.hardcal[0]) * self.softcal[0]
        self.data[1] = (y_axis - self.hardcal[1]) * self.softcal[1]
        self.data[2] = (z_axis - self.hardcal[2]) * self.softcal[2]

        return True

    @micropython.native
    def _normalize(self, vector):
        v1, v2, v3 = vector
        length = (v1 * v1 + v2 * v2 + v3 * v3) ** 0.5
        if length == 0:
            return [0.0, 0.0, 0.0]
        return [v1 / length, v2 / length, v3 / length]

    def _axes_calibration_rotations(self, fieldstrength):
        """
        Ожидает вращения устройства и отслеживает мин/макс значения по осям.
        Использует O(1) памяти, что предотвращает MemoryError в MicroPython.
        """
        # Инициализация мин/макс текущими значениями
        min_x = max_x = self.data[0]
        min_y = max_y = self.data[1]
        min_z = max_z = self.data[2]

        # Запоминаем стартовые позиции для определения возврата в исходную точку
        start_x = self.data[0]
        start_y = self.data[1]
        start_z = self.data[2]

        xcomplete, ycomplete, zcomplete = False, False, False

        self._log("  >>> ВРАЩАЙТЕ УСТРОЙСТВО! Ожидаю полного оборота по каждой оси...")

        while not (xcomplete and ycomplete and zcomplete):
            flag = self._update_data()
            if flag is None:
                continue

            cx, cy, cz = self.data[0], self.data[1], self.data[2]

            # Обновляем мин/макс на лету (без сохранения в списки!)
            if cx < min_x: min_x = cx
            if cx > max_x: max_x = cx
            if cy < min_y: min_y = cy
            if cy > max_y: max_y = cy
            if cz < min_z: min_z = cz
            if cz > max_z: max_z = cz

            # Проверка завершения оборота: диапазон > 80% от ожидаемого И значение вернулось к старту
            if not xcomplete:
                if (max_x - min_x) > 0.8 * 2 * fieldstrength and abs(cx - start_x) < 0.1:
                    xcomplete = True
                    self._log("  [OK] Ось X откалибрована!")
            if not ycomplete:
                if (max_y - min_y) > 0.8 * 2 * fieldstrength and abs(cy - start_y) < 0.1:
                    ycomplete = True
                    self._log("  [OK] Ось Y откалибрована!")
            if not zcomplete:
                if (max_z - min_z) > 0.8 * 2 * fieldstrength and abs(cz - start_z) < 0.1:
                    zcomplete = True
                    self._log("  [OK] Ось Z откалибрована!")

            time.sleep_ms(10)

        return min_x, max_x, min_y, max_y, min_z, max_z

    def calibrate(self, calibrationrotations=2):
        """
        Метод калибровки магнитометра. Устраняет эффекты "жесткого" и "мягкого" железа.
        Оптимизирован для MicroPython: использует только глобальные мин/макс значения,
        что исключает ошибки нехватки памяти (MemoryError).
        """
        self._log("=" * 60)
        self._log(" НАЧАЛО КАЛИБРОВКИ МАГНИТОМЕТРА (QMC5883P)")
        self._log("=" * 60)
        self._log("ИНСТРУКЦИЯ ПО ВРАЩЕНИЮ:")
        self._log(" 1. Держите устройство в руке, как мяч.")
        self._log(" 2. Медленно вращайте его на 360° вокруг оси X (кувырок вперед-назад).")
        self._log(" 3. Затем медленно вращайте его на 360° вокруг оси Y (влево-вправо).")
        self._log(
            " 4. Повторите этот цикл {} раз(а), описывая большие сферы в пространстве.".format(calibrationrotations))
        self._log(" 5. Избегайте резких движений и nearby металлических предметов.")
        self._log("-" * 60)
        self._log("Подготовка... (начало через 2 секунды)")
        time.sleep(2)

        fieldstrength = 0
        number_readings_fieldstrength = 20

        # ЭТАП 1: Определение базовой напряженности поля
        self._log("[ЭТАП 1/4] Измерение базовой напряженности магнитного поля...")
        self._log("  -> Держите устройство неподвижно...")
        for i in range(number_readings_fieldstrength):
            flag = self._update_data()
            if flag is not None:
                vector_length = (self.data[0] ** 2 + self.data[1] ** 2 + self.data[2] ** 2) ** 0.5
                fieldstrength += vector_length
            time.sleep_ms(5)

        fieldstrength /= number_readings_fieldstrength
        self._log("  [OK] Базовая напряженность поля определена: {:.4f} Гаусс".format(fieldstrength))
        time.sleep(1)

        # ЭТАП 2: Сбор данных при вращении (Глобальные мин/макс)
        self._log("[ЭТАП 2/4] Сбор данных при вращении (всего циклов: {})...".format(calibrationrotations + 1))

        g_min_x = g_max_x = 0.0
        g_min_y = g_max_y = 0.0
        g_min_z = g_max_z = 0.0
        first_run = True

        for i in range(calibrationrotations + 1):
            self._log("  -> Цикл вращения {} из {}. Начните плавное вращение устройства!".format(i + 1,
                                                                                                 calibrationrotations + 1))

            # Получаем мин/макс за один цикл вращения
            min_x, max_x, min_y, max_y, min_z, max_z = self._axes_calibration_rotations(fieldstrength)
            self._log("  [OK] Цикл {} успешно завершен.".format(i + 1))

            # Обновляем глобальные мин/макс
            if first_run:
                g_min_x, g_max_x = min_x, max_x
                g_min_y, g_max_y = min_y, max_y
                g_min_z, g_max_z = min_z, max_z
                first_run = False
            else:
                if min_x < g_min_x: g_min_x = min_x
                if max_x > g_max_x: g_max_x = max_x
                if min_y < g_min_y: g_min_y = min_y
                if max_y > g_max_y: g_max_y = max_y
                if min_z < g_min_z: g_min_z = min_z
                if max_z > g_max_z: g_max_z = max_z

            time.sleep(0.5)

        # ЭТАП 3: Обработка данных
        self._log("[ЭТАП 3/4] Обработка и математический расчет коэффициентов...")
        self._log("  -> Глобальные минимумы: X={:.4f}, Y={:.4f}, Z={:.4f}".format(g_min_x, g_min_y, g_min_z))
        self._log("  -> Глобальные максимумы: X={:.4f}, Y={:.4f}, Z={:.4f}".format(g_max_x, g_max_y, g_max_z))

        # ЭТАП 4: Применение калибровки
        self._log("[ЭТАП 4/4] Применение калибровочных коэффициентов...")

        # Hard Iron (Center offsets) - смещение центра сферы
        self.hardcal[0] = (g_max_x + g_min_x) / 2.0
        self.hardcal[1] = (g_max_y + g_min_y) / 2.0
        self.hardcal[2] = (g_max_z + g_min_z) / 2.0
        self._log("  [OK] Компенсация 'жесткого железа' (Hard Iron) завершена.")
        self._log("       Смещения (должны быть близки к 0.0):")
        self._log(
            "       X: {:>7.4f}, Y: {:>7.4f}, Z: {:>7.4f}".format(self.hardcal[0], self.hardcal[1], self.hardcal[2]))

        # Soft Iron (Scale factors) - масштабирование осей для превращения эллипсоида в сферу
        range_x = (g_max_x - g_min_x) / 2.0
        range_y = (g_max_y - g_min_y) / 2.0
        range_z = (g_max_z - g_min_z) / 2.0

        avg_range = (range_x + range_y + range_z) / 3.0

        # Защита от деления на ноль, если ось не была задействована
        self.softcal[0] = avg_range / range_x if range_x > 0.001 else 1.0
        self.softcal[1] = avg_range / range_y if range_y > 0.001 else 1.0
        self.softcal[2] = avg_range / range_z if range_z > 0.001 else 1.0

        self._log("  [OK] Компенсация 'мягкого железа' (Soft Iron) завершена.")
        self._log("       Масштабирование (должно быть близко к 1.0):")
        self._log(
            "       X: {:>7.4f}, Y: {:>7.4f}, Z: {:>7.4f}".format(self.softcal[0], self.softcal[1], self.softcal[2]))

        self._log("=" * 60)
        self._log(" КАЛИБРОВКА УСПЕШНО ЗАВЕРШЕНА!")
        self._log("=" * 60)

    def getdata_raw(self):
        self._update_data()
        return self.data

    def compass_2d(self, declination=0):
        """
        Базовый 2D-компас. НЕ требует данных акселерометра/гироскопа.
        Работает точно только тогда, когда модуль расположен строго горизонтально.
        declination: магнитное склонение в градусах (по умолчанию 0).
        """
        self._update_data()
        # Север принимается за отрицательную ось X модуля GY-271
        heading = atan2(self.data[1], -self.data[0]) * (180 / pi) - declination
        heading %= 360
        return int(heading + 0.5)


def get_compass(slc, sda):
    compass = Magnetometer(slc, sda)
    compass.calibrate()  # Выполните вращения сенсора, как будет запрошено

    # 3. Основной цикл получения компенсированного курса
    while True:
        heading = compass.compass_2d()
        print(heading)
        time.sleep(0.1)
