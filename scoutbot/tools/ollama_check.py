import argparse,time,httpx
from scoutbot.settings import load,get
from scoutbot.talk.models import OllamaTalk

def parser():
 p=argparse.ArgumentParser(description='Check, pull, and benchmark configured Ollama model.');p.add_argument('--profile',default='mac');return p
def main(argv=None):
 a=parser().parse_args(argv);cfg=load(a.profile);url=get(cfg,'talk.ollama.url');model=get(cfg,'talk.ollama.model');r=httpx.get(url.rstrip('/')+'/api/tags',timeout=5);r.raise_for_status();names=[x.get('name','') for x in r.json().get('models',[])]
 if not any(model in n for n in names):
  print('Pulling',model);httpx.post(url.rstrip('/')+'/api/pull',json={'name':model,'stream':False},timeout=600).raise_for_status()
 talk=OllamaTalk(url,model);t=time.monotonic();reply=talk.reply([], 'No hazards.');print(f'PASS reply in {time.monotonic()-t:.2f}s: {reply}');t=time.monotonic()
 try: talk.triage_facts([], 'No hazards.',None);print(f'PASS JSON triage in {time.monotonic()-t:.2f}s')
 except Exception as e: print('FAIL JSON triage:',e)
if __name__=='__main__':main()
