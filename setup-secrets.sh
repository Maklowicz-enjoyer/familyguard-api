#!/bin/bash
# setup-secrets.sh
# Uruchom RAZ na każdej maszynie: ./setup-secrets.sh
# Tworzy folder secrets/ z losowymi wartościami.
# Ten folder NIE trafia na git (jest w .gitignore).

set -e

echo "==> Tworzę folder secrets/"
mkdir -p secrets

echo "==> Generuję hasło do PostgreSQL..."
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > secrets/pg_password.txt

echo "==> Ustawiam nazwę użytkownika PostgreSQL..."
echo "appuser" > secrets/pg_user.txt

echo "==> Generuję SECRET_KEY dla JWT..."
python3 -c "import secrets; print(secrets.token_hex(32))" > secrets/api_secret_key.txt

echo "==> Ustawiam uprawnienia (tylko właściciel może czytać)..."
chmod 600 secrets/*.txt
chmod 700 secrets/

echo ""
echo "✅ Gotowe! Sekrety w secrets/:"
ls -la secrets/
echo ""
echo "⚠️  Folder secrets/ jest w .gitignore - nie trafi na GitHub"
echo "⚠️  Partner musi uruchomić ten skrypt na swojej maszynie osobno"
