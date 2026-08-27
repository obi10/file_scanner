import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import simulador


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.lab = Path(self.temporary_directory.name) / "laboratorio"
        self.fake_drive = self.lab / "disco_externo_ficticio"
        self.results = self.lab / "resultados"
        self.patches = [
            patch.object(simulador, "LAB_ROOT", self.lab),
            patch.object(simulador, "FAKE_DRIVE", self.fake_drive),
            patch.object(simulador, "RESULTS_ROOT", self.results),
            patch.object(simulador, "AUDIT_LOG", self.lab / "auditoria.jsonl"),
            patch.object(simulador, "MARKER", self.lab / ".entorno_simulado"),
        ]
        for active_patch in self.patches:
            active_patch.start()
        simulador.initialize_lab()

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temporary_directory.cleanup()

    def test_no_controls_copies_only_target_extensions(self):
        result = simulador.run_simulation("sin-controles")
        self.assertEqual(result["archivos_detectados"], 7)
        self.assertEqual(result["archivos_copiados"], 7)
        self.assertGreater(result["bytes_copiados"], 0)
        destination_root = self.lab / str(result["resultado_relativo"])
        for source in simulador.target_files():
            destination = destination_root / source.relative_to(self.fake_drive)
            self.assertEqual(
                simulador.sha256_file(source), simulador.sha256_file(destination)
            )

    def test_read_block_copies_nothing(self):
        result = simulador.run_simulation("bloqueo-lectura")
        self.assertEqual(result["archivos_detectados"], 7)
        self.assertEqual(result["archivos_copiados"], 0)
        self.assertEqual(result["bytes_copiados"], 0)

    def test_safety_boundary_rejects_path_outside_parent(self):
        with self.assertRaises(RuntimeError):
            simulador.ensure_inside(self.lab.parent / "fuera.txt", self.lab)

    def test_real_usb_mode_copies_only_its_own_fixture(self):
        mount_root = Path(self.temporary_directory.name) / "usb_montado"
        mount_root.mkdir()
        unrelated = mount_root / "archivo_existente.iso"
        unrelated.write_text("NO TOCAR", encoding="utf-8")

        with patch("simulador.os.path.ismount", return_value=True):
            result = simulador.run_real_usb_test(mount_root)

        self.assertEqual(result["archivos_copiados"], 5)
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "NO TOCAR")
        fixture_root = mount_root / simulador.USB_TEST_DIRECTORY
        self.assertEqual(
            {path.name for path in fixture_root.iterdir() if not path.name.startswith(".")},
            set(simulador.USB_FIXTURE_BUILDERS),
        )

    def test_generated_office_files_have_valid_container_structure(self):
        office_files = {
            "documentos/informe_ficticio.docx": "word/document.xml",
            "hojas/calculo_ficticio.xlsx": "xl/workbook.xml",
            "presentaciones/exposicion_ficticia.pptx": "ppt/presentation.xml",
        }
        for relative_name, required_member in office_files.items():
            with self.subTest(filename=relative_name):
                with ZipFile(self.fake_drive / relative_name) as package:
                    self.assertIsNone(package.testzip())
                    self.assertIn(required_member, package.namelist())
        self.assertTrue(
            (self.fake_drive / "documentos/reporte_ficticio.pdf")
            .read_bytes()
            .startswith(b"%PDF-1.4")
        )

    def test_real_usb_mode_rejects_non_mount_directory(self):
        ordinary_directory = Path(self.temporary_directory.name) / "carpeta_normal"
        ordinary_directory.mkdir()
        with patch("simulador.os.path.ismount", return_value=False):
            with self.assertRaises(RuntimeError):
                simulador.prepare_usb_fixture(ordinary_directory)


if __name__ == "__main__":
    unittest.main()
