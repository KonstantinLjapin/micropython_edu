PORT = /dev/ttyACM0

# Быстрый запуск кода без сохранения на устройстве
run:
	mpremote connect $(PORT) run main.py

# Полная выгрузка проекта на устройство
deploy:
	mpremote connect $(PORT) cp -r lib/ :/
	mpremote connect $(PORT) cp -r drivers/ :/
	mpremote connect $(PORT) cp motor_control.py :
	mpremote connect $(PORT) cp main.py :
	mpremote connect $(PORT) reset
	@echo "✅ Проект успешно загружен!"

# Перезагрузка устройства и вход в REPL
repl:
	mpremote connect $(PORT) repl

# Мягкая перезагрузка устройства (без отключения питания)
reset:
	mpremote connect $(PORT) reset

# Очистка файловой системы устройства (ОСТОРОЖНО!)
clean-device:
	mpremote connect $(PORT) fs rm -r lib
	mpremote connect $(PORT) fs rm -r drivers