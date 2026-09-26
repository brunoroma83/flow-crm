import argparse
import sys
from pathlib import Path

from .backup import (
    create_backup,
    delete_backup,
    list_backups,
    restore_backup,
    rotate_old_backups,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="flow-crm-backup",
        description="Utilitário CLI para gerenciamento de backups e restauração do FlowCRM",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando create
    create_parser = subparsers.add_parser("create", help="Cria um novo backup do banco de dados")
    create_parser.add_argument("--label", "-l", default="manual", help="Rótulo identificador do backup (ex: manual, pre-deploy)")

    # Subcomando list
    subparsers.add_parser("list", help="Lista todos os backups disponíveis")

    # Subcomando restore
    restore_parser = subparsers.add_parser("restore", help="Restaura o banco de dados a partir de um arquivo")
    restore_parser.add_argument("--file", "-f", required=True, help="Nome do arquivo de backup (.dump ou .sql)")
    restore_parser.add_argument("--no-safety", action="store_true", help="Desativa a criação automática do safety snapshot antes de restaurar")

    # Subcomando delete
    delete_parser = subparsers.add_parser("delete", help="Exclui um arquivo de backup")
    delete_parser.add_argument("--file", "-f", required=True, help="Nome do arquivo a ser excluído")

    # Subcomando rotate
    rotate_parser = subparsers.add_parser("rotate", help="Remove backups antigos que excedam o limite de retenção")
    rotate_parser.add_argument("--days", "-d", type=int, default=30, help="Período de retenção em dias (padrão: 30)")

    args = parser.parse_args()

    try:
        if args.command == "create":
            res = create_backup(label=args.label)
            print(f"[OK] Backup criado com sucesso: {res['filename']} ({res['size_bytes']} bytes)")
        elif args.command == "list":
            backups = list_backups()
            if not backups:
                print("Nenhum backup encontrado.")
                return
            print(f"{'FILENAME':<45} {'LABEL':<15} {'SIZE (MB)':<10} {'CREATED AT'}")
            print("-" * 90)
            for b in backups:
                size_mb = f"{b['size_bytes'] / (1024 * 1024):.2f}"
                print(f"{b['filename']:<45} {b['label']:<15} {size_mb:<10} {b.get('created_at', '')}")
        elif args.command == "restore":
            safety = not args.no_safety
            print(f"[INFO] Iniciando restauração do arquivo '{args.file}'...")
            res = restore_backup(filename=args.file, safety_snapshot=safety)
            print(f"[OK] Restauração concluída com sucesso para '{args.file}'.")
            if res.get("safety_snapshot"):
                print(f"[SAFETY] Safety snapshot criado previamente: '{res['safety_snapshot']}'")
        elif args.command == "delete":
            delete_backup(filename=args.file)
            print(f"[OK] Backup '{args.file}' excluído.")
        elif args.command == "rotate":
            deleted = rotate_old_backups(retention_days=args.days)
            print(f"[OK] Rotação concluída. {len(deleted)} arquivo(s) removido(s).")
    except Exception as e:
        print(f"[ERRO] Erro ao executar operação de backup: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
