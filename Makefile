# cupertino-aboutpane installer

SHELL    := /bin/sh
BIN_NAME := aboutpane
PY_NAME  := aboutpane.py
DESKTOP  := aboutpane.desktop

LOCAL_BIN  := $(HOME)/.local/bin
LOCAL_APPS := $(HOME)/.local/share/applications
SYS_BIN    := /usr/local/bin
SYS_APPS   := /usr/share/applications

.PHONY: install install-system uninstall uninstall-system

install: ## Install for current user (~/.local/bin + ~/.local/share/applications)
	@mkdir -p "$(LOCAL_BIN)" "$(LOCAL_APPS)"
	@sed 's|/usr/local/bin/$(PY_NAME)|$(LOCAL_BIN)/$(PY_NAME)|g' $(BIN_NAME) > "$(LOCAL_BIN)/$(BIN_NAME)"
	@chmod +x "$(LOCAL_BIN)/$(BIN_NAME)"
	@cp $(PY_NAME) "$(LOCAL_BIN)/$(PY_NAME)"
	@chmod +x "$(LOCAL_BIN)/$(PY_NAME)"
	@cp $(DESKTOP) "$(LOCAL_APPS)/$(DESKTOP)"
	@update-desktop-database "$(LOCAL_APPS)" 2>/dev/null || true
	@printf 'Installed to %s\n' "$(LOCAL_BIN)"
	@printf 'Desktop entry installed to %s\n' "$(LOCAL_APPS)"
	@printf 'Make sure %s is in your PATH.\n' "$(LOCAL_BIN)"

install-system: ## Install system-wide (/usr/local/bin + /usr/share/applications) — requires sudo
	@cp $(BIN_NAME) "$(SYS_BIN)/$(BIN_NAME)"
	@chmod +x "$(SYS_BIN)/$(BIN_NAME)"
	@cp $(PY_NAME) "$(SYS_BIN)/$(PY_NAME)"
	@chmod +x "$(SYS_BIN)/$(PY_NAME)"
	@cp $(DESKTOP) "$(SYS_APPS)/$(DESKTOP)"
	@update-desktop-database "$(SYS_APPS)" 2>/dev/null || true
	@printf 'Installed system-wide to %s\n' "$(SYS_BIN)"
	@printf 'Desktop entry installed to %s\n' "$(SYS_APPS)"

uninstall: ## Remove user install
	@rm -f "$(LOCAL_BIN)/$(BIN_NAME)" "$(LOCAL_BIN)/$(PY_NAME)" "$(LOCAL_APPS)/$(DESKTOP)"
	@update-desktop-database "$(LOCAL_APPS)" 2>/dev/null || true
	@printf 'Uninstalled from %s\n' "$(LOCAL_BIN)"

uninstall-system: ## Remove system-wide install — requires sudo
	@rm -f "$(SYS_BIN)/$(BIN_NAME)" "$(SYS_BIN)/$(PY_NAME)" "$(SYS_APPS)/$(DESKTOP)"
	@update-desktop-database "$(SYS_APPS)" 2>/dev/null || true
	@printf 'Uninstalled from %s\n' "$(SYS_BIN)"
