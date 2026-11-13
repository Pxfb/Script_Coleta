"""Instala todas as bibliotecas em .venv; programas opcionais dependem do sistema."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if os.name=='nt' else 'bin/python')


def call(args, **kwargs):
    print(' > '+' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),check=True,**kwargs)


def sistema(ocr=False, java=False):
    if sys.platform.startswith('linux'):
        if not shutil.which('apt-get'): raise ValueError('Instalação automática de programas Linux suporta Debian/Ubuntu (apt-get).')
        prefix = [] if os.geteuid()==0 else ['sudo']
        packages = ([] if not ocr else ['tesseract-ocr','tesseract-ocr-por']) + ([] if not java else ['default-jdk','maven'])
        call(prefix+['apt-get','update']); call(prefix+['apt-get','install','-y']+packages)
    elif sys.platform=='darwin':
        if not shutil.which('brew'): raise ValueError('Instale Homebrew para habilitar OCR/Java automaticamente.')
        packages = ([] if not ocr else ['tesseract','tesseract-lang']) + ([] if not java else ['openjdk','maven'])
        call(['brew','install']+packages)
    elif os.name=='nt':
        if ocr and not shutil.which('tesseract') and not (Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Tesseract-OCR/tesseract.exe').exists():
            if not shutil.which('winget'): raise ValueError('winget não encontrado. Instale Tesseract com o idioma por e execute novamente.')
            call(['winget','install','--id','UB-Mannheim.TesseractOCR','--exact','--silent',
                  '--accept-source-agreements','--accept-package-agreements'])
        if java:
            # Java/Maven can have several vendor-specific installations. Never guess paths.
            if not shutil.which('java') or not shutil.which('mvn'):
                raise ValueError('Para SAFBuilder no Windows, instale JDK e Maven, adicione ambos ao PATH e repita --java. O SAF Python já está disponível.')
    else: raise ValueError('Sistema não suportado para instalação automática de OCR/Java.')


def main(argv=None):
    p=argparse.ArgumentParser(description='Instala dependências de todas as etapas de uma só vez.')
    p.add_argument('--ocr',action='store_true',help='Instala também Tesseract no sistema')
    p.add_argument('--java',action='store_true',help='Prepara e compila o SAFBuilder opcional')
    p.add_argument('--se-necessario',action='store_true',help='Reutiliza ambiente já preparado')
    a=p.parse_args(argv)
    if sys.version_info<(3,12): raise ValueError('Use Python 3.12 ou superior (validado em 3.12).')
    marker=ROOT/'.venv/pronto.json'
    signature=hashlib.sha256((ROOT/'requirements.txt').read_bytes()+(ROOT/'requirements.lock.txt').read_bytes()).hexdigest()
    ready=False
    if a.se_necessario and PYTHON.exists() and marker.exists():
        ready=json.loads(marker.read_text()).get('requirements_sha256')==signature
    if not ready:
        if not PYTHON.exists(): venv.EnvBuilder(with_pip=True).create(ROOT/'.venv')
        call([PYTHON,'-m','pip','install','-r',ROOT/'requirements.txt','-c',ROOT/'requirements.lock.txt'])
        call([PYTHON,'-m','pip','check'])
        call([PYTHON,'-c','import requests, bs4, pdfplumber, fitz, pytesseract, PIL'])
        marker.write_text(json.dumps({'requirements_sha256':signature}),encoding='utf-8')
    if a.java and not (ROOT/'terceiros/SAFBuilder/pom.xml').is_file():
        raise ValueError('Fonte Java não incluída na distribuição pública. Configure safbuilder_jar com um JAR obtido do fornecedor, ou use o motor python.')
    if a.ocr or a.java: sistema(a.ocr,a.java)
    if a.ocr:
        # Local language data avoids writing into Program Files on Windows.
        if os.name=='nt':
            from urllib.request import urlopen
            folder=ROOT/'dados_ocr'; folder.mkdir(exist_ok=True)
            for lang in ('por','eng'):
                target=folder/(lang+'.traineddata')
                if not target.exists():
                    with urlopen('https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/'+lang+'.traineddata',timeout=120) as r:
                        temp=target.with_suffix('.tmp'); temp.write_bytes(r.read()); temp.replace(target)
        env=dict(os.environ)
        if (ROOT/'dados_ocr').is_dir(): env['TESSDATA_PREFIX']=str(ROOT/'dados_ocr')
        call([PYTHON,'-c',"from sophia.pdf import validar_ocr; validar_ocr({'ocr':True,'idioma_ocr':'por'})"],cwd=ROOT,env=env)
    if a.java:
        maven=shutil.which('mvn')
        if not maven or not shutil.which('java'): raise ValueError('Java/Maven não encontrados no PATH; abra um terminal novo e repita --java.')
        call([maven,'-B','package'],cwd=ROOT/'terceiros/SAFBuilder')
    print('Ambiente pronto. Use executar.bat --help ou .venv/bin/python executar.py --help.')
    return 0


if __name__=='__main__':
    try: raise SystemExit(main())
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print('INSTALAÇÃO NÃO CONCLUÍDA: '+str(exc),file=sys.stderr); raise SystemExit(1)
