PYTHON_DIR="/home/${FIRST_USER_NAME}/python"
python3 -c "import platform;print(platform.machine());"
python3 -m venv "${PYTHON_DIR}/venv"
"${PYTHON_DIR}/venv/bin/python" -m pip install --no-cache-dir --upgrade --index-url=https://www.piwheels.org/simple pip
"${PYTHON_DIR}/venv/bin/pip" install --no-cache-dir --upgrade --index-url=https://www.piwheels.org/simple setuptools wheel
"${PYTHON_DIR}/venv/bin/pip" install --no-cache-dir -r "${PYTHON_DIR}/requirements.txt"
