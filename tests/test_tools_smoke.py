import importlib,pytest
MODULES=['yolo_bench','camcheck','ollama_check','sensor_check','motor_check','doctor']
def test_tool_help_parsers():
 for name in MODULES:
  mod=importlib.import_module('scoutbot.tools.'+name)
  with pytest.raises(SystemExit) as exc: mod.parser().parse_args(['--help'])
  assert exc.value.code==0

def test_doctor_runs(capsys):
 from scoutbot.tools import doctor
 rc=doctor.main(['--quiet','--no-camera'])
 out=capsys.readouterr().out
 assert rc==0 and 'Start with' in out
