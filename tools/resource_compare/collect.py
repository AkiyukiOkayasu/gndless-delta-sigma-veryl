"""同条件のVeryl概算とGowin合成・配置配線結果を保存する。"""
import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
    def handle_data(self,value):
        if value.strip(): self.parts.append(value.strip())

def collect(root, variant):
    stem=f'resource_{variant}'
    project=root/variant/stem
    syn=project/'impl/gwsynthesis'
    pnr=project/'impl/pnr'
    hierarchy=ET.parse(syn/f'{stem}_syn_rsc.xml').getroot()
    def count(name):
        return int(hierarchy.attrib.get('T_'+name,'0').split('(')[0])
    parser=Text()
    parser.feed((pnr/f'{stem}_tr_content.html').read_text())
    text='\n'.join(parser.parts)
    frequency=re.search(r'Max Frequency Summary:.*?([\d.]+)\(MHz\)\n([\d.]+)\(MHz\)',text,re.S)
    assert frequency
    report=(pnr/f'{stem}.rpt.txt').read_text()
    logic=re.search(r'(\d+)\((\d+) LUT, (\d+) ALU',report)
    def endpoints(label):
        return int(re.search(label+r'\n(\d+)',text)[1])
    netlist=(syn/f'{stem}.vg').read_text()
    primitives=Counter(re.findall(r'^\s+([A-Z][A-Z0-9_]*)\s+\\?\S+\s*\(',netlist,re.M))
    dsp=[name for name in primitives if name.startswith(('MULT','DSP','PADD','ALU54'))]
    assert not dsp, dsp
    return dict(variant=variant,synthesis=dict(ff=count('Register'),lut=count('Lut'),alu=count('Alu'),logic=count('Lut')+count('Alu'),dsp=count('Dsp'),bsram=count('Bsram')),pnr=dict(logic=int(logic[1]),lut=int(logic[2]),alu=int(logic[3]),ff=int(re.search(r'Register\s*\|\s*(\d+)/',report)[1]),fmax_mhz=float(frequency[2]),setup_violated_endpoints=endpoints('Numbers of Setup Violated Endpoints'),hold_violated_endpoints=endpoints('Numbers of Hold Violated Endpoints')),netlist_primitives=dict(primitives),source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (project/'src').glob('*.sv')})

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--ternary',type=Path,required=True)
    args=parser.parse_args()
    result=dict(source_revision='b2fa1c926f7ed9e522ad72fe09ca9ca267061f52',veryl_version='0.22.1 (8521c8c 2026-11-04)',veryl={v:json.loads(p.read_text()) for v,p in [('binary',args.binary),('ternary',args.ternary)]},gowin=dict(tool='V1.9.12',device='GW5A-LV25MG121NC1/I0',device_version='A',clock_period_ns=20,input_wrapper_ffs=32,iob_register_packing=False,place_option=1,route_option=2,rows=[collect(args.root,v) for v in ('binary','ternary')]))
    Path(__file__).with_name('results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
