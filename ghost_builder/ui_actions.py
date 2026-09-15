import datetime, queue, secrets, string, threading
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk
from . import ANDROID_API
from .model import ProjectConfig
from .ui_theme import ACCENT, CARD, MUTED, SUCCESS, TEXT, WARNING

class ActionsMixin:
    def _go_tab(self,key):self.tabs.set(self._tab_names[key])
    def _switch_language(self,value):
        new="pl" if value=="PL" else "en"
        if new==self.lang:return
        self.lang=new;self.t.set_language(new);data=self.store.load();data["language"]=new;self.store.save(data)
        for widget,key,kwargs in self._translated:
            try:widget.configure(text=self.t(key,**kwargs))
            except Exception:pass
        for key in self.TABS:
            old=self._tab_names[key];new_name=self.t(f"tab.{key}")
            try:self.tabs.rename(old,new_name);self._tab_names[key]=new_name
            except Exception:pass
        self.refresh_engine_status();self._append_log("info",self.t("msg.language_changed"))
    def _show_welcome(self):
        win=ctk.CTkToplevel(self);win.title(self.t("welcome.title"));win.geometry("620x410");win.resizable(False,False);win.transient(self);win.grab_set();win.configure(fg_color="#071018")
        ctk.CTkLabel(win,text="GHOST",text_color=ACCENT,font=ctk.CTkFont(size=34,weight="bold")).pack(pady=(28,4));self.trw(ctk.CTkLabel(win,text_color=TEXT,font=ctk.CTkFont(size=22,weight="bold")),"welcome.title").pack(pady=(0,8));self.trw(ctk.CTkLabel(win,text_color=MUTED,justify="center",wraplength=530),"welcome.body").pack(padx=34,pady=(0,18));features=ctk.CTkFrame(win,fg_color=CARD,corner_radius=14);features.pack(fill="x",padx=34,pady=8);self.trw(ctk.CTkLabel(features,text_color=TEXT,justify="left",anchor="w",wraplength=510),"welcome.features").pack(fill="x",padx=18,pady=16);row=ctk.CTkFrame(win,fg_color="transparent");row.pack(fill="x",padx=34,pady=(18,0))
        def finish(target,prepare=False):
            data=self.store.load();data["onboarding_done"]=True;data["language"]=self.lang;self.store.save(data);win.grab_release();win.destroy();self._go_tab(target)
            if prepare:self.prepare_engine()
        self.trw(ctk.CTkButton(row,fg_color=ACCENT,text_color="#04100e",command=lambda:finish("engine",True)),"welcome.prepare").pack(side="left",fill="x",expand=True);self.trw(ctk.CTkButton(row,fg_color=CARD,command=lambda:finish("project")),"welcome.start").pack(side="left",fill="x",expand=True,padx=(10,0));win.protocol("WM_DELETE_WINDOW",lambda:finish("home"))
    def _on_close(self):
        try:self.save_config(quiet=True)
        finally:self.destroy()
    def _emit(self,level,message):self.events.put((level,message))
    def _drain_events(self):
        try:
            while True:
                level,msg=self.events.get_nowait()
                if level=="progress" and ":" in msg:
                    try:self.progress.set(max(0,min(1,int(msg.rsplit(":",1)[1])/100)))
                    except ValueError:pass
                elif level=="__engine_done__":self._set_busy(False);self.refresh_engine_status()
                elif level=="__build_success__":self.progress.set(1);self._set_busy(False);self._append_log("success",msg);messagebox.showinfo(self.t("msg.build_complete_title"),self.t("msg.build_complete",path=msg))
                elif level=="__build_error__":self.progress.set(0);self._set_busy(False);self._append_log("error",msg);messagebox.showerror(self.t("msg.build_failed"),msg)
                else:self._append_log(level,msg)
        except queue.Empty:pass
        self.after(80,self._drain_events)
    def _append_log(self,level,message):self.logs.configure(state="normal");self.logs.insert("end",f"[{datetime.datetime.now():%H:%M:%S}] {level.upper():7} {message}\n");self.logs.see("end");self.logs.configure(state="disabled")
    def _set_busy(self,busy,key=None):self._busy=busy;self.build_btn.configure(state="disabled" if busy else "normal",text=self.t(key or "busy.building") if busy else self.t("footer.build"))
    def _copy_logs(self):self.clipboard_clear();self.clipboard_append(self.logs.get("1.0","end").strip());self._append_log("info",self.t("msg.logs_copied"))
    def _clear_logs(self):self.logs.configure(state="normal");self.logs.delete("1.0","end");self.logs.configure(state="disabled")
    def _export_logs(self):
        path=filedialog.asksaveasfilename(defaultextension=".txt",initialfile=f"Ghost-Logs-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt")
        if path:Path(path).write_text(self.logs.get("1.0","end"),encoding="utf-8");self._append_log("success",self.t("msg.logs_exported",path=path))
    @staticmethod
    def _set_entry(entry,value):
        if value:entry.delete(0,"end");entry.insert(0,value)
    def _pick_dir(self,entry):self._set_entry(entry,filedialog.askdirectory())
    def _pick_file(self,entry,kinds):self._set_entry(entry,filedialog.askopenfilename(filetypes=kinds))
    @staticmethod
    def _as_int(value):
        try:return int(value.strip())
        except Exception:return 0
    def _config(self):return ProjectConfig(app_name=self.app_name.get().strip(),package_name=self.package_name.get().strip(),version_name=self.version_name.get().strip(),version_code=self._as_int(self.version_code.get()),min_sdk=self._as_int(self.min_sdk.get()),target_sdk=self._as_int(self.target_sdk.get()),build_mode=self.mode_var.get(),export_format=self.format_var.get(),orientation=self.orientation.get(),fullscreen=self.fullscreen.get(),hardware_accel=self.hardware.get(),allow_backup=self.backup.get(),allow_cleartext=self.cleartext.get(),permission_internet=self.internet.get(),permission_camera=self.camera.get(),permission_location=self.location.get(),permission_microphone=self.microphone.get(),use_splash=self.splash.get(),minify_release=self.minify.get(),signing_enabled=self.signing.get(),keystore_path=self.keystore.get().strip(),key_alias=self.alias.get().strip(),output_dir=self.output_dir.get().strip(),custom_source=self.code.get("1.0","end"),extra_assets=self.assets.get().strip(),icon_path=self.icon_path.get().strip(),deploy_adb=self.adb_deploy.get())
    def analyze_project(self):
        errors=[self.t(f"validation.{x}") for x in self._config().validation_codes()]
        if errors:self.home_project_status.configure(text=self.t("home.project_errors",count=len(errors)),text_color=WARNING,fg_color="#221d12");messagebox.showerror(self.t("msg.project_check"),"\n\n".join(errors));[self._append_log("error",x) for x in errors];return False
        self.home_project_status.configure(text=self.t("home.project_ready"),text_color=SUCCESS,fg_color="#10211d");messagebox.showinfo(self.t("msg.project_check"),self.t("msg.project_ready",api=ANDROID_API));self._append_log("success",self.t("msg.project_passed"));return True
    def save_config(self,quiet=False):
        current=self.store.load();data=self._config().to_persisted_dict();data["language"]=self.lang;data["onboarding_done"]=bool(current.get("onboarding_done",False));self.store.save(data)
        if not quiet:self._append_log("success",self.t("msg.saved",path=self.paths.config))
    def _load_config(self,data):
        entries={"app_name":self.app_name,"package_name":self.package_name,"version_name":self.version_name,"version_code":self.version_code,"output_dir":self.output_dir,"keystore_path":self.keystore,"key_alias":self.alias,"extra_assets":self.assets,"icon_path":self.icon_path,"min_sdk":self.min_sdk,"target_sdk":self.target_sdk}
        for key,widget in entries.items():
            if data.get(key) not in (None,""):self._set_entry(widget,str(data[key]))
        for key,var in {"build_mode":self.mode_var,"export_format":self.format_var,"orientation":self.orientation}.items():
            if key in data:var.set(data[key])
        flags={"permission_internet":self.internet,"permission_camera":self.camera,"permission_location":self.location,"permission_microphone":self.microphone,"allow_cleartext":self.cleartext,"allow_backup":self.backup,"use_splash":self.splash,"fullscreen":self.fullscreen,"hardware_accel":self.hardware,"minify_release":self.minify,"signing_enabled":self.signing,"deploy_adb":self.adb_deploy}
        for key,var in flags.items():
            if key in data:var.set(bool(data[key]))
    def refresh_engine_status(self):
        status,ready=self.toolchain.status(),self.toolchain.ready();self.engine_badge.configure(text=self.t("engine.ready") if ready else self.t("engine.setup"),text_color=SUCCESS if ready else WARNING);self.home_engine_status.configure(text=self.t("home.engine_ready") if ready else self.t("home.engine_missing"),text_color=SUCCESS if ready else WARNING,fg_color="#10211d" if ready else "#221d12");self.engine_text.configure(state="normal");self.engine_text.delete("1.0","end")
        for key,value in status.items():self.engine_text.insert("end",f"{key:25} {value}\n")
        self.engine_text.configure(state="disabled")
    def prepare_engine(self):
        if self._busy or not messagebox.askyesno(self.t("msg.sdk_license_title"),self.t("msg.sdk_license")):return
        self._run_engine(lambda:self.toolchain.provision(accept_android_sdk_license=True),"busy.preparing")
    def repair_engine(self):
        if self._busy or not messagebox.askyesno(self.t("msg.sdk_license_title"),self.t("msg.sdk_license")):return
        self._run_engine(lambda:self.toolchain.repair(accept_android_sdk_license=True),"busy.repairing")
    def _run_engine(self,operation,key):
        self._set_busy(True,key);self._go_tab("logs")
        def worker():
            try:operation();self.events.put(("success",self.t("msg.engine_done")))
            except Exception as exc:self.events.put(("error",str(exc)))
            finally:self.events.put(("__engine_done__",""))
        threading.Thread(target=worker,daemon=True).start()
    def generate_keystore(self):
        if not self.toolchain.keytool_exe():messagebox.showerror(self.t("tab.engine"),self.t("msg.engine_unavailable"));return
        path=filedialog.asksaveasfilename(defaultextension=".jks",filetypes=[("Java Keystore","*.jks")],initialfile="ghost-release.jks")
        if not path:return
        password="".join(secrets.choice(string.ascii_letters+string.digits+"-_") for _ in range(24));alias=self.alias.get().strip() or "ghost_key"
        try:self.builder.generate_keystore(Path(path),password,alias);self._set_entry(self.keystore,path);self._set_entry(self.alias,alias);self._set_entry(self.store_password,password);self._set_entry(self.key_password,password);self.signing.set(True);messagebox.showinfo(self.t("msg.keystore_created_title"),self.t("msg.keystore_created",alias=alias,password=password))
        except Exception as exc:messagebox.showerror(self.t("msg.keystore_error"),str(exc))
    def start_build(self):
        if self._busy:return
        cfg=self._config();errors=[self.t(f"validation.{x}") for x in cfg.validation_codes()]
        if errors:self.home_project_status.configure(text=self.t("home.project_errors",count=len(errors)),text_color=WARNING,fg_color="#221d12");messagebox.showerror(self.t("msg.cannot_build"),"\n\n".join(errors));self._go_tab("project");return
        self.home_project_status.configure(text=self.t("home.project_ready"),text_color=SUCCESS,fg_color="#10211d")
        if not self.toolchain.ready():messagebox.showwarning(self.t("tab.engine"),self.t("msg.engine_not_ready"));self._go_tab("engine");return
        store_pw,key_pw=self.store_password.get(),self.key_password.get();self.save_config(quiet=True);self.progress.set(.08);self._set_busy(True,"busy.building");self._go_tab("logs")
        def worker():
            try:self.events.put(("__build_success__",str(self.builder.build(cfg,store_pw,key_pw))))
            except Exception as exc:self.events.put(("__build_error__",str(exc)))
        threading.Thread(target=worker,daemon=True).start()
