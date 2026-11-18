import importlib.util,json,os,pathlib,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
BUNDLE=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('team_setup',BUNDLE/'setup.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
PYTHON=pathlib.Path(sys.executable)
UV=pathlib.Path(shutil.which('uv')) if shutil.which('uv') else None
class InstallerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='komiai-team-')
  self.root=pathlib.Path(self.temp.name)
  self.home=self.root/'设计师 A space';self.home.mkdir()
  self.manifest=module.check_bundle(BUNDLE)
 def tearDown(self):self.temp.cleanup()
 def test_payload_integrity_and_tampering(self):
  repo=self.root/'copy';shutil.copytree(BUNDLE.parent,repo);copy=repo/'deploy'
  (copy.parent/'skills/komiai-imagegen/scripts/komiai_image.py').write_text('tampered')
  with self.assertRaisesRegex(RuntimeError,'损坏'):module.check_bundle(copy)
 def test_fresh_install_and_upgrade_preserve_previous_version(self):
  target,backup=module.install_payload(BUNDLE,self.home,PYTHON,self.manifest)
  self.assertIsNone(backup)
  self.assertIn(str(PYTHON),(target/'SKILL.md').read_text())
  (target/'local-note.txt').write_text('retain this old version')
  second,backup=module.install_payload(BUNDLE,self.home,PYTHON,self.manifest)
  self.assertEqual(target,second)
  self.assertEqual((backup/'local-note.txt').read_text(),'retain this old version')
  self.assertFalse((second/'local-note.txt').exists())
  self.assertEqual((second/'scripts/komiai_image.py').read_bytes(),(BUNDLE.parent/'skills/komiai-imagegen/scripts/komiai_image.py').read_bytes())
 def test_failed_replacement_restores_working_install(self):
  target,_=module.install_payload(BUNDLE,self.home,PYTHON,self.manifest)
  (target/'keep.txt').write_text('working')
  rename=pathlib.Path.rename
  def fail_stage(source,destination):
   if source.name=='komiai-imagegen' and source.parent.name.startswith('komiai-install-'):
    raise OSError('injected disk error')
   return rename(source,destination)
  with patch.object(pathlib.Path,'rename',fail_stage):
   with self.assertRaises(OSError):module.install_payload(BUNDLE,self.home,PYTHON,self.manifest)
  self.assertEqual((target/'keep.txt').read_text(),'working')
 def test_foreign_target_and_symlink_are_not_overwritten(self):
  target=self.home/'.agents/skills/komiai-imagegen';target.mkdir(parents=True)
  (target/'SKILL.md').write_text('---\nname: another-skill\n---\nkeep')
  with self.assertRaises(RuntimeError):module.install_payload(BUNDLE,self.home,PYTHON,self.manifest)
  self.assertIn('keep',(target/'SKILL.md').read_text())
  shutil.rmtree(target);target.symlink_to(BUNDLE,target_is_directory=True)
  with self.assertRaises(RuntimeError):module.install_payload(BUNDLE,self.home,PYTHON,self.manifest)
 def test_windows_interpreter_reference(self):
  executable=module.runtime_python(pathlib.Path('C:/Users/Designer/.agents/komiai-runtime/python312'),'win32')
  self.assertEqual(executable.as_posix(),'C:/Users/Designer/.agents/komiai-runtime/python312/Scripts/python.exe')
  target,_=module.install_payload(BUNDLE,self.home,executable,self.manifest)
  self.assertIn(str(executable),(target/'SKILL.md').read_text())
 @unittest.skipUnless(UV is not None and sys.version_info[:2] == (3,12), 'Python 3.12 and uv required for runtime smoke test')
 def test_real_runtime_creation_and_idempotent_setup_without_credentials(self):
  with patch.object(pathlib.Path,'home',return_value=self.home),patch.object(module,'configure_credentials',return_value=True),patch.dict(os.environ,{'UV_CACHE_DIR':str(self.root/'uv-cache')}):
   self.assertEqual(module.main(['--uv',str(UV)]),0)
   self.assertEqual(module.main(['--uv',str(UV)]),0)
  state=json.loads((self.home/'.agents/komiai-install-logs/latest.json').read_text())
  self.assertEqual(state['status'],'ready')
  executable=state['python']
  result=subprocess.run([executable,str(self.home/'.agents/skills/komiai-imagegen/scripts/komiai_image.py'),'--help'],capture_output=True)
  self.assertEqual(result.returncode,0)
 def test_cancelled_key_is_recorded_as_pending(self):
  with patch.object(pathlib.Path,'home',return_value=self.home),patch.object(module,'prepare_runtime',return_value=PYTHON),patch.object(module,'configure_credentials',return_value=False):
   self.assertEqual(module.main(['--uv',str(UV)]),0)
  state=json.loads((self.home/'.agents/komiai-install-logs/latest.json').read_text())
  self.assertEqual(state['status'],'installed_key_pending')
  self.assertNotIn('key',state)
if __name__ == '__main__':
 unittest.main(verbosity=2)
