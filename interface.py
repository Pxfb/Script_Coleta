"""Interface desktop para acompanhar a atualização e guardar os pacotes SAF."""
import csv
import json
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent


class Interface(tk.Tk):
    def __init__(self):
        super().__init__()
        brand_file = ROOT / 'assets' / 'marca.json'
        self.brand = json.loads(brand_file.read_text(encoding='utf-8')) if brand_file.exists() else {'nome': 'SophiaFluxo'}
        self.title(self.brand['nome'])
        self.geometry('1220x880')
        self.minsize(1000, 760)
        self.configure(background='#f3f6f4')
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background='#f3f6f4', foreground='#243b30')
        style.configure('TButton', padding=(14, 9), borderwidth=0)
        style.configure('Primary.TButton', background='#287344', foreground='white')
        style.map('Primary.TButton', background=[('active', '#1d5d35'), ('disabled', '#91ad9b')])
        style.configure('TNotebook.Tab', padding=(24, 12))
        style.map('TNotebook.Tab', background=[('selected', '#e0eee3')], foreground=[('selected', '#18552c')])
        style.configure('Treeview', rowheight=32, fieldbackground='white', background='white', borderwidth=0)
        style.configure('Treeview.Heading', background='#e8eeea', padding=8, font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#d6eadd')], foreground=[('selected', '#173d25')])
        self.events = queue.Queue()
        self.running = False
        self.action_buttons = []
        self.rows = {}
        self.searches = {}
        self.cards = {}
        self.last_folders = {}
        self.config_path = tk.StringVar(value=str(ROOT / 'config.json'))
        self.since = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.size = tk.StringVar(value='95')
        self.limit = tk.StringVar(value='')
        self.status = tk.StringVar(value='Comece por Configurar projeto e depois consulte o catálogo.')
        header = ttk.Frame(self, padding=(24, 18))
        header.pack(fill='x')
        logo = ROOT / 'assets' / self.brand.get('logo', 'logo.png')
        if logo.is_file():
            from PIL import Image, ImageTk
            picture = Image.open(logo).convert('RGBA')
            picture.thumbnail((160, 75))
            self.logo = ImageTk.PhotoImage(picture)
            ttk.Label(header, image=self.logo).pack(side='left', padx=(0, 22))
        title = ttk.Frame(header)
        title.pack(side='left')
        ttk.Label(title, text=self.brand['nome'], font=('Segoe UI', 25, 'bold')).pack(anchor='w')
        ttk.Label(title, text='Acompanhe o acervo e prepare os pacotes de importação', foreground='#62776a').pack(anchor='w', pady=4)
        ttk.Button(header, text='Configurar projeto', command=self.edit_config).pack(side='right')
        tk.Frame(self, background='#bd4848', height=3).pack(fill='x', padx=24)
        settings = ttk.Frame(self, padding=(24, 12))
        settings.pack(fill='x')
        settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text='Configuração atual').grid(row=0, column=0, sticky='w')
        ttk.Entry(settings, textvariable=self.config_path).grid(row=0, column=1, sticky='ew', padx=10)
        ttk.Button(settings, text='Abrir JSON', command=self.choose_config).grid(row=0, column=2)
        options = ttk.Frame(settings)
        options.grid(row=1, column=0, columnspan=3, sticky='w', pady=(10, 0))
        for i, (label, variable, width) in enumerate([
            ('Novas aquisições desde (AAAA-MM-DD)', self.since, 13),
            ('MiB por ZIP', self.size, 7), ('Limite de itens (vazio = todos)', self.limit, 8)
        ]):
            ttk.Label(options, text=label).grid(row=0, column=i*2, padx=(0, 8))
            ttk.Entry(options, textvariable=variable, width=width).grid(row=0, column=i*2+1, padx=(0, 20))
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True, padx=24)
        self.views = {}
        for key, title in [('recentes', 'Novas aquisições'), ('pendentes', 'Acervo geral')]:
            page = ttk.Frame(self.tabs, padding=14)
            self.tabs.add(page, text=title)
            self.rows[key] = []
            metrics = ttk.Frame(page)
            metrics.pack(fill='x')
            self.cards[key] = []
            for label in ('Nesta lista', 'Ausentes da base', 'A processar para SAF', 'Sem PDF registrados'):
                box = tk.Frame(metrics, background='white', padx=16, pady=9)
                box.pack(side='left', fill='x', expand=True, padx=4)
                number = tk.StringVar(value='—')
                tk.Label(box, textvariable=number, background='white', foreground='#287344', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
                tk.Label(box, text=label, background='white', foreground='#5b6f62', font=('Segoe UI', 10)).pack(anchor='w')
                self.cards[key].append(number)
            ttk.Label(page, text='Contagens da consulta carregada. Ausente da base pode já ter SAF no histórico local.', foreground='#62776a').pack(anchor='w', pady=8)
            actions = ttk.Frame(page)
            actions.pack(fill='x', pady=(0, 10))
            for label, callback, primary in [
                ('Consultar catálogo', lambda k=key: self.start(k, False), False),
                ('Gerar ZIPs dos pendentes', lambda k=key: self.start(k, True), True),
                ('Ver relatório', lambda k=key: self.open_report(k), False),
            ]:
                button = ttk.Button(actions, text=label, command=callback, style='Primary.TButton' if primary else 'TButton')
                button.pack(side='left', padx=(0, 8))
                self.action_buttons.append(button)
            search = tk.StringVar()
            self.searches[key] = search
            ttk.Label(actions, text='Buscar').pack(side='left', padx=(10, 5))
            ttk.Entry(actions, textvariable=search, width=22).pack(side='left', fill='x', expand=True)
            search.trace_add('write', lambda *args, k=key: self.filter_rows(k))
            table = ttk.Frame(page)
            table.pack(fill='both', expand=True)
            tree = ttk.Treeview(table, columns=('codigo', 'titulo', 'base', 'verificacao'), show='headings', height=7)
            for column, label, width in [('codigo','Código',80),('titulo','Título',440),('base','Ausente da base',130),('verificacao','Situação',220)]:
                tree.heading(column, text=label, command=lambda c=column, k=key: self.sort_rows(k,c))
                tree.column(column, width=width, minwidth=60)
            scrollbar = ttk.Scrollbar(table, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side='right', fill='y')
            tree.pack(fill='both', expand=True)
            tree.tag_configure('even', background='#f4f8f5')
            tree.bind('<Double-1>', lambda event, k=key: self.item_details(k))
            files = ttk.Frame(page)
            files.pack(fill='x', pady=(10, 0))
            ttk.Label(files, text='ZIPs desta seleção', font=('Segoe UI', 11, 'bold')).pack(side='left')
            ttk.Button(files, text='Carregar anteriores', command=lambda k=key: self.load_packages(k)).pack(side='right')
            ttk.Button(files, text='Salvar ZIP…', command=lambda k=key: self.save_zip(k)).pack(side='right', padx=8)
            packages = tk.Listbox(page, height=3, background='white', foreground='#243b30', relief='flat', selectbackground='#d6eadd', font=('Segoe UI', 10))
            packages.pack(fill='x', pady=5)
            self.views[key] = (tree, packages)
        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.pack(fill='x', padx=24, pady=(10, 0))
        self.log = tk.Text(self, height=4, wrap='word', state='disabled', background='#edf2ee', foreground='#3f5849', relief='flat', font=('Consolas', 9))
        self.log.pack(fill='x', padx=24, pady=6)
        ttk.Label(self, textvariable=self.status, padding=(24, 8), wraplength=1120).pack(fill='x')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(150, self.poll)

    def edit_config(self):
        if self.running:
            messagebox.showinfo('Execução em andamento', 'Aguarde a conclusão para alterar a configuração.')
            return
        path = Path(self.config_path.get()).resolve()
        try:
            source = path if path.exists() else ROOT / 'config.exemplo.json'
            data = json.loads(source.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            messagebox.showerror('Configuração', str(exc))
            return
        window = tk.Toplevel(self)
        window.title('Configurar projeto')
        window.geometry('740x300')
        window.transient(self)
        window.grab_set()
        fields = {}
        for i, (key, label) in enumerate([('url_base', 'Endereço do catálogo'), ('base', 'CSV de base (opcional)'), ('saida', 'Pasta de saída e histórico')]):
            variable = tk.StringVar(value=data.get(key) or '')
            fields[key] = variable
            ttk.Label(window, text=label).grid(row=i, column=0, padx=12, pady=14, sticky='w')
            ttk.Entry(window, textvariable=variable, width=58).grid(row=i, column=1, padx=8)
            if key != 'url_base':
                def browse(k=key, v=variable):
                    chosen = filedialog.askdirectory(parent=window) if k == 'saida' else filedialog.askopenfilename(parent=window, filetypes=[('CSV', '*.csv')])
                    if chosen: v.set(chosen)
                ttk.Button(window, text='Escolher', command=browse).grid(row=i, column=2)
        ttk.Label(window, text='Caminhos relativos usam a pasta do JSON. Preserve a saída para manter o histórico.', wraplength=650).grid(row=3, column=0, columnspan=3, padx=12)
        def save():
            from urllib.parse import urlparse
            url = fields['url_base'].get().strip()
            if urlparse(url).scheme not in ('http', 'https') or not urlparse(url).netloc or not fields['saida'].get().strip():
                messagebox.showerror('Configuração', 'Informe uma URL HTTP(S) e a pasta de saída.', parent=window)
                return
            data.update({key: value.get().strip() or None for key, value in fields.items()})
            try:
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            except OSError as exc:
                messagebox.showerror('Configuração', str(exc), parent=window)
                return
            self.status.set('Configuração salva. Consulte o catálogo para atualizar a tela.')
            window.destroy()
        ttk.Button(window, text='Salvar configuração', command=save, style='Primary.TButton').grid(row=4, column=1, pady=18, sticky='e')

    def filter_rows(self, selection):
        tree = self.views[selection][0]
        tree.delete(*tree.get_children())
        query = self.searches[selection].get().casefold()
        for i, values in enumerate(self.rows[selection]):
            if query in ' '.join(map(str, values)).casefold():
                tree.insert('', 'end', values=values, tags=('even',) if i % 2 == 0 else ())

    def sort_rows(self, selection, column):
        index = ('codigo', 'titulo', 'base', 'verificacao').index(column)
        self.rows[selection].sort(key=lambda row: int(row[0]) if index == 0 else str(row[index]).casefold())
        self.filter_rows(selection)

    def item_details(self, selection):
        tree = self.views[selection][0]
        if tree.selection():
            values = tree.item(tree.selection()[0], 'values')
            messagebox.showinfo('Detalhes do item', '\n\n'.join(f'{label}: {value}' for label, value in zip(('Código', 'Título', 'Ausente da base', 'Situação'), values)))

    def open_report(self, selection):
        import webbrowser
        folder = self.last_folders.get(selection)
        if folder and (folder / 'relatorio.html').exists():
            webbrowser.open((folder / 'relatorio.html').resolve().as_uri())
        else:
            messagebox.showinfo('Relatório', 'Consulte o catálogo ou carregue as execuções anteriores primeiro.')

    def update_counts(self, selection):
        rows = self.rows[selection]
        completed = {'Presente na base', 'Cadastro confirmado', 'SAF já gerado', 'Sem PDF — ignorado'}
        counts = [len(rows), sum(row[2] == 'sim' for row in rows),
                  sum(row[2] == 'sim' and row[3] not in completed for row in rows),
                  sum(row[3] == 'Sem PDF — ignorado' for row in rows)]
        for variable, value in zip(self.cards[selection], counts):
            variable.set(str(value))

    def choose_config(self):
        path=filedialog.askopenfilename(filetypes=[('Configuração JSON','*.json')])
        if path:self.config_path.set(path)

    def start(self, selection, process):
        if self.running:
            messagebox.showinfo('Execução em andamento','Aguarde a execução atual terminar.');return
        try:
            config=Path(self.config_path.get()).resolve()
            data=json.loads(config.read_text(encoding='utf-8-sig'))
            since=date.fromisoformat(self.since.get()).isoformat() if selection == 'recentes' else None
            size=float(self.size.get())
            import math
            if not math.isfinite(size) or size<=0:raise ValueError('Informe um limite de ZIP positivo.')
            output=(config.parent/data.get('saida','saida')).resolve()
            # A consulta visual sempre usa o catálogo. A lista XML configurada é substituída somente nesta cópia.
            data['xml']=None
            data['desde']=since
            data['selecao']=selection
            data['saf']=process
            data['lote_mb']=size
            data['limite']=int(self.limit.get()) if self.limit.get().strip() else None
            if data['limite'] is not None and data['limite'] < 1: raise ValueError('O limite de itens deve ser positivo.')
            for key in ('base','saida','safbuilder_jar'):
                if data.get(key):data[key]=str((config.parent/data[key]).resolve())
            output.mkdir(parents=True,exist_ok=True)
            import uuid
            snapshot=output/('interface_config_'+uuid.uuid4().hex+'.json')
            snapshot.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            before=set((output/'execucoes').glob('*'))
        except Exception as exc:
            messagebox.showerror('Confira a configuração',str(exc));return
        self.running=True
        self.progress.start(15)
        for button in self.action_buttons: button.state(['disabled'])
        self.status.set('Executando. O progresso aparece abaixo.')
        script='executar.py' if process else '01_verificar.py'
        def worker():
            try:
                command=[sys.executable,'-u',str(ROOT/script),'--config',str(snapshot)]
                with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace') as child:
                    for line in child.stdout:self.events.put(('log',line))
                    code=child.wait()
                folders=sorted(set((output/'execucoes').glob('*'))-before)
                self.events.put(('done',(selection,output,folders,code)))
            except Exception as exc:self.events.put(('error',str(exc)))
            finally: snapshot.unlink(missing_ok=True)
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='log':
                    self.log.configure(state='normal');self.log.insert('end',value);self.log.see('end');self.log.configure(state='disabled')
                elif kind=='error':
                    self.running=False;self.status.set(value)
                    self.progress.stop()
                    for button in self.action_buttons: button.state(['!disabled'])
                else:
                    self.running=False
                    self.progress.stop()
                    for button in self.action_buttons: button.state(['!disabled'])
                    selection,output,folders,code=value
                    tree,packages=self.views[selection]
                    for folder in folders:
                        summary=folder/'resumo.json'
                        if not summary.exists():continue
                        self.last_folders[selection] = folder
                        result=json.loads(summary.read_text(encoding='utf-8'))
                        for stage in result.get('etapas',[]):
                            if stage.get('etapa')=='verificação':
                                path=Path(stage['pasta'])/('ultimas_aquisicoes.csv' if selection=='recentes' else 'pendentes.csv')
                                tree.delete(*tree.get_children())
                                with path.open(encoding='utf-8-sig',newline='') as f:
                                    control_path = output / 'controle.json'
                                    control = json.loads(control_path.read_text(encoding='utf-8')).get('itens', {}) if control_path.exists() else {}
                                    for row in csv.DictReader(f):
                                        entry = control.get(row['codigo'], {})
                                        situation = row.get('verificacao', '')
                                        checkpoint = output / 'coleta' / (row['codigo'] + '.json')
                                        if row.get('ausente_base') == 'não':
                                            situation = 'Presente na base'
                                        elif entry.get('cadastrado'):
                                            situation = 'Cadastro confirmado'
                                        elif entry.get('saf_gerado'):
                                            situation = 'SAF já gerado'
                                        elif checkpoint.exists() and json.loads(checkpoint.read_text(encoding='utf-8')).get('status') == 'sem_pdf':
                                            situation = 'Sem PDF — ignorado'
                                        elif entry.get('metadados_concluidos'):
                                            situation = 'Metadados concluídos'
                                        tree.insert('', 'end', values=(row['codigo'], row.get('titulo', ''), row.get('ausente_base', ''), situation))
                        for path in sorted((folder/'saf').glob('*.zip'))+sorted((folder/'saf/lotes').glob('*.zip')):packages.insert('end',str(path))
                    self.rows[selection] = [tree.item(item, 'values') for item in tree.get_children()]
                    self.update_counts(selection)
                    self.filter_rows(selection)
                    self.status.set(f'Execução finalizada, código {code}. 0 = concluído; 2 = revisar avisos; 1 = falha. Arquivos em {output}')
        except queue.Empty:pass
        except Exception as exc:self.status.set('Falha ao ler o relatório: '+str(exc))
        self.after(150,self.poll)

    def load_packages(self, selection):
        try:
            config = Path(self.config_path.get()).resolve()
            data = json.loads(config.read_text(encoding='utf-8-sig'))
            output = (config.parent / data.get('saida', 'saida')).resolve()
            packages = self.views[selection][1]
            packages.delete(0, 'end')
            for summary in sorted((output / 'execucoes').glob('*/resumo.json')):
                result = json.loads(summary.read_text(encoding='utf-8'))
                matches = any(
                    stage.get('etapa') == 'verificação'
                    and Path(stage.get('xml_selecionado', '')).name == selection + '_para_coletar.xml'
                    for stage in result.get('etapas', [])
                )
                if matches:
                    self.last_folders[selection] = summary.parent
                    folder = summary.parent / 'saf'
                    for path in sorted(folder.glob('*.zip')) + sorted((folder / 'lotes').glob('*.zip')):
                        packages.insert('end', str(path))
        except (OSError, ValueError) as exc:
            messagebox.showerror('Não foi possível carregar os pacotes', str(exc))

    def save_zip(self,selection):
        box=self.views[selection][1]
        if not box.curselection():
            messagebox.showinfo('Salvar ZIP', 'Selecione um pacote na lista primeiro.')
            return
        source=Path(box.get(box.curselection()[0]))
        target=filedialog.asksaveasfilename(initialfile=source.name,defaultextension='.zip',filetypes=[('Pacote SAF','*.zip')])
        if target:
            try:
                if Path(target).resolve()!=source.resolve():shutil.copy2(source,target)
            except OSError as exc:messagebox.showerror('Não foi possível salvar',str(exc))

    def close(self):
        if self.running:
            messagebox.showinfo('Execução em andamento','Aguarde a conclusão para fechar a interface.');return
        self.destroy()


if __name__=='__main__':
    Interface().mainloop()
