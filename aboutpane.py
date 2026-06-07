#!/usr/bin/env python3
"""
aboutpane — macOS-style About This System window
GTK4 + Libadwaita. Hook into Logo Menu's "About My System" action.

Install:
  sudo cp aboutpane /usr/local/bin/aboutpane
  sudo chmod +x /usr/local/bin/aboutpane
  sudo cp aboutpane.desktop /usr/share/applications/
  sudo update-desktop-database /usr/share/applications/
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
import subprocess, platform

# ── System info ──────────────────────────────────────────────────────────────

def read_file(path, fallback='Unknown'):
    try:
        with open(path) as f: return f.read().strip()
    except: return fallback

def get_os_pretty_name():
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    return line.split('=', 1)[1].strip().strip('"')
    except: pass
    return platform.system()

def get_chip():
    try:
        import re
        cpu_name = ''
        cpu_cores = 0
        with open('/proc/cpuinfo') as f:
            for line in f:
                if line.startswith('model name') and not cpu_name:
                    cpu_name = line.split(':', 1)[1].strip()
                if line.startswith('processor'):
                    cpu_cores += 1
        if cpu_name:
            cpu_name = re.sub(r'\s+@\s+[\d.]+\s*GHz', '', cpu_name)
            cpu_name = cpu_name.replace('(R)', '®').replace('(TM)', '™')
            cpu_name = re.sub(r'\s+', ' ', cpu_name).strip()
            if cpu_cores > 0:
                cpu_name = f'{cpu_name} × {cpu_cores}'
            return cpu_name
    except: pass
    return platform.processor() or 'Unknown'

def get_gpu():
    import re, glob

    try:
        for card in sorted(glob.glob('/sys/class/drm/card[0-9]*')):
            try:
                uevent = open(f'{card}/device/uevent').read()
                driver = ''
                pci_id = ''
                for line in uevent.splitlines():
                    if line.startswith('DRIVER='):
                        driver = line.split('=',1)[1].strip().lower()
                    if line.startswith('PCI_ID='):
                        pci_id = line.split('=',1)[1].strip().lower().replace(':','')

                if not driver or not pci_id:
                    continue

                # Look up PCI ID in hwdata
                vendor_id = pci_id[:4]
                device_id = pci_id[4:]
                pci_name = ''
                try:
                    in_vendor = False
                    with open('/usr/share/hwdata/pci.ids') as f:
                        for line in f:
                            if line.startswith(vendor_id):
                                in_vendor = True
                                continue
                            if in_vendor:
                                if line.startswith('	') and not line.startswith('		'):
                                    if line.strip().startswith(device_id):
                                        pci_name = line.strip()[len(device_id):].strip()
                                        break
                                elif not line.startswith('	') and not line.startswith('#'):
                                    break
                except: pass

                if driver == 'i915':
                    if pci_name:
                        # Extract bracket tag e.g. [UHD Graphics], [Iris Xe]
                        bracket = re.search(r'\[([^\]]+)\]', pci_name)
                        # Extract ADL/TGL/RPL etc codename
                        codename_map = {'Alder':'ADL','Tiger':'TGL','Raptor':'RPL','Meteor':'MTL','Ice':'ICL','Comet':'CML','Kaby':'KBL','Skylake':'SKL','Broadwell':'BDW'}
                        abbr = next((v for k,v in codename_map.items() if k.lower() in pci_name.lower()), None)
                        gt = re.search(r'(GT\d)', pci_name, re.IGNORECASE)
                        suffix = f' ({abbr} {gt.group(1)})' if abbr and gt else (f' ({abbr})' if abbr else '')
                        brand = bracket.group(1) if bracket else 'Graphics'
                        return f'Intel® {brand}{suffix}'
                    return 'Intel® Graphics'

                elif driver == 'amdgpu':
                    if pci_name:
                        bracket = re.search(r'\[([^\]]+)\]', pci_name)
                        brand = bracket.group(1) if bracket else 'Radeon™ Graphics'
                        return f'AMD {brand}'
                    return 'AMD Radeon™ Graphics'

                elif driver in ('nvidia', 'nouveau'):
                    if pci_name:
                        bracket = re.search(r'\[([^\]]+)\]', pci_name)
                        brand = bracket.group(1) if bracket else 'Graphics'
                        return f'NVIDIA® {brand}'
                    return 'NVIDIA® Graphics'

            except: pass
    except: pass

    # Fallback: lspci
    try:
        r = subprocess.run(['lspci'], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if any(k in line.upper() for k in ('VGA', '3D', 'DISPLAY')):
                name = line.split(':', 2)[-1].strip()
                name = re.sub(r'\s*\(rev [0-9a-f]+\)', '', name)
                name = name.replace('(R)', '®').replace('(TM)', '™')
                return name.strip()
    except: pass
    return 'Unknown'

def get_memory_detail():
    total_gb = 'Unknown'
    speed = ''
    mem_type = ''

    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    total_gb = f'{round(int(line.split()[1]) / 1024 / 1024)} GB'
                    break
    except: pass

    try:
        r = subprocess.run(['sudo', 'dmidecode', '-t', 'memory'],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith('Speed:') and 'Unknown' not in line and not speed:
                val = line.split(':', 1)[1].strip()
                if 'MT/s' in val or 'MHz' in val:
                    speed = val.replace('MT/s', 'MHz')
            if line.startswith('Type:') and 'Unknown' not in line and not mem_type:
                val = line.split(':', 1)[1].strip()
                if val and val not in ('Other', 'Unknown'):
                    mem_type = val
    except: pass

    parts = [total_gb]
    if speed: parts.append(speed)
    if mem_type: parts.append(mem_type)
    return ' '.join(parts)

def get_product_name():
    try:
        result = subprocess.run(['hostnamectl', '--pretty'], capture_output=True, text=True)
        pretty = result.stdout.strip()
        if pretty: return pretty
    except: pass
    name = read_file('/sys/class/dmi/id/product_name', '')
    version = read_file('/sys/class/dmi/id/product_version', '')
    bad = ('Unknown', 'To Be Filled By O.E.M.', 'System Product Name', 'None', '')
    if name and name not in bad:
        if version and version not in bad:
            # Lenovo puts e.g. "82RJ" in product_name and "IdeaPad 3 14IAU7" in version
            # — prefer whichever looks more human-readable (contains a space)
            candidates = [s for s in (name, version) if ' ' in s]
            if candidates:
                # Strip trailing model suffix like "14IAU7", "15ITL6" etc.
                import re
                best = max(candidates, key=len)
                best = re.sub(r'\s+\d{2}[A-Z]{2,5}\d?\s*$', '', best).strip()
                return best
            return name
        return name
    return platform.node()


def get_serial():
    s = read_file('/sys/class/dmi/id/product_serial', '')
    return s if s and s not in ('Unknown', 'To Be Filled By O.E.M.', 'None', '') else None

def get_chassis_icon():
    chassis = read_file('/sys/class/dmi/id/chassis_type', '3').strip()
    return 'computer-laptop' if chassis in ('8', '9', '10', '14') else 'computer'

# ── Window ───────────────────────────────────────────────────────────────────

class AboutPane(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title('About This System')
        self.set_default_size(400, -1)
        self.set_resizable(False)
        self.set_hide_on_close(True)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        header = Adw.HeaderBar()
        header.set_show_title(False)
        header.add_css_class('flat')
        root.append(header)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            margin_start=24, margin_end=24, margin_bottom=0,
        )
        root.append(content)

        # Device illustration
        icon_img = Gtk.Image.new_from_icon_name(get_chassis_icon())
        icon_img.set_pixel_size(192)
        icon_img.set_margin_bottom(16)
        icon_img.set_margin_top(12)
        icon_img.add_css_class('dim-label')
        content.append(icon_img)

        # Device name
        name_lbl = Gtk.Label(label=get_product_name())
        name_lbl.add_css_class('title-1')
        name_lbl.set_wrap(True)
        name_lbl.set_justify(Gtk.Justification.CENTER)
        name_lbl.set_margin_bottom(4)
        content.append(name_lbl)

        # OS name
        os_lbl = Gtk.Label()
        os_lbl.set_markup(f'<small>{GLib.markup_escape_text(get_os_pretty_name())}</small>')
        os_lbl.add_css_class('dim-label')
        os_lbl.set_margin_bottom(24)
        content.append(os_lbl)

        # Info card
        card = Gtk.ListBox()
        card.add_css_class('boxed-list')
        card.set_selection_mode(Gtk.SelectionMode.NONE)
        card.set_margin_bottom(24)
        content.append(card)

        rows = [('Processor', get_chip()), ('Graphics', get_gpu()), ('Memory', get_memory_detail()), ('Kernel', platform.release())]
        serial = get_serial()
        if serial: rows.append(('Serial Number', serial))

        for label, value in rows:
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(12)
            box.set_margin_end(12)
            lbl_top = Gtk.Label(label=label)
            lbl_top.add_css_class('caption')
            lbl_top.add_css_class('dim-label')
            lbl_top.set_halign(Gtk.Align.START)
            lbl_val = Gtk.Label(label=value)
            lbl_val.set_halign(Gtk.Align.START)
            lbl_val.set_selectable(True)
            lbl_val.set_wrap(True)
            box.append(lbl_top)
            box.append(lbl_val)
            row.set_child(box)
            card.append(row)

        # More Info button
        btn = Gtk.Button(label='More Info…')
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect('clicked', self._on_more_info)
        content.append(btn)

        # Copyright
        copy_lbl = Gtk.Label()
        copy_lbl.set_markup('<small>© The GNOME Project and Contributors&#10;Licensed under the GNU General Public License</small>')
        copy_lbl.add_css_class('dim-label')
        copy_lbl.set_justify(Gtk.Justification.CENTER)
        copy_lbl.set_margin_top(24)
        copy_lbl.set_margin_bottom(42)
        content.append(copy_lbl)

    def _on_more_info(self, btn):
        try:
            subprocess.Popen(['gnome-control-center', 'system', 'about'])
            self.hide()
        except FileNotFoundError:
            try:
                subprocess.Popen(['gnome-control-center'])
                self.hide()
            except: pass

# ── App ──────────────────────────────────────────────────────────────────────

class AboutPaneApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='aboutpane',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect('activate', self._on_activate)
        self._win = None

    def _on_activate(self, app):
        if self._win is None:
            self._win = AboutPane(app)
            self._win.connect('hide', lambda w: self.quit())
        self._win.present()

if __name__ == '__main__':
    import sys, socket, threading, signal

    LOCK_ADDR = '\0aboutpane-single'
    server = None

    def _listen_for_raise(app, server):
        """Background thread: accept a connection = raise window."""
        while True:
            try:
                conn, _ = server.accept()
                conn.close()
                # Schedule present() on the main GTK thread
                GLib.idle_add(lambda: app._win and app._win.present())
            except OSError:
                break

    # Try to become the server (first instance)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(LOCK_ADDR)
        server.listen(1)
    except OSError:
        # Bind failed — close our socket, then try to raise existing instance
        server.close()
        server = None
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(LOCK_ADDR)
            client.close()
        except OSError:
            # Nothing listening (race / prior crash) — fall through and exit cleanly
            pass
        sys.exit(0)

    def _on_sigint(signum, frame):
        """Close the abstract socket cleanly on Ctrl-C so the next launch works."""
        if server:
            server.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, _on_sigint)

    GLib.set_application_name('About This System')
    GLib.set_prgname('aboutpane')
    app = AboutPaneApp()

    # Start listener thread after app is created
    t = threading.Thread(target=_listen_for_raise, args=(app, server), daemon=True)
    t.start()

    app.run()
    if server:
        server.close()
