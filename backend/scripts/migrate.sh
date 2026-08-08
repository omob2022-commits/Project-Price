#!/usr/bin/env bash
#
# Database migration helper script
# Usage: ./scripts/migrate.sh [command]
#
# Commands:
#   upgrade     - Apply all pending migrations (default)
#   downgrade   - Rollback one migration
#   current     - Show current revision
#   history     - Show migration history
#   create      - Create a new migration (requires description)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

COMMAND="${1:-upgrade}"

case "$COMMAND" in
    upgrade)
        echo "🚀 Applying migrations..."
        python -m alembic upgrade head
        echo "✅ Migrations complete"
        ;;
    
    downgrade)
        echo "⚠️  Rolling back one migration..."
        python -m alembic downgrade -1
        echo "✅ Rollback complete"
        ;;
    
    current)
        echo "📍 Current revision:"
        python -m alembic current
        ;;
    
    history)
        echo "📚 Migration history:"
        python -m alembic history --verbose
        ;;
    
    create)
        if [ -z "${2:-}" ]; then
            echo "❌ Error: Migration description required"
            echo "Usage: ./scripts/migrate.sh create 'your_description_here'"
            exit 1
        fi
        echo "📝 Creating new migration: $2"
        python -m alembic revision --autogenerate -m "$2"
        echo "✅ Migration created"
        ;;
    
    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        echo "Available commands:"
        echo "  upgrade     - Apply all pending migrations (default)"
        echo "  downgrade   - Rollback one migration"
        echo "  current     - Show current revision"
        echo "  history     - Show migration history"
        echo "  create DESC - Create a new migration with description"
        exit 1
        ;;
esac
