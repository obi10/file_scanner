#!/usr/bin/env python3
"""Simulación segura y local de copia no autorizada desde un disco ficticio."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from fixtures import build_docx, build_pdf, build_pptx, build_xlsx


PROJECT_ROOT = Path(__file__).resolve().parent
LAB_ROOT = PROJECT_ROOT / "laboratorio"
FAKE_DRIVE = LAB_ROOT / "disco_externo_ficticio"
RESULTS_ROOT = LAB_ROOT / "resultados"
AUDIT_LOG = LAB_ROOT / "auditoria.jsonl"
MARKER = LAB_ROOT / ".entorno_simulado"

TARGET_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".json",
    ".odp",
    ".ods",
    ".odt",
    ".pdf",
    ".ppt",
    ".pptx",
    ".rtf",
    ".txt",
    ".xls",
    ".xlsx",
}
CONTROLS = ("sin-controles", "solo-lectura", "bloqueo-lectura")
USB_TEST_DIRECTORY = "SIMULACION_ACADEMICA_SEGURA"
USB_MARKER_FILENAME = ".marcador_laboratorio_usb"
USB_MARKER_CONTENT = "LABORATORIO-USB-CONTROLADO-v1\n"
USB_FAKE_CONTENT = (
    "ARCHIVO FICTICIO PARA PRUEBA ACADÉMICA.\n"
    "No contiene información personal ni credenciales reales.\n"
)

FAKE_FILES = {
    "documentos/clientes_ficticios.csv": (
        "id,nombre,email\n"
        "F001,Ana Ejemplo,ana@example.invalid\n"
        "F002,Luis Demostración,luis@example.invalid\n"
    ),
    "documentos/notas_ficticias.txt": (
        "DOCUMENTO DE PRUEBA. No contiene información real.\n"
        "Proyecto: Demostración universitaria de controles de acceso.\n"
    ),
    "configuracion/cuenta_ficticia.json": json.dumps(
        {
            "aviso": "DATOS COMPLETAMENTE FICTICIOS",
            "usuario": "usuario_demo",
            "token": "TOKEN-FALSO-NO-UTILIZABLE",
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    "otros/no_objetivo.bin": "ARCHIVO FICTICIO NO SELECCIONADO\n",
}

FAKE_BINARY_BUILDERS = {
    "documentos/informe_ficticio.docx": build_docx,
    "documentos/reporte_ficticio.pdf": build_pdf,
    "hojas/calculo_ficticio.xlsx": build_xlsx,
    "presentaciones/exposicion_ficticia.pptx": build_pptx,
}

USB_FIXTURE_BUILDERS = {
    "archivo_ficticio.txt": lambda: USB_FAKE_CONTENT.encode("utf-8"),
    "documento_ficticio.docx": build_docx,
    "hoja_ficticia.xlsx": build_xlsx,
    "presentacion_ficticia.pptx": build_pptx,
    "reporte_ficticio.pdf": build_pdf,
}


@dataclass(frozen=True)
class AuditEvent:
    timestamp_utc: str
    scenario: str
    action: str
    relative_source: str
    relative_destination: str | None
    bytes_copied: int
    sha256: str | None
    result: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_inside(path: Path, parent: Path) -> Path:
    """Resuelve una ruta y falla si sale del directorio permitido."""
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    try:
        resolved_path.relative_to(resolved_parent)
    except ValueError as exc:
        raise RuntimeError(
            f"Límite de seguridad: {resolved_path} está fuera de {resolved_parent}"
        ) from exc
    return resolved_path


def initialize_lab() -> None:
    LAB_ROOT.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "Este marcador identifica el entorno académico simulado.\n",
        encoding="utf-8",
    )
    for relative_name, content in FAKE_FILES.items():
        destination = ensure_inside(FAKE_DRIVE / relative_name, FAKE_DRIVE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    for relative_name, builder in FAKE_BINARY_BUILDERS.items():
        destination = ensure_inside(FAKE_DRIVE / relative_name, FAKE_DRIVE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(builder())
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)


def target_files() -> Iterable[Path]:
    ensure_inside(FAKE_DRIVE, LAB_ROOT)
    for path in sorted(FAKE_DRIVE.rglob("*")):
        if path.is_file() and path.suffix.lower() in TARGET_EXTENSIONS:
            yield ensure_inside(path, FAKE_DRIVE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_audit(event: AuditEvent) -> None:
    ensure_inside(AUDIT_LOG, LAB_ROOT)
    with AUDIT_LOG.open("a", encoding="utf-8") as audit:
        audit.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")


def validate_mount_root(raw_path: str | Path) -> Path:
    """Acepta únicamente la raíz real de un volumen montado y no el disco del SO."""
    mount_root = Path(raw_path).expanduser().resolve()
    if not mount_root.is_dir():
        raise RuntimeError(f"El punto de montaje no existe: {mount_root}")
    if not os.path.ismount(mount_root):
        raise RuntimeError(f"La ruta no es la raíz de un volumen montado: {mount_root}")
    if os.name == "posix" and mount_root == Path("/"):
        raise RuntimeError("Se rechazó la raíz del sistema operativo")
    if (
        os.name == "nt"
        and mount_root.drive.casefold() == PROJECT_ROOT.drive.casefold()
    ):
        raise RuntimeError("Se rechazó la unidad donde está el sistema/proyecto")
    return mount_root


def prepare_usb_fixture(raw_mount_path: str | Path) -> list[Path]:
    """Crea archivos ficticios de oficina dentro de una carpeta exclusiva del USB."""
    mount_root = validate_mount_root(raw_mount_path)
    usb_lab = ensure_inside(mount_root / USB_TEST_DIRECTORY, mount_root)
    marker = ensure_inside(usb_lab / USB_MARKER_FILENAME, usb_lab)

    if usb_lab.exists() and not marker.is_file():
        raise RuntimeError(
            f"La carpeta {usb_lab} ya existe sin el marcador esperado; no se modificó"
        )

    usb_lab.mkdir(parents=False, exist_ok=True)
    if marker.exists() and marker.read_text(encoding="utf-8") != USB_MARKER_CONTENT:
        raise RuntimeError("El marcador USB no coincide; no se modificó la carpeta")

    marker.write_text(USB_MARKER_CONTENT, encoding="utf-8")
    fake_files = []
    for filename, builder in USB_FIXTURE_BUILDERS.items():
        fake_file = ensure_inside(usb_lab / filename, usb_lab)
        fake_file.write_bytes(builder())
        fake_files.append(fake_file)
    return fake_files


def run_real_usb_test(raw_mount_path: str | Path) -> dict[str, object]:
    """Prepara y copia solo los archivos ficticios conocidos desde un volumen real."""
    initialize_lab()
    sources = prepare_usb_fixture(raw_mount_path)
    marker = sources[0].parent / USB_MARKER_FILENAME
    if marker.read_text(encoding="utf-8") != USB_MARKER_CONTENT:
        raise RuntimeError("Falta el marcador válido del laboratorio USB")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    destination_root = ensure_inside(RESULTS_ROOT / f"usb-real_{run_id}", RESULTS_ROOT)
    destination_root.mkdir(parents=True, exist_ok=False)
    total_size = 0
    hashes = {}
    for source in sources:
        destination = ensure_inside(destination_root / source.name, destination_root)
        shutil.copyfile(source, destination)
        size = destination.stat().st_size
        digest = sha256_file(destination)
        if digest != sha256_file(source):
            raise RuntimeError(f"La copia no coincide con el original: {source.name}")
        total_size += size
        hashes[source.name] = digest
        append_audit(
            AuditEvent(
                timestamp_utc=utc_now(),
                scenario="usb-real-autorizado",
                action="copia_desde_usb_real_controlado",
                relative_source=f"{USB_TEST_DIRECTORY}/{source.name}",
                relative_destination=str(destination.relative_to(LAB_ROOT)),
                bytes_copied=size,
                sha256=digest,
                result="copiado_y_verificado",
            )
        )
    summary: dict[str, object] = {
        "escenario": "usb-real-autorizado",
        "archivos_copiados": len(sources),
        "bytes_copiados": total_size,
        "hashes_sha256": hashes,
        "resultado_relativo": str(destination_root.relative_to(LAB_ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def run_simulation(control: str) -> dict[str, int | str]:
    if control not in CONTROLS:
        raise ValueError(f"Control desconocido: {control}")
    if not MARKER.is_file():
        raise RuntimeError("Primero ejecute: python3 simulador.py inicializar")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    destination_root = ensure_inside(RESULTS_ROOT / f"{control}_{run_id}", RESULTS_ROOT)
    destination_root.mkdir(parents=True, exist_ok=False)

    files_seen = 0
    files_copied = 0
    bytes_copied = 0

    for source in target_files():
        files_seen += 1
        relative = source.relative_to(FAKE_DRIVE)

        if control == "bloqueo-lectura":
            append_audit(
                AuditEvent(
                    timestamp_utc=utc_now(),
                    scenario=control,
                    action="intento_lectura",
                    relative_source=str(relative),
                    relative_destination=None,
                    bytes_copied=0,
                    sha256=None,
                    result="bloqueado_por_politica_simulada",
                )
            )
            continue

        destination = ensure_inside(destination_root / relative, destination_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        size = destination.stat().st_size
        digest = sha256_file(destination)
        files_copied += 1
        bytes_copied += size
        append_audit(
            AuditEvent(
                timestamp_utc=utc_now(),
                scenario=control,
                action="copia_local_simulada",
                relative_source=str(relative),
                relative_destination=str(destination.relative_to(LAB_ROOT)),
                bytes_copied=size,
                sha256=digest,
                result="copiado",
            )
        )

    summary: dict[str, int | str] = {
        "escenario": control,
        "archivos_detectados": files_seen,
        "archivos_copiados": files_copied,
        "bytes_copiados": bytes_copied,
        "resultado_relativo": str(destination_root.relative_to(LAB_ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def compare() -> None:
    initialize_lab()
    summaries = [run_simulation(control) for control in CONTROLS]
    print("\nRESUMEN COMPARATIVO")
    print("escenario             detectados  copiados  bytes")
    for item in summaries:
        print(
            f"{item['escenario']:<21} "
            f"{item['archivos_detectados']:>10}  "
            f"{item['archivos_copiados']:>8}  "
            f"{item['bytes_copiados']:>5}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulador académico contenido de copia de archivos ficticios"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inicializar", help="crea el disco y los datos ficticios")
    simulate_parser = subparsers.add_parser("simular", help="ejecuta un escenario")
    simulate_parser.add_argument("--control", choices=CONTROLS, required=True)
    subparsers.add_parser("comparar", help="ejecuta los tres escenarios")
    usb_parser = subparsers.add_parser(
        "probar-usb",
        help="crea y copia solo un archivo ficticio desde un volumen autorizado",
    )
    usb_parser.add_argument(
        "--ruta-montaje",
        required=True,
        help="raíz montada del USB (por ejemplo /run/media/usuario/USB o E:\\)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "inicializar":
        initialize_lab()
        print(f"Laboratorio creado en: {LAB_ROOT}")
    elif args.command == "simular":
        run_simulation(args.control)
    elif args.command == "comparar":
        compare()
    elif args.command == "probar-usb":
        run_real_usb_test(args.ruta_montaje)


if __name__ == "__main__":
    main()
