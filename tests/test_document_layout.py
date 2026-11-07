from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
import core
from auto_scan import same_question


class LayoutTests(unittest.TestCase):
    def test_comparison_table_cells_keep_their_headers(self):
        page=Mock()
        page.get_drawings.return_value=[{'items':['line']*12}]
        table=Mock()
        table.bbox=(0,0,300,300)
        table.extract.return_value=[['Features','Type A','Type B'],['Definition','First definition','Second definition'],['Duration','Ten years','Twenty years']]
        page.find_tables.return_value.tables=[table]
        page.get_text.side_effect=lambda *args,**kwargs: [(0,0,300,300,'flat mixed text',0,0)] if args else 'flat mixed text'
        text=core.extract_page_text(page)
        self.assertIn('Type A\nDefinition: First definition\nDuration: Ten years',text)
        self.assertIn('Type B\nDefinition: Second definition\nDuration: Twenty years',text)
        self.assertNotIn('flat mixed text',text)

    def test_document_index_reused_and_invalidated_by_pdf_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'notes').mkdir()
            pdf=root/'notes'/'sample.pdf'
            pdf.write_bytes(b'first pdf contents')
            page=Mock()
            page.get_drawings.return_value=[]
            page.get_text.return_value='Sample lecture text.'
            document=Mock()
            document.__enter__=Mock(return_value=[page])
            document.__exit__=Mock(return_value=False)
            with patch.object(core,'ROOT',root),patch.object(core,'DATA',root/'data'),patch('pymupdf.open',return_value=document) as opened:
                first=core.load_pages()
                self.assertEqual(core.load_pages(),first)
                self.assertEqual(opened.call_count,1)
                pdf.write_bytes(b'changed pdf contents')
                self.assertNotEqual(core.load_pages()[1],first[1])
                self.assertEqual(opened.call_count,2)

    def test_ocr_word_spacing_can_differ_without_losing_the_question(self):
        self.assertTrue(same_question('Creativity can generate business ideas.','Creativity cangeneratebusinessideas.'))

    def test_ocr_negation_and_decimal_changes_are_not_ignored(self):
        for a,b in [('not able','notable'),('no where','nowhere'),('2.5 percent','25 percent'),('is NOT protected','is protected')]:
            self.assertFalse(same_question(a,b),(a,b))


if __name__=='__main__': unittest.main()
