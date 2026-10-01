# ESP32-C3 SuperMini motion test (PlatformIO)
# Override port: make upload PORT=/dev/cu.usbmodem1101

PIO        ?= pio
BAUD       ?= 115200
ENV        ?= esp32-c3-supermini

flash-blue:
	$(MAKE) flash ENV=esp32-c3-blue-boy

flash-red:
	$(MAKE) flash ENV=esp32-c3-red-girl

# First matching USB serial (avoid Bluetooth/Jabra auto-detect)
ESP_PORT   ?= $(shell \
	for p in /dev/cu.usbmodem* /dev/cu.wchusbserial* /dev/cu.SLAB_USBtoUART* /dev/cu.usbserial*; do \
		[ -e "$$p" ] && echo "$$p" && exit 0; \
	done; \
	exit 0)

PORT       ?= $(ESP_PORT)

.PHONY: help build upload monitor deploy clean ports upload-only port-users free-port flash flash-blue flash-red m usb-check

help:
	@echo "Body motion test — make targets"
	@echo ""
	@echo "  make build        Compile firmware (ENV=... for blue/red)"
	@echo "  make flash-blue   Blue remote → boy hero"
	@echo "  make flash-red    Red remote → girl hero"
	@echo "  make flash        Build + upload (frees busy port first)"
	@echo "  make upload       Same as flash"
	@echo "  make monitor      Serial log at $(BAUD) (auto USB port)"
	@echo "  make deploy       flash then monitor"
	@echo "  make ports        List /dev/cu.* and detected ESP port"
	@echo "  make usb-check    macOS USB tree (Espressif / serial should appear when plugged in)"
	@echo "  make m            Alias for monitor"
	@echo "  make port-users   Show process using PORT (lsof)"
	@echo "  make free-port    Kill process holding PORT (close monitor first if you prefer)"
	@echo "  make clean        Remove PlatformIO build artifacts"
	@echo ""
	@echo "  make upload PORT=/dev/cu.usbmodem1101   Force port"

port-users:
	@test -n "$(PORT)" || (echo "No PORT. Run: make ports"; exit 1)
	@echo "Processes using $(PORT):"
	@lsof "$(PORT)" 2>/dev/null || echo "  (none — port free or wrong path)"

free-port:
	@if [ -z "$(PORT)" ]; then \
		echo "No PORT set — nothing to free."; \
		exit 0; \
	fi
	@PIDS=$$(lsof -t "$(PORT)" 2>/dev/null); \
	if [ -z "$$PIDS" ]; then \
		echo "Port $(PORT) is free."; \
	else \
		echo "Stopping PIDs on $(PORT): $$PIDS"; \
		kill $$PIDS 2>/dev/null || true; \
		sleep 0.5; \
		PIDS2=$$(lsof -t "$(PORT)" 2>/dev/null); \
		if [ -n "$$PIDS2" ]; then \
			echo "Still busy — try: kill -9 $$PIDS2"; \
			exit 1; \
		fi; \
		echo "Port is free."; \
	fi

build:
	$(PIO) run -e $(ENV)

upload-only:
	@if [ -z "$(PORT)" ]; then \
		echo ""; \
		echo "No ESP USB serial port detected (looking for usbmodem / wchusbserial / SLAB / usbserial)."; \
		echo "  • Plug in the SuperMini with a data USB-C cable (not charge-only)."; \
		echo "  • Run: make ports   then flash with the cu.* name you see."; \
		echo "  • Example: make flash-blue PORT=/dev/cu.usbmodem101"; \
		echo ""; \
		$(MAKE) ports; \
		exit 1; \
	fi
	@$(MAKE) free-port
	@echo "Upload → $(PORT)"
	$(PIO) run -e $(ENV) -t upload --upload-port $(PORT)

flash: build upload-only
upload: flash

monitor:
	@if [ -z "$(PORT)" ] || [ ! -e "$(PORT)" ]; then \
		echo ""; \
		if [ -n "$(PORT)" ] && [ ! -e "$(PORT)" ]; then \
			echo "Port $(PORT) does not exist (unplugged or macOS renumbered it after replug)."; \
		else \
			echo "No ESP USB port. Plug in the board or set PORT=..."; \
		fi; \
		echo "Run: make ports"; \
		echo ""; \
		$(MAKE) ports; \
		exit 1; \
	fi
	@echo "Monitor $(PORT) @ $(BAUD) — then press RST on the board if the screen stays empty"
	$(PIO) device monitor --port $(PORT) -b $(BAUD) --raw

deploy: upload monitor

m: monitor

usb-check:
	@echo "Plug in the SuperMini, then look for Espressif / USB JTAG / usbmodem below."
	@system_profiler SPUSBDataType 2>/dev/null | sed -n '/USB:/,/^$$/p' | head -80 || true

ports:
	@echo "Detected ESP port: $(if $(ESP_PORT),$(ESP_PORT),none)"
	@echo ""
	@echo "PlatformIO serial devices:"
	@$(PIO) device list 2>/dev/null | sed -n '1,40p' || true
	@echo ""
	@echo "All /dev/cu.*:"
	@ls /dev/cu.* 2>/dev/null || true

clean:
	$(PIO) run -e $(ENV) -t clean
