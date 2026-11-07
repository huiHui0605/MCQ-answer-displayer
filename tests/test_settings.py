import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import settings


class SettingsTests(unittest.TestCase):
    def test_settings_survive_restart_without_screen_or_question_text(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(settings,'PATH',Path(directory)/'settings.json'):
            saved={'region':settings.make_region((1000,1600,3),(900,800),(100,100)),'model':'qwen2.5:7b'}
            settings.save_settings(saved)
            self.assertEqual(settings.load_settings(),saved)
            self.assertEqual(settings.preferred_model(saved),'qwen2.5:7b')
            self.assertEqual(set(saved['region']),{'screen','rect'})

    def test_resolution_change_requires_reselection(self):
        region=settings.make_region((1000,1600,3),(100,100),(900,800))
        with self.assertRaisesRegex(ValueError,'分辨率'):
            settings.apply_region(np.zeros((900,1600,3),dtype=np.uint8),region)

    def test_cropped_coordinates_and_small_area_validation(self):
        image=np.zeros((1000,1600,3),dtype=np.uint8)
        region=settings.make_region(image.shape,(900,800),(100,100))
        self.assertEqual(settings.apply_region(image,region).shape,(700,800,3))
        with self.assertRaises(ValueError): settings.make_region(image.shape,(0,0),(5,5))

    def test_bad_settings_and_nonlocal_models(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(settings,'PATH',Path(directory)/'settings.json'):
            settings.PATH.write_text('not JSON')
            self.assertEqual(settings.load_settings(),{})
            settings.PATH.write_text('[]')
            self.assertEqual(settings.load_settings(),{})
        with self.assertRaises(ValueError): settings.preferred_model({'model':'test:cloud'})


if __name__=='__main__': unittest.main()
