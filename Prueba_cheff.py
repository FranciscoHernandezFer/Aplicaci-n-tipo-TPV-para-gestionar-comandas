import asyncio
import requests
import threading
import time
import re
import os
import json
from datetime import datetime, timedelta
from threading import Lock
from threading import RLock
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import mainthread, Clock
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.core.audio import SoundLoader
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.animation import Animation
from concurrent.futures import ThreadPoolExecutor
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivy.metrics import dp
from kivy.core.text import LabelBase
from kivymd.uix.button import MDIconButton
from kivymd.uix.list import OneLineIconListItem
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import OneLineListItem
from kivymd.uix.button import MDRaisedButton
from kivy.utils import get_color_from_hex
from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import IRightBodyTouch, OneLineAvatarIconListItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.button import MDRoundFlatIconButton
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.card import MDCard
from kivymd.uix.list import MDList, TwoLineListItem
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDRectangleFlatIconButton
from types import MethodType


executor = ThreadPoolExecutor(max_workers=5)

lock = threading.Lock()
# Cargar el token de Telegram desde un archivo .env

lock_orden_mesas = RLock()

CHAT_ID = '-1002531458261'  # ID del chat de Telegram (grupo o canal)

TOKEN = '7833165689:AAE_QWuMCuVa3KQuWVXj8OuRRXdPCv3x_TU'

# Diccionario para almacenar los mensajes por categoría (Mesa)
mensajes_por_categoria = {f"M{i}": [] for i in range(1, 29)}

#variable copia de mensajes
mensajes_copia = {f"M{i}": [] for i in range(1, 29)}

# Lista para almacenar el orden de las mesas
orden_mesas = []

# Ruta para almacenar los mensajes de las mesas
RUTA_MENSAJES = "mensajes.json"

# Archivo compartido para offset e ids
ARCHIVO_ESTADO = "ultimo_offset.json"

# Archivo para guardar el numero de comandas por usuario
ARCHIVO_CONTADORES_TURNO = "contadores_turno.json"

# Función para guardar los mensajes en un archivo JSON
def guardar_mensajes():

    with lock_orden_mesas: # Proteger el acceso a las variables mientras se guardan
        try:
            with open(RUTA_MENSAJES, "w") as archivo:
                json.dump({
                    "mensajes_por_categoria": mensajes_por_categoria,
                    "orden_mesas": orden_mesas
                }, archivo)
                print(f"Datos guardados correctamente en {RUTA_MENSAJES}")
        except Exception as e:
            print(f"Error al guardar mensajes en {RUTA_MENSAJES}: {e}")  

