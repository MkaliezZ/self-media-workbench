"""Real FFmpeg execution; no mocked renderer, no proprietary sample files."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from fixture_tools import fixture_path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from media_render import render
from review_edits import plan_keeps


class PortableRenderTests(unittest.TestCase):
    def test_cut_restore_captions_and_actual_decoding(self):
        review={'duration':4.,'source_sha256':'a'*64,'words':[
            {'id':0,'text':'不保证','start':.2,'end':.8},
            {'id':1,'text':'适用全部','start':2.1,'end':3.0}],
            'caption_groups':[[0],[1]],'candidates':[{'id':'gap','start':1.0,'end':1.7}]}
        lengths=[]
        with tempfile.TemporaryDirectory() as directory:
            for i,selected in enumerate([[],['gap'],[]]):
                out=Path(directory)/str(i);plan=plan_keeps(review,selected)
                result=render(fixture_path(),review,plan,out)
                self.assertEqual(result['words'],2)
                p=out/'reviewed_cut.mp4'
                meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(p)]))
                duration=float(meta['format']['duration']);lengths.append(duration)
                self.assertLess(abs(duration-plan['output_duration']),.13)
                subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True,capture_output=True)
                srt=(out/'reviewed_cut.srt').read_text('utf-8');self.assertIn('不保证',srt)
                words=json.loads((out/'reviewed_cut.words.json').read_text('utf-8'))
                self.assertAlmostEqual(words[1]['start'],2.1-(.7 if selected else 0),places=5)
            self.assertLess(lengths[1],lengths[0]-.5);self.assertAlmostEqual(lengths[0],lengths[2],places=2)


if __name__=='__main__':unittest.main()
