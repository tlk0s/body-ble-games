# Body BLE controller (PlatformIO)
PIO        ?= pio
BAUD       ?= 115200
ENV        ?= esp32-c3-supermini

flash-blue:
	$(MAKE) flash ENV=esp32-c3-blue-boy

flash-red:
	$(MAKE) flash ENV=esp32-c3-red-girl

ESP_PORT   ?= $(shell \
	for p in /dev/cu.usbmodem* /dev/cu.wchusbserial* /dev/cu.SLAB_USBtoUART* /dev/cu.usbserial*; do \
		[ -e "$$p" ] && echo "$$p" && exit 0; \
	done; \
	exit 0)

PORT       ?= $(ESP_PORT)

.PHONY: help build flash upload upload-only monitor ports free-port flash-blue flash-red

help:
	@echo "  make flash-blue / flash-red"
	@echo "  make flash PORT=/dev/cu.usbmodem101"
	@echo "  make ports"

build:
	$(PIO) run -e $(ENV)

free-port:
	@if [ -z "$(PORT)" ]; then exit 0; fi
	@PIDS=$$(lsof -t "$(PORT)" 2>/dev/null); \
	if [ -n "$$PIDS" ]; then kill $$PIDS 2>/dev/null || true; sleep 0.5; fi

upload-only:
	@if [ -z "$(PORT)" ] || [ ! -e "$(PORT)" ]; then \
		echo ""; \
		echo "No ESP port (or path missing). Plug in USB data cable, then:"; \
		echo "  ls /dev/cu.usbmodem*"; \
		echo "  make flash-blue PORT=/dev/cu.usbmodem101"; \
		echo ""; \
		$(MAKE) ports; \
		exit 1; \
	fi
	@$(MAKE) free-port
	@echo "Upload → $(PORT)"
	$(PIO) run -e $(ENV) -t upload --upload-port $(PORT)

flash: build upload-only

monitor:
	@if [ ! -e "$(PORT)" ]; then echo "Bad PORT=$(PORT). Run: make ports"; exit 1; fi
	@echo "Monitor $(PORT) — press RST if empty"
	$(PIO) device monitor --port $(PORT) -b $(BAUD) --raw

ports:
	@echo "Auto-detected: $(if $(ESP_PORT),$(ESP_PORT),none)"
	@echo ""
	@$(PIO) device list 2>/dev/null | head -30 || true
	@echo ""
	@ls /dev/cu.usbmodem* 2>/dev/null || echo "(no usbmodem devices)"
