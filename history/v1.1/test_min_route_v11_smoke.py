import json, unittest
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SRC=Path('/mnt/data/design-router-pizarra-mapa-funcional-v1.0.html')
DST=Path('/mnt/data/design-router-pizarra-seleccion-minima-v1.1.html')

def soup(p):return BeautifulSoup(p.read_text(),'html.parser')
class Smoke(unittest.TestCase):
    def test_structure_and_immutability(self):
        doc=soup(DST)
        for i in ['minPanel','minPrimary','minPrereqs','minSupport','minCoverage','minScope','minExport','minRouteData','capabilityPanel']:
            self.assertIsNotNone(doc.find(id=i),i)
        a=json.loads(soup(SRC).find(id='capabilityMapData').string)
        b=json.loads(doc.find(id='capabilityMapData').string)
        self.assertEqual(a,b,'Existing functionality data was modified')
        self.assertEqual(len(a['skills']),47)
        self.assertEqual(len(b['functions']),28)
        self.assertEqual(len(json.loads(doc.find(id='minRouteData').string)['profiles']),8)
    def test_interactive_selection_and_export(self):
        with sync_playwright() as p:
            b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
            pg=b.new_page(viewport={'width':1280,'height':860},accept_downloads=True)
            pg.route('**/*',lambda rt:rt.abort())
            js_errors=[];pg.on('pageerror',lambda e:js_errors.append(str(e)))
            pg.set_content(DST.read_text(),wait_until='commit',timeout=30000)
            self.assertEqual(pg.locator('#minPrimary').locator('.min-owner-name').all_inner_texts(),['G2 · typography-selection-pairing'])
            self.assertIn('Pendiente de revisar',pg.locator('[data-review-owner="G3"]').inner_text())
            pg.get_by_role('button',name='Interlineado',exact=True).click()
            self.assertEqual(pg.locator('#minPrimary').locator('.min-owner-name').all_inner_texts(),['G3 · typography-scales-microtype'])
            self.assertIn('Impeccable',pg.locator('#minSupport').inner_text())
            self.assertIn('ESCRITURA · Sin permiso',pg.locator('#minSupport').inner_text())
            pg.get_by_role('button',name='Tipografía',exact=True).click()
            pg.locator('#minScope').select_option('scenario')
            self.assertEqual(set(pg.locator('#minPrimary').locator('.min-owner-name').all_inner_texts()),{'G2 · typography-selection-pairing','G3 · typography-scales-microtype'})
            pg.locator('#minScope').select_option('function')
            pg.locator('[data-cap="type-micro"]').click()
            self.assertEqual(pg.locator('#minPrimary').locator('.min-owner-name').all_inner_texts(),['G3 · typography-scales-microtype'])
            pg.get_by_role('button',name='Auditoría',exact=True).click()
            self.assertIn('Falta delimitar dominio',pg.locator('#minPrimary').inner_text())
            self.assertEqual(pg.locator('.min-review-row').count(),7)
            pg.locator('#minReviewToggle').click()
            pg.locator('[data-review-owner="G4"] select').select_option('not_applicable')
            self.assertIn('Falta justificar',pg.locator('[data-review-owner="G4"]').inner_text())
            pg.locator('[data-review-owner="G4"] input').fill('No se evalúan colores en esta auditoría focalizada.')
            pg.locator('[data-review-owner="G4"] input').dispatch_event('change')
            self.assertIn('No aplica (propuesto)',pg.locator('[data-review-owner="G4"]').inner_text())
            pg.locator('#minDomain').select_option('G5')
            self.assertIn('G5',pg.locator('#minPrimary').inner_text())
            pg.get_by_role('button',name='Color',exact=True).click()
            self.assertEqual(pg.locator('#minPrimary').locator('.min-owner-name').all_inner_texts(),['G4 · color-theory-palette'])
            with pg.expect_download() as download:
                pg.locator('#minExport').click()
            self.assertIn('seleccion-minima-v1.1',download.value.suggested_filename)
            for view in ['stageMapView','skillNetworkView','proposalBoardView','compareSkillsView','allComparisonsView','capabilityMapView']:
                pg.locator('#'+view).click()
            self.assertTrue(pg.locator('#capabilityPanel').is_visible())
            self.assertEqual(js_errors,[])
            b.close()
    def test_mobile(self):
        with sync_playwright() as p:
            b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
            pg=b.new_page(viewport={'width':320,'height':740});pg.route('**/*',lambda rt:rt.abort());pg.set_content(DST.read_text(),wait_until='commit',timeout=30000)
            pg.get_by_role('button',name='Interlineado',exact=True).click()
            pg.locator('#minReviewToggle').click()
            self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),320)
            self.assertTrue(pg.locator('#minPanel').is_visible())
            b.close()
if __name__=='__main__':unittest.main(verbosity=2)
