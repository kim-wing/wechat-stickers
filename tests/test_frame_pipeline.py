"""Offline regression checks; synthetic fixtures do not validate image-model quality."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pipeline', ROOT / 'scripts/run_wechat_sticker_pipeline.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

class FramePipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'job'
        self.parser = pipeline.build_parser()
        self.run_command('init', '--output-dir', str(self.out), '--pack-name', 'test', '--count', '1', '--motion', 'animated')
        self.plan_path = self.out / 'sticker-plan.json'

    def run_command(self, *argv):
        args = self.parser.parse_args(argv)
        args.func(args)

    def test_defaults_need_no_video_secrets_or_keyframes(self):
        plan = pipeline.read_json(self.plan_path)
        self.assertEqual(plan['animated_source_mode'], 'sprite_sheet')
        self.assertIsNone(plan['video_model'])
        self.assertIsNone(plan['video_input_mode'])
        with patch.dict('os.environ', {}, clear=True):
            self.run_command('validate', '--plan', str(self.plan_path), '--require-secrets', '--require-keyframes')
        with self.assertRaises(SystemExit):
            self.run_command('submit-videos', '--plan', str(self.plan_path))

    def test_failed_raw_sheet_records_failure_without_gif(self):
        # Blank sheet is genuinely rejected by the existing image inspector.
        source = Path(self.temp.name) / 'blank.png'
        Image.new('RGB', (400, 400), '#ff00ff').save(source)
        plan = pipeline.read_json(self.plan_path)
        plan['stickers'][0].update(sheet_source_path=str(source), candidate_id='01-candidate-001',
            visual_review={'raw_sheet_ok': True, 'notes': 'Synthetic invalid fixture for failure handling'})
        pipeline.write_json(self.plan_path, plan)
        import subprocess
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_command('process-sheets', '--plan', str(self.plan_path))
        state = pipeline.read_json(self.out / 'run-state.json')
        self.assertEqual(state['stickers']['01']['status'], 'failed')
        self.assertFalse((self.out / 'main/01.gif').exists())
        self.assertFalse(pipeline.read_json(self.out / 'raw/01-candidate-001.inspect.json')['ok'])

    def test_valid_synthetic_sequence_reaches_gif(self):
        # Deterministic encoding fixture only, never a generated-art deliverable.
        from PIL import ImageDraw
        source = Path(self.temp.name) / 'generated_images' / 'fixture' / 'sheet.png'
        source.parent.mkdir(parents=True)
        sheet = Image.new('RGB', (400, 400), '#ff00ff')
        draw = ImageDraw.Draw(sheet)
        for i in range(16):
            x, y = (i % 4) * 100, (i // 4) * 100
            draw.rectangle((x+25, y+25, x+75, y+75), fill='blue')
            draw.rectangle((x+45, y+45, x+48+(i % 2), y+48), fill='white')
        sheet.save(source)
        plan = pipeline.read_json(self.plan_path)
        plan['stickers'][0].update(sheet_source_path=str(source), candidate_id='01-fixture',
            visual_review={'raw_sheet_ok': True, 'notes': 'Synthetic encoding fixture'})
        pipeline.write_json(self.plan_path, plan)
        self.run_command('process-sheets', '--plan', str(self.plan_path))
        with Image.open(self.out / 'main/01.gif') as gif:
            self.assertEqual(gif.size, (240, 240))
            self.assertGreater(gif.n_frames, 1)
            self.assertEqual(gif.info['loop'], 0)
        state = pipeline.read_json(self.out / 'run-state.json')
        self.assertEqual(state['stickers']['01']['status'], 'gif_done')
        self.assertTrue(state['stickers']['01']['playback_review_required'])

    def test_targeted_review_pairs_and_fractional_grid(self):
        spec = importlib.util.spec_from_file_location('pack', ROOT / 'scripts/wechat_sticker_pack.py')
        pack = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pack)
        self.assertEqual(pack.review_pairs({'diff_means': [1, 9, 3, 8]}, 5),
                         [[2, 3], [4, 5], [3, 4], [5, 1]])
        frames = pack.split_grid(Image.new('RGBA', (1254, 1254)), 4, 4)
        self.assertEqual(len(frames), 16)
        self.assertEqual(sum(f.width for f in frames[:4]), 1254)
        self.assertEqual(sum(frames[i].height for i in (0, 4, 8, 12)), 1254)

    def test_package_refuses_missing_outputs(self):
        import subprocess
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_command('package', '--plan', str(self.plan_path))
        self.assertFalse(self.out.with_suffix('.zip').exists())

    def test_mode_lock_rejects_accidental_switch(self):
        plan = pipeline.read_json(self.plan_path)
        plan['animated_source_mode'] = 'green_screen_video'
        pipeline.write_json(self.plan_path, plan)
        with self.assertRaises(SystemExit):
            self.run_command('validate', '--plan', str(self.plan_path))

if __name__ == '__main__':
    unittest.main()
