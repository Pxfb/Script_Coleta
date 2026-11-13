"""Comando único: chama os três passos e, se solicitado, gera SAF."""
import sys
try:
    from sophia.fluxo import main
except ModuleNotFoundError as exc:
    print(f'Dependência ausente: {exc.name}. Execute instalar.bat ou python instalar.py.',file=sys.stderr)
    raise SystemExit(1)
if __name__ == '__main__':
    raise SystemExit(main())