def copiar_mensajes_por_categoria():
    with lock_orden_mesas:
        try:
            with open("mensajes_copia.json", "w") as f:
                json.dump({"mensajes": mensajes_copia}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar mensajes_copia.json: {e}")

# Función para cargar los mensajes desde un archivo JSON
def cargar_mensajes():
   with lock_orden_mesas:
    global mensajes_por_categoria, orden_mesas_real, orden_mesas, mensajes_copia
    if os.path.exists(RUTA_MENSAJES) and os.path.getsize(RUTA_MENSAJES) != 0:
        with open(RUTA_MENSAJES, "r") as archivo:
            datos = json.load(archivo)
            mensajes_por_categoria = datos.get("mensajes_por_categoria", {})
            orden_mesas = datos.get("orden_mesas", [])
    else:
        mensajes_por_categoria = {f"M{i}": [] for i in range(1, 29)}
        orden_mesas = []
        with open(RUTA_MENSAJES, "w") as archivo:
            json.dump({
                "mensajes_por_categoria": mensajes_por_categoria,
                "orden_mesas": orden_mesas
            }, archivo)
   
    # Cargar orden visual desde orden_mesas_real.json
    if os.path.exists("orden_mesas_real.json") and os.path.getsize("orden_mesas_real.json") != 0:
      with open("orden_mesas_real.json", "r") as f:
       orden_mesas_real = json.load(f)

    else:   
        orden_mesas_real = [f"M{i}" for i in range(1, 29)]

        with open("orden_mesas_real.json", "w") as f:
            json.dump(orden_mesas_real, f)

    if os.path.exists("mensajes_copia.json") and os.path.getsize("mensajes_copia.json") != 0:
        with open("mensajes_copia.json", "r") as f:
            datos = json.load(f)
            mensajes_copia = datos.get("mensajes", {})
    else:
        mensajes_copia = {f"M{i}": [] for i in range(1, 29)}
        with open("mensajes_copia.json", "w") as f:
            json.dump({"mensajes": mensajes_copia}, f)

def guardar_orden_visual(layout, archivo="orden_mesas_real.json"):
    print("Intentando adquirir lock_orden_mesas...")
    global orden_mesas_real, layout_backup
    with lock_orden_mesas:
        print("Lock adquirido.")
        app = App.get_running_app()
        orden_visual = []
        if len(layout.children) != 28:  # Si el número de celdas no es 28 quiere decir que está en pantalla completa
            # layout.children está en orden inverso al visual
            for widget in reversed(layout_backup):
                for clave, celda in app.celdas.items():
                    if celda == widget:
                        orden_visual.append(clave)
                        break
        else:                           # Si el número de celdas es 28, significa que está en la vista normal
            for widget in reversed(layout.children):
                for clave, celda in app.celdas.items():
                    if celda == widget:
                        orden_visual.append(clave)
                        break

        with open(archivo, "w") as f:
            json.dump(orden_visual, f)

        orden_mesas_real = orden_visual[:]
        print("Función completada.")


def recalcular_tamaño_fuente_celdas(self, dt):
    # función para ajustar el tamaño de la fuente de los mensajes al actualizarse el tamaño de celda
    app = App.get_running_app()
    for categoria, mensajes in mensajes_por_categoria.items():
        if categoria in orden_mesas:
            celda = app.celdas[categoria]
            celda.label_mensajes.markup = True  # 🔹 Habilitar soporte de color
            mensajes_texto ="\n".join(
                f"[color=0000ff][u][{datetime.strptime(m['hora'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')}] {m['Nombre']}[/u][/color]:\n{m['texto']}"
                for m in mensajes
                if 'texto' in m and 'hora' in m and 'Nombre' in m
            )
            label_mensajes = celda.label_mensajes
            Clock.schedule_once(lambda dt, lbl=label_mensajes, txt=mensajes_texto, celda=celda: ajustar_tamano_fuente(lbl, txt, celda), 0)

def ajustar_tamano_fuente(label_mensajes, mensajes_texto, celda):
    max_font_size = 40
    min_font_size = 20
    font_size = max_font_size

    # Aplica el texto temporalmente para medir
    label_mensajes.text = mensajes_texto
    label_mensajes.font_size = font_size
    label_mensajes.texture_update()

    max_width, max_height = label_mensajes.size  # ← límite real de la celda

    # Crear un Label temporal solo para medir
    label_temp = Label(text=mensajes_texto, font_size=font_size,
                       halign="center", valign="top",
                       text_size=(max_width, None))
    label_temp.texture_update()
    texto_real_width, texto_real_height = label_temp.texture_size

    while (texto_real_width > max_width or texto_real_height > max_height) and font_size > min_font_size:
        font_size -= 1
        label_temp.font_size = font_size
        label_temp.texture_update()
        texto_real_width, texto_real_height = label_temp.texture_size

    label_mensajes.font_size = font_size
    label_mensajes.text = mensajes_texto
    label_mensajes.texture_update()
    # --- Si aún así no cabe, añadir un icono en la celda ---
    if texto_real_height > max_height:
        if not hasattr(celda, "icono_mas_texto"):
            celda.icono_mas_texto = MDIcon(
                icon="chevron-down",
                halign="center",
                theme_text_color="Custom",
                text_color=(0.3, 0.3, 0.3, 1),  # gris
                size_hint=(None, None),
                size=(dp(24), dp(24)),
                pos_hint={"center_x": 0.5, "y": 0}  # abajo centrado
            )
            celda.add_widget(celda.icono_mas_texto)
    else:
        # Si ahora sí cabe, eliminamos el icono
        if hasattr(celda, "icono_mas_texto") and celda.icono_mas_texto is not None:
            if celda.icono_mas_texto.parent:
                celda.remove_widget(celda.icono_mas_texto)
            celda.icono_mas_texto = None


@mainthread
def actualizar_celda(categoria, mensaje, nueva_mesa):
    global layout_backup
    with lock_orden_mesas:
        app = App.get_running_app()
        layout = app.grid
        celda = app.celdas[categoria]
        mensajes = mensajes_por_categoria[categoria]
        celda.label_mensajes.markup = True  # 🔹 Habilitar soporte de color
        mensajes_texto = "\n".join(
            f"[color=0000ff][u][{datetime.strptime(m['hora'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')}] {m['Nombre']}:[/u][/color]\n[color=000000]{m['texto']}"  # texto en negro
            for m in mensajes
            if 'texto' in m and 'hora' in m and 'Nombre' in m
        )
        label_mensajes = celda.label_mensajes
        # Solo mover la celda si es la primera vez que recibe un mensaje
        if nueva_mesa == 1:
            if len(layout.children) == 28:   # Si hay 28 celdas, significa que está en la vista normal
                # Eliminar todas las celdas del layout
                for mesa in (orden_mesas):
                    layout.remove_widget(app.celdas[mesa])

                # Volver a agregar las celdas en el nuevo orden
                for i, mesa in enumerate(orden_mesas):
                    layout.add_widget(app.celdas[mesa], index=len(layout.children))
            else:  # Si hay menos de 28 celdas, significa que está en la vista de pantalla completa
                # Eliminar todas las celdas del layout
                for mesa in (orden_mesas):
                    layout_backup.remove(app.celdas[mesa])

                # Volver a agregar las celdas en el nuevo orden
                for i, mesa in enumerate(orden_mesas):
                    layout_backup.insert(len(layout_backup), app.celdas[mesa])

            # GUARDAR orden visual real después de reordenar
            guardar_orden_visual(layout)

        # Recalcular el tamaño de la fuente y ajustar el texto
        Clock.schedule_once(lambda dt: ajustar_tamano_fuente(label_mensajes, mensajes_texto, celda), 0)
        # 🔹 Si esa mesa está en pantalla completa, actualizar también el clon
        if hasattr(app, "celda_fullscreen_real") and app.celda_fullscreen_real:
            if app.celda_fullscreen_real.numero == celda.numero:
                app.celda_fullscreen_clone.label_mensajes.markup = True
                app.celda_fullscreen_clone.label_mensajes.text = mensajes_texto
                Clock.schedule_once(
                    lambda dt: ajustar_tamano_fuente(
                        app.celda_fullscreen_clone.label_mensajes,
                        mensajes_texto,
                        app.celda_fullscreen_clone
                    ),
                    0
                )

        app.flash_verde()
        if app.sonido:
            app.sonido.play()

def cargar_estado():
    with lock:
        try:
            with open(ARCHIVO_ESTADO, "r") as f:
                estado = json.load(f)
        except(FileNotFoundError, json.JSONDecodeError):
            estado = {"offset": 0, "mensajes_recibidos": [], "Contador usuarios": {}}
        return estado
def guardar_estado(data):
    with lock:
        with open(ARCHIVO_ESTADO, "w") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def procesar_mensaje(message, estado):
    try:
        message_id = message.get("message_id", 0)
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        clave_unica = f"{chat_id}_{message_id}_{text}"
        Nombre = message.get("from", {}).get("first_name", "Desconocido")

        if clave_unica in estado["mensajes_recibidos"]:
            return  # Ya registrado

        match = re.search(r'\bM([1-9]|1[0-9]|2[0-6]|28)\b|\bpa(ra)? llevar\b', text, re.IGNORECASE)
        if not match:
            return

        categoria = f"M{match.group(1)}" if match.group(1) else "M27"
        if categoria not in mensajes_por_categoria:
            mensajes_por_categoria[categoria] = []
        hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")        
        nuevo_mensaje = {"texto": text, "Nombre": Nombre, "hora": hora_actual, "id": message_id}
        mensajes_por_categoria[categoria].append(nuevo_mensaje)
        mensajes_copia[categoria].append(nuevo_mensaje)
        nueva_mesa = 0
        if categoria not in orden_mesas:
            orden_mesas.insert(0, categoria)
            nueva_mesa = 1

        actualizar_celda(categoria, text, nueva_mesa)
        copiar_mensajes_por_categoria()
        guardar_mensajes()

        estado["mensajes_recibidos"].append(clave_unica)
        estado["mensajes_recibidos"] = estado["mensajes_recibidos"][-800:]  # limitar tamaño

        # --- Actualizar contadores por turno ---
        turno_actual = obtener_turno_actual()
        contadores = cargar_contadores_turno()

        if turno_actual not in contadores:
            contadores[turno_actual] = {}  # Nueva clave de turno

        if Nombre not in contadores[turno_actual]:
            contadores[turno_actual][Nombre] = {'contador': 0, 'porcentaje': 0}

        contadores[turno_actual][Nombre]['contador'] += 1

        guardar_contadores_turno(contadores)

    except Exception as e:
        print(f"Error al procesar mensaje: {e}")

def recibir_mensajes():
    estado = cargar_estado()
    offset = estado.get("offset", 0)
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {'timeout': 10, 'offset': offset}
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            if data.get("ok"):
                updates = data.get("result", [])
                if updates:
                    for update in updates:
                        message = update.get("message")
                        update_id = update["update_id"]

                        if not message or "text" not in message:
                            continue
                        try:                          
                            procesar_mensaje(message, estado)
                            offset = update_id + 1  # Solo si no hay error
                            estado["offset"] = offset
                            guardar_estado(estado)
                        except Exception as e:
                            print(f"Error procesando mensaje con update_id {update_id}: {e}")

                    offset = updates[-1]["update_id"] + 1
                    estado["offset"] = offset
                    guardar_estado(estado)
                    limpiar_mensajes_viejos() # Actualiza la funcion para ver si han pasado 12 horas
                            # Si el Bot API devuelve error, backoff y reintento
        except Exception as e:
            print(f"Error al recibir mensajes: {e}")
        time.sleep(0.1)

def limpiar_mensajes_viejos():  # Limpiar mensajes viejos en mensajes_copia
    ahora = datetime.now()
    max_tiempo = timedelta(hours=12)
    cambios = False

    # Asegurarse de que mensajes_copia tiene la estructura esperada
    if not isinstance(mensajes_copia, dict):
        print("mensajes_copia no es un diccionario válido.")
        return

    for categoria in list(mensajes_copia):
        mensajes_actualizados = []
        for mensaje in mensajes_copia.get(categoria, []):
            try:
                hora_msg = datetime.strptime(mensaje["hora"], "%Y-%m-%d %H:%M:%S")
                if ahora - hora_msg <= max_tiempo:
                    mensajes_actualizados.append(mensaje)
                else:
                    cambios = True
            except Exception as e:
                print(f"Error al analizar hora de mensaje en {categoria}: {e}")

        mensajes_copia[categoria] = mensajes_actualizados  # ← SIEMPRE deja la clave, vacía o no

    if cambios:
        try:
            with open("mensajes_copia.json", "w") as f:
                json.dump({"mensajes": mensajes_copia}, f, indent=2, ensure_ascii=False)
            print("mensajes_copia.json actualizado correctamente.")
        except Exception as e:
            print(f"Error al guardar mensajes_copia.json: {e}")

def cargar_contadores_turno():
    try:
        with open(ARCHIVO_CONTADORES_TURNO, "r") as f:
            data = json.load(f)
            if not data:  # Si el contenido está vacío
                raise ValueError("Archivo vacío")
            return data
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        # Crear o inicializar el archivo si no existe o está vacío/corrupto
        with open(ARCHIVO_CONTADORES_TURNO, "w") as f:
            json.dump({}, f)
        return {}

def guardar_contadores_turno(data):
    # Calcular porcentaje antes de guardar
    for turno, usuarios in data.items():
        total_mensajes = sum(v['contador'] for v in usuarios.values())
        for usuario, datos in usuarios.items():
            porcentaje = (datos['contador'] / total_mensajes) * 100 if total_mensajes > 0 else 0
            datos['porcentaje'] = round(porcentaje, 2)
    with open(ARCHIVO_CONTADORES_TURNO, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def obtener_turno_actual():
    ahora = datetime.now()
    hora = ahora.hour
    fecha = ahora.strftime("%d/%m/%Y")

    if 7 <= hora < 17:
        return f"Turno mañana dia {fecha}"
    else:
        return f"Turno tarde dia {fecha}"

def resetear_contadores_turno():
    global ARCHIVO_CONTADORES_TURNO
    with lock:
        try:
            with open(ARCHIVO_CONTADORES_TURNO, "w") as f:
                json.dump({}, f)
            print("Contadores de turno reseteados correctamente.")
        except Exception as e:
            print(f"Error al resetear contadores de turno: {e}")

class Separator(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(size_hint_y=None, height=1, **kwargs)
        with self.canvas:
            Color(0.8, 0.8, 0.8, 1)  # gris claro
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class CeldaMesa(MDCard):
    def __init__(self, numero, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint=(1, None),
            height=550,
            padding=15,
            radius=[18],
            elevation=0,
            ripple_behavior=True,     # efecto ripple al tocar
            **kwargs
        )
        self.numero = numero
        self.fullscreen = False
        self.aceptar_pulsacion = True
        self.md_bg_color = (0.95, 0.95, 0.95, 1)  # gris claro transparente
        self.last_font_size = 20     # cache para ajuste de fuente (mejora 2)

        # --- Fondo liso oscuro en lugar de sombra ---
        with self.canvas.before:
            Color(0.0, 0.0, 0.0, 1)  # negro oscuro
            self.bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[18]
            )
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Colores de tema (fallback por si no hay theme_cls aún)
        app = App.get_running_app()
        try:
            primary = app.theme_cls.primary_color
            text_on_primary = (1, 1, 1, 1) # negro
        except Exception:
            primary = (0.0, 0.45, 0.9, 1)
            text_on_primary = (1, 1, 1, 1)

        # --- Cabecera coloreada ---
        header = MDBoxLayout(orientation="vertical", size_hint_y=None, size=(250, 55), padding=(8, 0, 8, 0))
        with header.canvas.before:
            Color(*primary)
            self._hdr_rect = RoundedRectangle(pos=header.pos, size=(55, 55), radius=[25, 25, 0, 0])
        header.bind(pos=lambda inst, val: setattr(self._hdr_rect, "pos", inst.pos),
                    size=lambda inst, val: setattr(self._hdr_rect, "size", inst.size))

        self.label_titulo = MDLabel(
            text=f"Mesa {numero}",
            halign="center",
            bold=True,
            theme_text_color="Custom",
            text_color=text_on_primary,
            size_hint=(1, 1),
        )
        header.add_widget(self.label_titulo)
        self.add_widget(header)

        # --- Área de mensajes ---
        self.label_mensajes = Label(
            text="",
            markup=True,          # soporta [color], [u], [b], etc.
            font_size=20,
            color=(0, 0, 0, 1),  # color del texto
            halign="center",
            valign="top",
            size_hint=(1, 1),
        )
        # Ajuste automático del wrapping
        self.label_mensajes.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], val[1])))
        self.add_widget(self.label_mensajes)

    # 🔹 Este método faltaba
    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # ⏱️ Debug: imprime instante exacto de la pulsación
            print(f"[DEBUG] Pulsación detectada en Celda {self.numero} a {time.time():.3f}, aceptar_pulsacion={self.aceptar_pulsacion}")

            if not self.aceptar_pulsacion:
                print(f"[DEBUG] Pulsación IGNORADA en {self.numero} (cooldown activo)")
                return True

            # Bloquear nuevas pulsaciones
            self.aceptar_pulsacion = False

            app = App.get_running_app()

            if self.fullscreen:
                print(f"[DEBUG] Salir de fullscreen en {self.numero}")
                app.restaurar_vista()
                self.fullscreen = False
                Clock.schedule_once(self.habilitar_pulsacion, 0.7)

            else:
                print(f"[DEBUG] Entrar en fullscreen en {self.numero}")
                self.fullscreen = True
                app.mostrar_a_pantalla_completa(self)
                Clock.schedule_once(self.habilitar_pulsacion, 1.2)

            return True

        return super().on_touch_down(touch)

    def habilitar_pulsacion(self, dt):
        print(f"[DEBUG] Cooldown terminado en {self.numero} a {time.time():.3f}")
        self.aceptar_pulsacion = True


    def _actualizar_text_size(self, instance, value):
        instance.text_size = (instance.width, None)

    def _update_canvas(self, *args):
        self.fondo.pos = self.pos
        self.fondo.size = self.size
        self.borde.rectangle = (self.x, self.y, self.width, self.height)
        
class TabletApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.celda_fullscreen = None
        self.layout_original = None
        self.boton_completar = None
        self.boton_historial = None
        self.dialog = None
        self.theme_cls.primary_palette = "Blue"   # "Indigo", "Teal", etc.
        self.theme_cls.theme_style = "Light"      # o "Dark"


    def build(self):
        cargar_mensajes()

        # Crear grid de celdas
        self.grid = GridLayout(cols=3, padding=10, spacing=10, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.celdas = {}
        self.sonido = SoundLoader.load("notificacion.mp3")

        # --- Fondo gris oscuro para el grid ---
        grid_fondo = FloatLayout(size_hint=(1, 1))
        with grid_fondo.canvas.before:
            Color(0.15, 0.15, 0.15, 1)  # Gris oscuro
            self.grid_bg_rect = Rectangle(size=grid_fondo.size, pos=grid_fondo.pos)
        grid_fondo.bind(size=lambda inst, val: setattr(self.grid_bg_rect, "size", inst.size))
        grid_fondo.bind(pos=lambda inst, val: setattr(self.grid_bg_rect, "pos", inst.pos))
        grid_fondo.add_widget(self.grid)

        # Asegura que el FloatLayout tenga la altura del grid para que funcione el scroll
        self.grid.bind(height=lambda inst, val: setattr(grid_fondo, "height", val))
        grid_fondo.size_hint_y = None
        grid_fondo.height = self.grid.height

        for i in range(1, 29):
            self.celdas[f"M{i}"] = CeldaMesa(i)

        if orden_mesas_real:
            orden_a_usar = orden_mesas_real
        else:
            orden_a_usar = [f"M{i}" for i in range(1, 29)]

        for mesa in orden_a_usar:
            self.grid.add_widget(self.celdas[mesa])
            if mesa in orden_mesas:
                mensajes_texto = "\n".join(
                    f"[b][{datetime.strptime(mensaje.get('hora', ''), '%Y-%m-%d %H:%M:%S').strftime('%H:%M')}][/b]\n{mensaje.get('texto', '')}"
                    for mensaje in mensajes_por_categoria[mesa]
                    if "texto" in mensaje and "hora" in mensaje
                )
                self.celdas[mesa].label_mensajes.text = mensajes_texto
                Clock.schedule_once(lambda _, lbl=self.celdas[mesa].label_mensajes, txt=mensajes_texto, celda=self.celdas[mesa]: ajustar_tamano_fuente(lbl, txt, celda), 0)

        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(grid_fondo)

        # Layout principal para contener el ScrollView y el flash verde
        layout_flotante = MDFloatLayout()
        layout_flotante.add_widget(scroll_view)

        # --- Flash verde ---
        self.flash_widget = Widget(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        with self.flash_widget.canvas:
            self.flash_color = Color(0, 1, 0, 0)
            self.flash_rect = Rectangle(pos=(0, 0), size=(Window.width, Window.height))
        self.flash_widget.bind(size=self._update_flash_rect, pos=self._update_flash_rect)
        layout_flotante.add_widget(self.flash_widget)

        # --- Botones flotantes ---
        boton_reset = MDFloatingActionButton(
            icon="alert",
            size_hint=(0.1, 0.12),
            pos_hint={"right": 0.98, "y": 0.05},
            on_release=self.resetear_celdas
        )
        layout_flotante.add_widget(boton_reset)

        boton_porcentaje = MDFloatingActionButton(
            icon="percent",
            size_hint=(0.1, 0.12),
            pos_hint={"x": 0.02, "y": 0.05},
            on_release=self.mostrar_informacion_turnos
        )
        layout_flotante.add_widget(boton_porcentaje)

        # --- Hilos y lógica inicial ---
        Clock.schedule_once(lambda dt: recalcular_tamaño_fuente_celdas(self, dt), 0.5)
        bot_thread = threading.Thread(target=recibir_mensajes)
        bot_thread.daemon = True
        bot_thread.start()


        return layout_flotante
    

    def _update_flash_rect(self, instance, value):
        self.flash_rect.size = instance.size
        self.flash_rect.pos = instance.pos

    def historial_de_comandas(self, *_):
        global mensajes_copia

        mesa_actual = "M" + str(self.celda_fullscreen_real.numero)
        mensajes = mensajes_copia.get(mesa_actual, [])
        mensajes_ordenados = reversed(sorted(mensajes, key=lambda x: x['hora']))

        # --- Layout contenedor ---
        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=Window.height * 0.75,
            width=Window.width * 0.95,
            spacing=10
        )
        scroll = ScrollView(size_hint=(1, 1))
        md_list = MDList(spacing=10)

        for comanda in mensajes_ordenados:
            hora = comanda['hora']
            texto = comanda['texto']

            item_box = MDBoxLayout(orientation="vertical", padding=(10, 5), size_hint_y=None)
            item_box.bind(minimum_height=item_box.setter("height"))

            # Hora en azul
            label_hora = MDLabel(
                text=hora,
                theme_text_color="Custom",
                text_color=(0, 0, 1, 1),
                halign="left",
                size_hint_y=None,
            )
            label_hora.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))

            # Texto multilínea en negro
            label_texto = MDLabel(
                text=texto,
                theme_text_color="Custom",
                text_color=(0, 0, 0, 1),
                halign="left",
                size_hint_y=None,
            )
            label_texto.bind(
                texture_size=lambda inst, val: setattr(inst, "height", val[1]),
                width=lambda inst, val: setattr(inst, "text_size", (val, None))
            )

            item_box.add_widget(label_hora)
            item_box.add_widget(label_texto)
            md_list.add_widget(item_box)
            md_list.add_widget(Separator())

        scroll.add_widget(md_list)
        content.add_widget(scroll)

        # Botón cerrar
        boton_cerrar = MDRaisedButton(
            text="Cerrar"
        )

        # --- Diálogo ---
        historial_dialog = MDDialog(
            title=f"Historial de Mesa {self.celda_fullscreen_real.numero}",
            type="custom",
            content_cls=content,
            height=Window.height * 0.75,
            width=Window.width * 0.95,
            auto_dismiss=False,
            buttons=[boton_cerrar],
        )

        # Cerrar correctamente el diálogo y el fondo oscuro
        def cerrar_dialogo_historial(*_):
            if historial_dialog:
                historial_dialog.dismiss()
        
        boton_cerrar.bind(on_press=cerrar_dialogo_historial)

        historial_dialog.open()

    def mostrar_a_pantalla_completa(self, celda_real):
        """Muestra una copia de la celda a pantalla completa sin tocar la original."""
        if self.grid is None:
            print("Error: grid no inicializado.")
            return

        self.celda_fullscreen_real = celda_real
        root = App.get_running_app().root
        self.fullscreen_layout = FloatLayout()

        # Crear y guardar el clon
        self.celda_fullscreen_clone = CeldaMesa(celda_real.numero)
        self.celda_fullscreen_clone.label_mensajes.text = celda_real.label_mensajes.text
        self.celda_fullscreen_clone.label_mensajes.font_size = celda_real.label_mensajes.font_size + 10

        # 🔹 Tocar el clon = salir de fullscreen
        def salir_fullscreen_touch(widget, touch):
            if widget.collide_point(*touch.pos):
                print(f"[DEBUG] Toque en clon fullscreen de {celda_real.numero}")
                celda_real.fullscreen = False  # 👈 sincronizar estado
                self.restaurar_vista()
                return True
            return super(type(widget), widget).on_touch_down(touch)
        self.celda_fullscreen_clone.on_touch_down = MethodType(salir_fullscreen_touch, self.celda_fullscreen_clone)

        # Ajustar altura
        alto_ventana = Window.height
        tamaño_mensaje = len(self.celda_fullscreen_clone.label_mensajes.text)
        alto_mensaje = 100 + (tamaño_mensaje // 20) * 20 if tamaño_mensaje > 280 else 0
        self.celda_fullscreen_clone.height = alto_ventana + alto_mensaje

        # Scroll
        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(self.celda_fullscreen_clone)
        self.fullscreen_layout.add_widget(scroll_view)

        #--- Botón Historial (izquierda) ---    
        self.boton_historial = MDRectangleFlatIconButton(
            text="Historial",
            icon="history",
            icon_color=(1, 1, 1, 1),
            font_size= dp(16),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            line_color=(0.2, 0.4, 0.8, 1),   # azul
            md_bg_color=(0.2, 0.4, 0.8, 1),  # azul relleno
            size_hint=(None, None),
            size=(dp(180), dp(50)),
            padding=(dp(5), dp(5), dp(5), dp(5)),
            pos_hint={'x': 0.02, 'top': 0.895},  # izquierda centrado vertical
            on_release=lambda x: self.historial_de_comandas(x),
        )
        self.boton_historial.bind(on_release=lambda x: self.historial_de_comandas(x))
        self.fullscreen_layout.add_widget(self.boton_historial)

        # --- Botón Completar (flotante, derecha medio) ---
        self.boton_completar = MDRectangleFlatIconButton(
            text="Completar",
            icon="check",
            theme_text_color="Custom",
            icon_color=(1, 1, 1, 1),      # 
            font_size= dp(18),
            padding= (dp(16), dp(60)),
            text_color=(1, 1, 1, 1),
            line_color=(0, 0.6, 0, 1),    # verde
            md_bg_color=(0, 0.6, 0, 1),   # verde relleno
            size_hint=(None, None),
            size=(dp(300), dp(90)),  # bastante grande
            pos_hint={'right': 0.985, 'center_y': 0.77},  # derecha, centrado vertical
        )
        self.boton_completar.bind(on_release=lambda x: self.eliminar_comanda())
        self.fullscreen_layout.add_widget(self.boton_completar)

        # Añadir al root
        root.add_widget(self.fullscreen_layout)


    def eliminar_comanda(self):
        """Eliminar la comanda de la celda actual y restaurar vista."""
        original = [f"M{i}" for i in range(1, 29)]
        global orden_mesas_real
    
        # --- Notificar por Telegram ---
        self.notificar_comanda_completada()  

        if self.celda_fullscreen_real:
            nombre_mesa = f"M{self.celda_fullscreen_real.numero}"
            if nombre_mesa in orden_mesas:

                # Reorganizar orden_mesas_real
                posicion_destino = len(orden_mesas) + sum(
                    1 for x in original if original.index(x) < original.index(nombre_mesa) and x not in orden_mesas
                )
                orden_mesas_real.insert(posicion_destino, nombre_mesa)
                orden_mesas_real.remove(nombre_mesa)
                with open("orden_mesas_real.json", "w") as f:
                    json.dump(orden_mesas_real, f)

                # Limpiar mensajes de la celda y actualizar
                mensajes_por_categoria[nombre_mesa] = []
                orden_mesas.remove(nombre_mesa)

                # --- Guardar referencia local ---
                celda_ref = self.celda_fullscreen_real

                # Limpiar texto
                celda_ref.label_mensajes.text = ""

                # Forzar recalcular tamaño → elimina icono si existía
                Clock.schedule_once(lambda dt: ajustar_tamano_fuente(
                    celda_ref.label_mensajes, "", celda_ref
                ), 0)

                guardar_mensajes()

        # 👇 Restaurar la vista
        self.restaurar_vista()

        # 👇 Y reordenar explícitamente las celdas en el grid
        if self.grid and orden_mesas_real:
            self.grid.clear_widgets()
            for mesa in orden_mesas_real:
                self.grid.add_widget(self.celdas[mesa])
            self.grid.do_layout()

        self.fullscreen = False

    def notificar_comanda_completada(self):
        """Se envia un mensaje por telegram indicando que la comanda ha sido completada."""
        # Obtener texto original y dividir por líneas
        lineas = self.celda_fullscreen_real.label_mensajes.text.splitlines()

        # Eliminar las dos primeras líneas si existen
        if len(lineas) >= 2:
            lineas = lineas[2:]

        # Reconstruir el texto limpio
        texto_limpio = "\n".join(lineas).strip()

        # ✅ Si la comanda está vacía, no enviamos nada
        if not texto_limpio:
            print(f"[DEBUG] No se envía mensaje de la mesa {self.celda_fullscreen_real.numero} porque la comanda está vacía.")
            return
        
        # Construir mensaje final
        mensaje = f"✅ La comanda de la mesa {self.celda_fullscreen_real.numero} ha sido completada:\n{texto_limpio}"

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": mensaje
        }

        try:
            import requests
            requests.post(url, data=data)
        except Exception as e:
            print(f"[ERROR] No se pudo enviar la notificación a Telegram: {e}")



    def restaurar_vista(self):
        """Cerrar fullscreen y dejar el grid intacto."""
        if getattr(self, "fullscreen_layout", None):
            root = App.get_running_app().root
            if self.fullscreen_layout.parent:
                root.remove_widget(self.fullscreen_layout)

            self.fullscreen_layout.clear_widgets()
            self.fullscreen_layout = None

        # Reset referencias
        self.celda_fullscreen_clone = None
        self.celda_fullscreen_real = None
        self.boton_completar = None
        self.boton_historial = None


            
    def resetear_celdas(self, *args):
        def confirmar_reset(instance):
            global mensajes_por_categoria, orden_mesas_real, orden_mesas, mensajes_copia

            # Limpiar los mensajes y el orden
            mensajes_por_categoria = {f"M{i}": [] for i in range(1, 29)}
            mensajes_copia = {f"M{i}": [] for i in range(1, 29)}
            orden_mesas_real = [f"M{i}" for i in range(1, 29)]
            orden_mesas = []
            mensajes_recibidos = {"offset": 0, "mensajes_recibidos": [], "Contador usuarios": {}}

            # Limpiar la vista del grid
            self.grid.clear_widgets()

            # Restaurar las celdas vacías en orden original
            for i in range(1, 29):
                celda = self.celdas[f"M{i}"]
                celda.label_mensajes.text = ""  # Reiniciar el texto de la celda
                self.grid.add_widget(celda)

            with open("orden_mesas_real.json", "w") as f:
                json.dump(orden_mesas_real, f)

            with open("ultimo_offset.json", "w") as f:
                json.dump( mensajes_recibidos, f)

            guardar_mensajes()

            with open("mensajes_copia.json", "w") as f:
                json.dump({"mensajes": mensajes_copia}, f)

            popup.dismiss()

        def cancelar_reset(instance):
            popup.dismiss()

        # Contenido del popup
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        box.add_widget(Label(text="¿Estás seguro de que quieres resetear todas las celdas?", halign='center'))

        botones = BoxLayout(spacing=10, size_hint=(1, 0.3))
        btn_si = Button(text="Sí", background_color=(0, 1, 0, 1))
        btn_no = Button(text="No", background_color=(1, 0, 0, 1))
        btn_si.bind(on_press=confirmar_reset)
        btn_no.bind(on_press=cancelar_reset)
        botones.add_widget(btn_si)
        botones.add_widget(btn_no)

        box.add_widget(botones)

        popup = Popup(title="Confirmar reseteo", content=box, size_hint=(0.8, 0.4))
        popup.open()

    def mostrar_informacion_turnos(self, *args):
        contadores = cargar_contadores_turno()
        if not contadores:
            texto = "No hay información de turnos disponible."
        else:
            texto = ""
            for turno, datos in reversed(list(contadores.items())):
                texto += f"[b]{turno}[/b]\n"
                total_mensajes = sum(user_data.get("contador", 0) for user_data in datos.values())
                for usuario, user_data in datos.items():
                    mensajes = user_data.get("contador", 0)
                    porcentaje = user_data.get("porcentaje", 0.0)
                    texto += f"{usuario}: {mensajes} mensajes ({porcentaje:.1f}%)\n"
                texto += "\n"

        if not self.dialog:

            scroll = ScrollView(size_hint=(1, None), height="300dp")
            self.label_dialog = Label(
                text=texto,
                color=(0, 0, 0, 1),  # Texto negro
                size_hint_y=None,
                valign="top",
                halign="center",
                markup=True,
                text_size=(self.root.width * 0.8, None),
            )
            self.label_dialog.bind(
                texture_size=lambda instance, value: setattr(self.label_dialog, 'height', value[1])
            )
            scroll.add_widget(self.label_dialog)

            botones_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height="40dp", padding=[10, 10], spacing=10)
            boton_resetear = MDRoundFlatIconButton(
                icon="refresh",
                text="Resetear",
                on_release=self.mostrar_confirmacion_reseteo,
                size_hint=(None, None),
                height="36dp"
            )
            botones_layout.add_widget(boton_resetear)

            # Espaciador para empujar el siguiente botón a la derecha
            botones_layout.add_widget(BoxLayout())

             # Botón a la derecha
            boton_cerrar = MDFlatButton(
                text="Cerrar",
                on_release=self.cerrar_dialogo
            )
            botones_layout.add_widget(boton_cerrar)

            self.dialog = MDDialog(
                title="Información De Turnos",
                type="custom",
                content_cls=scroll,
                size_hint=(0.8, None),
                height="500dp",
            )
            self.dialog.add_widget(botones_layout)
        else:
            self.label_dialog.text = texto

        self.dialog.open()

    def cerrar_dialogo(self, *args):
        if self.dialog:
            self.dialog.dismiss()

    def mostrar_confirmacion_reseteo(self, *args):

        content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        label = MDLabel(
            text="¿Estás seguro de que deseas resetear los contadores de turno?",
            halign="center",
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1),  # Negro
            size_hint_y=None,
            markup=True
        )
        label.bind(
        texture_size=lambda instance, value: setattr(label, 'height', value[1]),
        width=lambda instance, value: setattr(label, 'text_size', (value, None))
        )
        content.add_widget(label)

        confirm_dialog = MDDialog( 
            title="",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancelar", on_release=lambda x: confirm_dialog.dismiss()),
                MDRaisedButton(text="Aceptar", on_release=lambda x: self.accion_reseteo(confirm_dialog)),
            ],
        )
        confirm_dialog.open()

    def accion_reseteo(self, dialogo):
        dialogo.dismiss()
        resetear_contadores_turno()
        if self.dialog:
            self.dialog.dismiss()  # Cierra el diálogo de información si sigue abierto
    
    def _update_flash_rect(self, *args):
        self.flash_rect.size = self.flash_widget.size
        self.flash_rect.pos = self.flash_widget.pos


    def flash_verde(self):
        self.flash_color.a = 0  # Asegura que comience desde 0
        anim_in = Animation(a=0.4, duration=0.6)
        anim_out = Animation(a=0, duration=1.3)
        anim_in.bind(on_complete=lambda *args: anim_out.start(self.flash_color))
        anim_in.start(self.flash_color)


if __name__ == "__main__":
    TabletApp().run()
