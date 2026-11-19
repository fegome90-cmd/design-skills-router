"""Pruebas negativas del HTML congelado v1.1. No modifica el original.
Expectativas de integridad semántica y accesibilidad, diseñadas para revelar defectos.
"""
import json
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'design-router-pizarra-seleccion-minima-v1.1.html'
if not SOURCE.exists(): SOURCE=Path('/mnt/data/design-router-pizarra-seleccion-minima-v1.1.html')
HTML=SOURCE.read_text()

class AuditExpectations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        cls.browser=cls.pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()
    def setUp(self):
        self.page=self.browser.new_page(viewport={'width':1280,'height':850},accept_downloads=True)
        self.page.route('**/*',lambda r:r.abort())
        self.page.set_content(HTML,wait_until='commit',timeout=30000)
    def tearDown(self):
        self.page.close()
    def owners(self):
        return self.page.evaluate('window.__minimalRouterPreview.getState().owners')
    def audit(self,scope='function',domain='G2'):
        self.page.locator('[data-route="auditoria"]').first.click()
        self.page.locator('#minScope').select_option(scope)
        self.page.locator('#minDomain').select_option(domain)

    def test_audit_focused_domain_G2_is_represented(self):
        self.audit('function','G2')
        self.assertEqual(self.owners(),['G2'],'Una auditoría tipográfica no puede quedar sin especialista tras elegir G2')

    def test_audit_scenario_does_not_force_motion_specialist(self):
        self.audit('scenario','G5')
        self.assertEqual(self.owners(),['G5'],'Elegir auditoría de layout no debe traer G7 por la lista genérica de funciones')

    def test_export_captures_explicit_audit_domain(self):
        self.audit('function','G2')
        with self.page.expect_download() as d: self.page.locator('#minExport').click()
        data=json.loads(Path(d.value.path()).read_text())
        self.assertEqual(data.get('selected_domain'),'G2','Exportar debe registrar la selección humana aunque no se resuelva el owner')

    def test_export_invalid_nonapplicability_is_explicitly_flagged(self):
        self.page.locator('#minReviewToggle').click()
        self.page.locator('[data-review-owner="G4"] select').select_option('not_applicable')
        with self.page.expect_download() as d: self.page.locator('#minExport').click()
        data=json.loads(Path(d.value.path()).read_text())
        self.assertFalse(data.get('validation',{}).get('valid',True),'Un N/A sin justificación debe exportarse como inválido o bloquear la exportación')

    def test_rebuilding_coverage_preserves_keyboard_focus(self):
        self.page.locator('#minReviewToggle').click()
        s=self.page.locator('[data-review-owner="G4"] select')
        s.focus(); s.select_option('not_applicable')
        focus=self.page.evaluate('document.activeElement?.tagName')
        self.assertIn(focus,{'SELECT','INPUT'},'Cambiar estado no debe dejar el foco en BODY')

if __name__=='__main__':unittest.main(verbosity=2)
