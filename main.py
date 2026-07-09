import os, json, ssl, urllib.request, threading, traceback, urllib.parse, sys, webbrowser
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.core.clipboard import Clipboard
from kivy.properties import ListProperty
from kivy.base import ExceptionManager, ExceptionHandler 
from kivy.utils import platform

# --- REPORTLAB PDF GENERATION IMPORTS ---
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

Window.softinput_mode = "below_target"
Window.clearcolor = (0.02, 0.35, 0.45, 1) 

cache_store = None
memory_cache = {}

def save_cache(key, val):
    global cache_store, memory_cache
    memory_cache[key] = val
    if cache_store:
        try: cache_store.put(key, data=val)
        except: pass

def load_cache(key):
    global cache_store, memory_cache
    if key in memory_cache: return memory_cache[key]
    if cache_store and cache_store.exists(key):
        try: 
            d = cache_store.get(key)['data']
            memory_cache[key] = d
            return d
        except: pass
    return None

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaGsfhJyn3uUuWs2TKSyVsmLeAFcDNiZsyc5PleRErLb5sp036TlHsr6KYUDh7MNCC5w/exec"

class ColorfulLabel(Label):
    bg_color = ListProperty([0.1, 0.5, 0.7, 0.85])

class SmoothInput(TextInput):
    def __init__(self, **kwargs):
        super(SmoothInput, self).__init__(**kwargs)
        self.bind(focus=self.on_focus_select)
        
    def on_focus_select(self, instance, value):
        if value:
            Clock.schedule_once(lambda dt: self.select_all(), 0.05)

    def insert_text(self, substring, from_undo=False):
        s = ''.join([c for c in substring if c in '0123456789aAbB-'])
        return super().insert_text(s, from_undo=from_undo)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if keycode[0] in (13, 271): 
            self.dispatch('on_text_validate')
            return True 
        return super().keyboard_on_key_down(window, keycode, text, modifiers)

def show_alert_popup(title, message):
    box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
    lbl = Label(text=message, color=(1,0.2,0.2,1), font_size='18sp', bold=True, halign='center')
    lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None))) 
    box.add_widget(lbl)
    btn_close = Button(text="OK, I WILL FIX IT", background_color=(0.9, 0.2, 0.2, 1), bold=True, size_hint_y=None, height="60dp")
    box.add_widget(btn_close)
    popup = Popup(title=title, title_color=(1,1,1,1), content=box, size_hint=(0.85, 0.45), auto_dismiss=False, background_color=(0.1, 0.2, 0.3, 0.9))
    btn_close.bind(on_release=popup.dismiss)
    popup.open()

def show_success_popup(title, message):
    box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
    lbl = Label(text=message, color=(0.5, 1, 0.5, 1), font_size='22sp', bold=True, halign='center')
    lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None))) 
    box.add_widget(lbl)
    btn_close = Button(text="AWESOME", background_color=(0, 0.7, 0.3, 1), bold=True, size_hint_y=None, height="60dp")
    box.add_widget(btn_close)
    popup = Popup(title=title, title_color=(1,1,1,1), content=box, size_hint=(0.85, 0.45), auto_dismiss=False, background_color=(0.1, 0.3, 0.2, 0.9))
    btn_close.bind(on_release=popup.dismiss)
    popup.open()

def show_error_popup(error_log):
    box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
    box.add_widget(Label(text="🚨 SYSTEM BUG REPORT 🚨", color=(1,0.2,0.2,1), font_size='20sp', bold=True, size_hint_y=None, height="40dp"))
    text_input = TextInput(text=str(error_log), readonly=True, foreground_color=(1,0,0,1), background_color=(0.95,0.95,0.95,0.9), multiline=True, font_size='14sp')
    box.add_widget(text_input)
    btn_box = BoxLayout(size_hint_y=None, height="60dp", spacing="15dp")
    btn_copy = Button(text="COPY FULL ERROR", background_color=(0.0, 0.7, 0.9, 1), bold=True)
    btn_close = Button(text="CLOSE APP", background_color=(0.9, 0.2, 0.2, 1), bold=True)
    btn_box.add_widget(btn_copy)
    btn_box.add_widget(btn_close)
    box.add_widget(btn_box)
    popup = Popup(title="Smart AI Catcher", title_color=(1,1,1,1), content=box, size_hint=(0.95, 0.95), auto_dismiss=False)
    def copy_action(inst):
        Clipboard.copy(str(error_log))
        btn_copy.text = "COPIED TO CLIPBOARD!"
        btn_copy.background_color = (0, 0.8, 0.2, 1)
    btn_copy.bind(on_release=copy_action)
    btn_close.bind(on_release=lambda x: popup.dismiss()) 
    popup.open()

class KivyCrashHandler(ExceptionHandler):
    def handle_exception(self, inst):
        error_log = traceback.format_exc()
        Clock.schedule_once(lambda dt, err=error_log: show_error_popup(err), 0)
        return ExceptionManager.PASS

ExceptionManager.add_handler(KivyCrashHandler())

KV = '''
<ColorfulLabel>:
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [6,]
    color: 1, 1, 1, 1
    bold: True
    font_size: '16sp'

<SmoothInput>:
    text_validate_unfocus: False 
    background_normal: ''
    background_color: 0.9, 0.95, 1, 0.85  
    color: 0, 0, 0, 1
    bold: True
    font_size: '18sp'
    halign: 'center'
    multiline: False
    input_type: 'number'
    canvas.after:
        Color:
            rgba: 0.8, 0.3, 0.3, 1
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 6]
            width: 1.2

ScreenManager:
    LoginScreen:
    PrincipalDashboard:
    TeacherDashboard:
    MarksEntryScreen:
    TeacherStatusScreen:
    ResetScreen:
    SubjectMappingScreen:
    AddStudentScreen:
    RemoveStudentScreen:

<LoginScreen>:
    name: 'login'
    on_enter: root.preload_data()
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.0, 0.5, 0.7, 0.4 
            Rectangle:
                pos: self.pos[0], self.size[1] - dp(120)
                size: self.size[0], dp(120)
        BoxLayout:
            orientation: 'vertical'
            padding: "25dp"
            spacing: "20dp"
            Label:
                text: 'SANSKRIT NASIRABAD'
                font_size: '28sp'
                bold: True
                color: 0.8, 1.0, 1.0, 1
                size_hint_y: None
                height: "80dp"
                
            TextInput:
                id: mobile_input
                hint_text: 'Enter Mobile Number to Login'
                input_filter: 'int'
                input_type: 'number'
                font_size: '22sp'
                size_hint_y: None
                height: "70dp"
                halign: 'center'
                multiline: False
                background_color: 0.9, 0.95, 1, 0.9
                
            Button:
                text: 'SECURE LOGIN'
                font_size: '22sp'
                bold: True
                background_color: 0.0, 0.6, 0.8, 0.9
                size_hint_y: None
                height: "65dp"
                on_press: root.smart_login()
            Label:
                id: error_msg
                text: ''
                color: 1, 0.3, 0.3, 1
                bold: True
            Widget:
                size_hint_y: 1

<PrincipalDashboard>:
    name: 'principal_dash'
    on_enter: root.check_notice()
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.0, 0.6, 0.8, 0.3
            Rectangle:
                pos: self.pos[0], self.size[1] - dp(80)
                size: self.size[0], dp(80)
        BoxLayout:
            size_hint_y: None
            height: "80dp"
            padding: "15dp"
            Label:
                text: 'Principal Dashboard'
                font_size: '24sp'
                bold: True
                color: 0.8, 1, 1, 1
        ScrollView:
            GridLayout:
                cols: 1
                padding: "20dp"
                spacing: "15dp"
                size_hint_y: None
                height: self.minimum_height
                
                Button:
                    text: '1. Enter Marks / Update'
                    font_size: '18sp'
                    bold: True
                    background_color: 0.0, 0.7, 0.5, 0.9
                    size_hint_y: None
                    height: "70dp"
                    on_press: root.manager.current = 'marks_entry'
                
                Button:
                    text: '2. Teacher Marks Entry Status'
                    font_size: '18sp'
                    bold: True
                    background_color: 0.0, 0.5, 0.8, 0.9
                    size_hint_y: None
                    height: "70dp"
                    on_press: root.manager.current = 'teacher_status'

                Button:
                    text: '3. Data Reset Panel'
                    font_size: '18sp'
                    bold: True
                    background_color: 0.8, 0.2, 0.3, 0.9
                    size_hint_y: None
                    height: "70dp"
                    on_press: root.manager.current = 'reset_screen'

                Button:
                    text: '4. Subject & Teacher Mapping'
                    font_size: '18sp'
                    bold: True
                    background_color: 0.6, 0.2, 0.8, 0.9
                    size_hint_y: None
                    height: "70dp"
                    on_press: root.manager.current = 'subject_mapping'

                Button:
                    text: '5. ➕ Add New Student (Shala Darpan)'
                    font_size: '18sp'
                    bold: True
                    background_color: 0.1, 0.6, 0.4, 0.9
                    size_hint_y: None
                    height: "70dp"
                    on_press: root.manager.current = 'add_student'

                Button:
                    text: '6. 🗑️ Remove Student (Shala Darpan)'
                    font_size: '18sp'
                    bold: True
                    background_color: 0.8, 0.2, 0.2, 0.9
                    size_hint_y: None
                    height: "70dp"
                    on_press: root.manager.current = 'remove_student'

                Button:
                    text: '🔄 SYNC ALL STUDENTS DATA'
                    font_size: '18sp'
                    bold: True
                    background_color: 0.1, 0.5, 0.8, 0.9
                    size_hint_y: None
                    height: "70dp"
                    on_press: root.sync_rosters()

                Widget:
                    size_hint_y: None
                    height: "5dp"
                Button:
                    text: 'LOG OUT'
                    font_size: '18sp'
                    bold: True
                    size_hint_y: None
                    height: "60dp"
                    background_color: 0.3, 0.3, 0.4, 0.9
                    on_press: app.logout()

<TeacherDashboard>:
    name: 'teacher_dash'
    on_enter: root.check_notice()
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.0, 0.5, 0.8, 0.3
            Rectangle:
                pos: self.pos[0], self.size[1] - dp(80)
                size: self.size[0], dp(80)
        BoxLayout:
            size_hint_y: None
            height: "80dp"
            padding: "15dp"
            Label:
                text: 'Teacher Dashboard'
                font_size: '24sp'
                bold: True
                color: 0.8, 1, 1, 1
        GridLayout:
            cols: 1
            padding: "25dp"
            spacing: "20dp"
            Button:
                text: 'Enter Marks / Update'
                font_size: '18sp'
                bold: True
                background_color: 0.0, 0.7, 0.6, 0.9
                size_hint_y: None
                height: "80dp"
                on_press: root.manager.current = 'marks_entry'
                
            Button:
                text: '🔄 SYNC ALL STUDENTS DATA'
                font_size: '18sp'
                bold: True
                background_color: 0.1, 0.5, 0.8, 0.9
                size_hint_y: None
                height: "80dp"
                on_press: root.sync_rosters()
                
            Widget:
                size_hint_y: 1
            Button:
                text: 'LOG OUT'
                size_hint_y: None
                height: "60dp"
                background_color: 0.8, 0.2, 0.3, 0.9
                on_press: app.logout()

<AddStudentScreen>:
    name: 'add_student'
    BoxLayout:
        orientation: 'vertical'
        padding: "10dp"
        spacing: "10dp"
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            Button:
                text: '< Back'
                size_hint_x: 0.25
                background_color: 0.8, 0.2, 0.3, 0.9
                on_press: root.manager.current = 'principal_dash'
            Label:
                text: '➕ ADD NEW STUDENT'
                font_size: '20sp'
                bold: True
                color: 0.5, 0.9, 1.0, 1

        ScrollView:
            GridLayout:
                cols: 1
                spacing: "15dp"
                size_hint_y: None
                height: self.minimum_height
                padding: "5dp"

                Spinner:
                    id: class_spin
                    text: 'Select Class'
                    values: ('1', '2', '3', '4', '6', '7', '9', '11')
                    size_hint_y: None
                    height: "60dp"
                    background_color: 0.0, 0.5, 0.7, 0.9

                SmoothInput:
                    id: inp_srno
                    hint_text: 'SR No (Scholar No)'
                    size_hint_y: None
                    height: "60dp"

                TextInput:
                    id: inp_name
                    hint_text: 'Student Name'
                    font_size: '18sp'
                    halign: 'center'
                    multiline: False
                    size_hint_y: None
                    height: "60dp"

                TextInput:
                    id: inp_father
                    hint_text: 'Father Name'
                    font_size: '18sp'
                    halign: 'center'
                    multiline: False
                    size_hint_y: None
                    height: "60dp"

                TextInput:
                    id: inp_mother
                    hint_text: 'Mother Name'
                    font_size: '18sp'
                    halign: 'center'
                    multiline: False
                    size_hint_y: None
                    height: "60dp"

                SmoothInput:
                    id: inp_dob
                    hint_text: 'DOB (DD-MM-YYYY)'
                    size_hint_y: None
                    height: "60dp"

                SmoothInput:
                    id: inp_roll
                    hint_text: 'Class Roll No'
                    size_hint_y: None
                    height: "60dp"

                Button:
                    text: '💾 SAVE TO SHALA DARPAN'
                    font_size: '20sp'
                    bold: True
                    background_color: 0.0, 0.8, 0.4, 0.9
                    size_hint_y: None
                    height: "70dp"
                    on_press: root.save_student()

<RemoveStudentScreen>:
    name: 'remove_student'
    BoxLayout:
        orientation: 'vertical'
        padding: "5dp"
        spacing: "8dp"
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            Button:
                text: '< Back'
                size_hint_x: 0.25
                background_color: 0.8, 0.2, 0.3, 0.9
                on_press: root.manager.current = 'principal_dash'
            Label:
                text: '🗑️ REMOVE STUDENT'
                font_size: '20sp'
                bold: True
                color: 1.0, 0.4, 0.4, 1
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            spacing: "8dp"
            Spinner:
                id: class_spin
                text: 'Select Class'
                values: ('1', '2', '3', '4', '6', '7', '9', '11')
                size_hint_x: 0.6
                background_color: 0.0, 0.5, 0.7, 0.9
            Button:
                text: 'GET STUDENTS'
                size_hint_x: 0.4
                bold: True
                background_color: 0.8, 0.4, 0.1, 0.9
                on_press: root.fetch_students()
        
        BoxLayout:
            id: header_box
            size_hint_y: None
            height: "35dp"
            spacing: "4dp"
            ColorfulLabel:
                text: "Roll No"
                bg_color: 0.8, 0.3, 0.1, 0.85
                size_hint_x: 0.2
            ColorfulLabel:
                text: "Student Name"
                bg_color: 0.1, 0.4, 0.8, 0.85
                size_hint_x: 0.5
            ColorfulLabel:
                text: "Action"
                bg_color: 0.8, 0.1, 0.1, 0.85
                size_hint_x: 0.3

        ScrollView:
            GridLayout:
                id: student_list
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: "8dp"

<SubjectMappingScreen>:
    name: 'subject_mapping'
    on_enter: root.update_lists()
    BoxLayout:
        orientation: 'vertical'
        padding: "5dp"
        spacing: "8dp"
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            Button:
                text: '< Back'
                size_hint_x: 0.25
                background_color: 0.8, 0.2, 0.3, 0.9
                on_press: root.go_back()
            Label:
                text: 'SUBJECT MAPPING'
                font_size: '20sp'
                bold: True
                color: 0.5, 0.9, 1.0, 1
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            spacing: "10dp"
            Button:
                text: '👨‍🏫 ADD/DEL TEACHER'
                background_color: 0.1, 0.6, 0.8, 0.9
                bold: True
                on_press: root.manage_teachers_popup()
            Button:
                text: '👑 CHANGE ADMIN'
                background_color: 0.8, 0.4, 0.1, 0.9
                bold: True
                on_press: root.change_admin_popup()
                
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            spacing: "8dp"
            Spinner:
                id: class_spin
                text: 'Select Class'
                values: ('1', '2', '3', '4', '6', '7', '9', '11')
                size_hint_x: 0.6
                background_color: 0.0, 0.5, 0.7, 0.9
            Button:
                text: 'GET DETAILS'
                size_hint_x: 0.4
                bold: True
                background_color: 0.8, 0.4, 0.1, 0.9
                on_press: root.load_details()
            
        BoxLayout:
            id: map_header
            size_hint_y: None
            height: "0dp"
            opacity: 0
            spacing: "4dp"
            ColorfulLabel:
                text: "Subject Name"
                bg_color: 0.1, 0.4, 0.8, 0.9
                size_hint_x: 0.4
            ColorfulLabel:
                text: "Teacher Name"
                bg_color: 0.1, 0.6, 0.4, 0.9
                size_hint_x: 0.4
            ColorfulLabel:
                text: "Action"
                bg_color: 0.8, 0.3, 0.1, 0.9
                size_hint_x: 0.2

        ScrollView:
            GridLayout:
                id: mapping_list
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: "8dp"
                
        Button:
            text: '🔄 SYNC DATA TO RESULT SHEETS'
            size_hint_y: None
            height: "60dp"
            bold: True
            font_size: '16sp'
            background_color: 0.0, 0.8, 0.4, 0.9
            on_press: root.push_to_excel()

<ResetScreen>:
    name: 'reset_screen'
    BoxLayout:
        orientation: 'vertical'
        padding: "15dp"
        spacing: "20dp"
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            Button:
                text: '< Back'
                size_hint_x: 0.25
                background_color: 0.3, 0.3, 0.4, 0.9
                on_press: root.go_back()
            Label:
                text: 'Master Reset Panel'
                font_size: '20sp'
                bold: True
                color: 1, 0.3, 0.3, 1
        
        Label:
            text: 'WARNING: This will ask Google Sheet to erase marks.'
            color: 1, 0.3, 0.3, 1
            bold: True
            halign: 'center'
            size_hint_y: None
            height: "60dp"
        Spinner:
            id: class_spin
            text: 'Select Class'
            values: ('1', '2', '3', '4', '6', '7', '9', '11')
            background_color: 0.0, 0.5, 0.7, 0.9
            size_hint_y: None
            height: "60dp"
        Spinner:
            id: subject_spin
            text: 'Select Option'
            values: ('*** ALL SUBJECTS ***', 'Hindi', 'English', 'Maths', 'Sanskrit', 'Science', 'Social Science', 'EVS', 'Work Experience', 'Art Education', 'Health & Physical Edu.', 'Attendance')
            background_color: 0.8, 0.4, 0.1, 0.9
            size_hint_y: None
            height: "60dp"
        Button:
            text: 'PROCEED TO DELETE'
            bold: True
            font_size: '20sp'
            size_hint_y: None
            height: "70dp"
            background_color: 0.9, 0.1, 0.1, 0.9
            on_press: root.confirm_reset()
        Label:
            id: msg_lbl
            text: ''
            color: 0.2, 0.8, 0.2, 1
            bold: True
        Widget:
            size_hint_y: 1

<TeacherStatusScreen>:
    name: 'teacher_status'
    BoxLayout:
        orientation: 'vertical'
        padding: "10dp"
        spacing: "10dp"
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            Button:
                text: '< Back'
                size_hint_x: 0.25
                background_color: 0.8, 0.2, 0.2, 0.9
                on_press: root.manager.current = 'principal_dash'
            Label:
                text: 'Teacher Marks Entry Status'
                font_size: '20sp'
                bold: True
                color: 0.0, 0.9, 1.0, 1
                
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            spacing: "5dp"
            Button:
                text: 'FETCH STATUS'
                bold: True
                background_color: 0.0, 0.6, 0.8, 0.9
                on_press: root.fetch_status()
            Button:
                text: '📄 OPEN PDF'
                bold: True
                background_color: 0.8, 0.3, 0.1, 0.9
                on_press: root.open_pdf_report()
            Button:
                text: '📤 SHARE PDF'
                bold: True
                background_color: 0.2, 0.8, 0.2, 0.9
                on_press: root.share_pdf_report()
                
        ScrollView:
            GridLayout:
                id: status_list
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: "8dp"

<MarksEntryScreen>:
    name: 'marks_entry'
    on_enter: root.on_enter_screen()
    BoxLayout:
        orientation: 'vertical'
        padding: "5dp"
        spacing: "8dp"
        
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            Button:
                text: '< Back'
                size_hint_x: 0.25
                background_color: 0.8, 0.2, 0.3, 0.9
                on_press: root.go_back()
            Label:
                text: 'MARKS ENTRY PANEL' 
                font_size: '22sp'
                bold: True
                color: 0.5, 0.9, 1.0, 1
                
        GridLayout:
            cols: 2
            size_hint_y: None
            height: "120dp"
            spacing: "8dp"
            Spinner:
                id: class_spin
                text: 'Select Class'
                background_color: 0.0, 0.5, 0.7, 0.85
                on_text: root.on_class_change()
            Spinner:
                id: subject_spin
                text: 'Select Subject'
                background_color: 0.0, 0.5, 0.7, 0.85
                on_text: root.update_options()
            Spinner:
                id: exam_spin
                text: 'Select Exam'
                background_color: 0.0, 0.5, 0.7, 0.85
                on_text: root.update_options()
            Spinner:
                id: part_spin
                text: 'Select Type'
                background_color: 0.0, 0.5, 0.7, 0.85
                on_text: root.update_options()
            
        Button:
            text: 'FETCH STUDENTS & MARKS'
            bold: True
            size_hint_y: None
            height: "55dp"
            background_color: 0.0, 0.7, 0.5, 0.9
            on_press: root.start_fetch()
        
        BoxLayout:
            id: header_box
            size_hint_y: None
            height: "35dp"
            spacing: "4dp"

        ScrollView:
            id: scroll_view
            GridLayout:
                id: student_list
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: "8dp"
                padding: "2dp"
        
        Label:
            id: status_msg_lbl
            text: ''
            color: 1, 1, 0.2, 1
            bold: True
            font_size: '16sp'
            size_hint_y: None
            height: "0dp"
            opacity: 0
            
        Button:
            text: 'SAVE / UPDATE ALL MARKS'
            bold: True
            font_size: '20sp'
            size_hint_y: None
            height: "65dp"
            background_color: 1, 0.4, 0.0, 0.9
            on_press: root.save_all_marks()
            
        Button:
            text: 'RESET SELECTED MARKS'
            bold: True
            font_size: '18sp'
            size_hint_y: None
            height: "55dp"
            background_color: 0.9, 0.1, 0.1, 0.9
            on_press: root.confirm_reset_activity()
'''

class LoginScreen(Screen):
    def preload_data(self):
        threading.Thread(target=self.do_preload).start()
        
    def do_preload(self):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            res = urllib.request.urlopen(urllib.request.Request(f"{SCRIPT_URL}?action=get_teachers"), context=ctx, timeout=10)
            data = json.loads(res.read().decode("utf-8"))
            save_cache("teachers_master_data", data)
            Clock.schedule_once(lambda dt: self.set_msg("System Ready!"), 0)
        except:
            pass
            
    def set_msg(self, msg):
        self.ids.error_msg.text = msg
        self.ids.error_msg.color = (0,1,0,1)
    def set_err(self, msg):
        self.ids.error_msg.text = msg
        self.ids.error_msg.color = (1,0.3,0.3,1)

    def smart_login(self):
        mob = self.ids.mobile_input.text.strip()
        if len(mob) < 10:
            self.set_err("Kripya Sahi Mobile Number Dalein!")
            return
        self.set_msg("Authenticating...")
        threading.Thread(target=self.verify, args=(mob,)).start()

    def verify(self, mob):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            res = urllib.request.urlopen(urllib.request.Request(f"{SCRIPT_URL}?action=get_teachers"), context=ctx, timeout=20)
            data = json.loads(res.read().decode("utf-8"))
            save_cache("teachers_master_data", data)
            
            is_admin = False
            t_name = ""
            found = False
            
            # STRICT TEACHER MASTER COLUMNS
            # Col 0: Name, Col 1: Mobile, Col 2: Class, Col 3: Subject
            for t in data:
                keys = list(t.keys())
                if len(keys) >= 4:
                    n = str(t[keys[0]]).strip()
                    m = str(t[keys[1]]).strip()
                    c = str(t[keys[2]]).strip().upper()
                    if m == mob:
                        found = True
                        t_name = n
                        if c == "ADMIN": is_admin = True
                        break
            
            # SUPER ADMIN FAILSAFE
            if mob == "7023475941":
                is_admin = True 
                if not t_name: t_name = "Master Admin"
                found = True
                
            if found:
                App.get_running_app().store.put('user', mobile=mob, is_admin=is_admin, name=t_name)
                Clock.schedule_once(lambda dt: self.go_dash(is_admin), 0)
            else:
                Clock.schedule_once(lambda dt: self.set_err("Mobile Number Not Found!"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.set_err(f"Net Error: {str(e)[:20]}"), 0)

    def go_dash(self, is_admin):
        self.ids.error_msg.text = ""
        self.ids.mobile_input.text = ""
        self.manager.current = 'principal_dash' if is_admin else 'teacher_dash'

class AddStudentScreen(Screen):
    def save_student(self):
        cls = self.ids.class_spin.text
        srno = self.ids.inp_srno.text.strip()
        name = self.ids.inp_name.text.strip()
        fname = self.ids.inp_father.text.strip()
        mname = self.ids.inp_mother.text.strip()
        dob = self.ids.inp_dob.text.strip()
        roll = self.ids.inp_roll.text.strip()

        if 'Select' in cls or not name or not roll:
            show_alert_popup("ERROR", "Class, Name aur Roll No jaruri hain!")
            return

        payload = {
            "action": "add_student", "class_name": cls, "srno": srno, "name": name,
            "father": fname, "mother": mname, "dob": dob, "roll": roll
        }

        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text="⏳ Please Wait, Saving to Shala Darpan...\nDo NOT close the app.", bold=True, halign='center'))
        popup = Popup(title="SAVING...", content=box, size_hint=(0.8, 0.3), auto_dismiss=False)
        popup.open()

        threading.Thread(target=self.post_data, args=(payload, popup)).start()

    def post_data(self, payload, popup):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(SCRIPT_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
            urllib.request.urlopen(req, context=ctx, timeout=40)
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: self.clear_fields(), 0)
            Clock.schedule_once(lambda dt: show_success_popup("SUCCESS", "Student Added & Auto-Sorted Successfully!"), 0.5)
        except Exception as e:
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: show_error_popup(f"ERROR: {str(e)}"), 0.5)

    def clear_fields(self):
        self.ids.inp_srno.text = ""
        self.ids.inp_name.text = ""
        self.ids.inp_father.text = ""
        self.ids.inp_mother.text = ""
        self.ids.inp_dob.text = ""
        self.ids.inp_roll.text = ""

class RemoveStudentScreen(Screen):
    def fetch_students(self):
        cls = self.ids.class_spin.text
        if 'Select' in cls:
            show_alert_popup("ERROR", "Please select a class!")
            return
            
        self.ids.student_list.clear_widgets()
        self.ids.student_list.add_widget(Label(text="Fetching Students...", color=(0,1,1,1)))
        
        threading.Thread(target=self.get_data, args=(cls,)).start()
        
    def get_data(self, cls):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(f"{SCRIPT_URL}?action=sync_all_rosters")
            res = urllib.request.urlopen(req, context=ctx, timeout=40)
            data = json.loads(res.read().decode("utf-8"))
            save_cache("master_roster", data)
            
            if cls in data and len(data[cls]) > 0:
                Clock.schedule_once(lambda dt: self.show_students(cls, data[cls]), 0)
            else:
                Clock.schedule_once(lambda dt: self.show_error("No students found in this class!"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(str(e)), 0)
            
    def show_error(self, msg):
        self.ids.student_list.clear_widgets()
        self.ids.student_list.add_widget(Label(text=f"Error: {msg}", color=(1,0,0,1)))

    def show_students(self, cls, roster_data):
        self.ids.student_list.clear_widgets()
        for st in roster_data:
            name = st.get('Name', '')
            roll = st.get('Roll', '')
            
            row = BoxLayout(size_hint_y=None, height="50dp", spacing="4dp")
            l_roll = ColorfulLabel(text=str(roll), size_hint_x=0.2, bg_color=[0.8, 0.3, 0.1, 0.85])
            l_name = ColorfulLabel(text=name, size_hint_x=0.5, bg_color=[0.1, 0.4, 0.8, 0.85], halign='left', valign='center')
            l_name.bind(size=l_name.setter('text_size'))
            
            btn_del = Button(text="🗑️ DELETE", size_hint_x=0.3, background_color=(0.9, 0.1, 0.1, 1), bold=True)
            btn_del.bind(on_release=lambda instance, c=cls, r=roll, n=name: self.confirm_delete(c, r, n))
            
            row.add_widget(l_roll); row.add_widget(l_name); row.add_widget(btn_del)
            self.ids.student_list.add_widget(row)

    def confirm_delete(self, cls, roll, name):
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text=f"WARNING: Completely REMOVE\n{name} (Roll: {roll})\nfrom Shala Darpan?", color=(1,0.2,0.2,1), bold=True, halign='center'))
        btn_box = BoxLayout(size_hint_y=None, height="50dp", spacing="10dp")
        btn_cancel = Button(text="CANCEL", background_color=(0.5,0.5,0.5,1))
        btn_delete = Button(text="YES, DELETE", background_color=(1,0,0,1), bold=True)
        btn_box.add_widget(btn_cancel); btn_box.add_widget(btn_delete)
        box.add_widget(btn_box)
        
        popup = Popup(title="CONFIRM REMOVE", content=box, size_hint=(0.85, 0.4), auto_dismiss=False)
        btn_cancel.bind(on_release=popup.dismiss)
        
        def proceed(inst):
            popup.dismiss()
            self.do_delete(cls, roll, name)
            
        btn_delete.bind(on_release=proceed)
        popup.open()

    def do_delete(self, cls, roll, name):
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text="⏳ Deleting Row & Adjusting Roll Nos...", bold=True, halign='center'))
        popup = Popup(title="PROCESSING...", content=box, size_hint=(0.8, 0.3), auto_dismiss=False)
        popup.open()
        
        payload = {"action": "remove_student", "class_name": cls, "roll": roll, "name": name}
        
        def run_post():
            try:
                ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(SCRIPT_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
                res = urllib.request.urlopen(req, context=ctx, timeout=40)
                resp = json.loads(res.read().decode('utf-8'))
                
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                if "error" in resp:
                    Clock.schedule_once(lambda dt: show_error_popup(f"Sheet Error: {resp['error']}"), 0.5)
                else:
                    Clock.schedule_once(lambda dt: show_success_popup("DELETED", f"{name} removed successfully!"), 0.5)
                    Clock.schedule_once(lambda dt: self.fetch_students(), 1.5)
            except Exception as e:
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                Clock.schedule_once(lambda dt: show_error_popup(f"Network Error: {str(e)}"), 0.5)
                
        threading.Thread(target=run_post).start()

class SubjectMappingScreen(Screen):
    def go_back(self):
        self.ids.map_header.opacity = 0
        self.ids.map_header.height = "0dp"
        self.ids.mapping_list.clear_widgets()
        self.manager.current = 'principal_dash'

    def update_lists(self):
        self.t_data = load_cache("teachers_master_data") or []
        names = set()
        self.admin_name = ""
        self.admin_mob = ""
        for t in self.t_data:
            keys = list(t.keys())
            if len(keys) >= 4:
                n = str(t[keys[0]])
                m = str(t[keys[1]])
                c = str(t[keys[2]]).upper()
                if c == "ADMIN":
                    self.admin_name = n
                    self.admin_mob = m
                elif n:
                    names.add(n)
        self.all_teachers = sorted(list(names))

    def load_details(self):
        cls = self.ids.class_spin.text
        self.ids.mapping_list.clear_widgets()
        if 'Select' in cls:
            show_alert_popup("ERROR", "Please select a class first!")
            return
            
        self.ids.map_header.height = "35dp"
        self.ids.map_header.opacity = 1
        
        count = 0
        for t in self.t_data:
            keys = list(t.keys())
            if len(keys) < 4: continue
            c = str(t[keys[2]])
            if c.endswith('.0'): c = c[:-2] 
            
            if c == cls:
                count += 1
                sub = str(t[keys[3]])
                tname = str(t[keys[0]])
                
                row = BoxLayout(size_hint_y=None, height="50dp", spacing="4dp")
                l_sub = ColorfulLabel(text=sub, size_hint_x=0.4, bg_color=[0.1, 0.4, 0.8, 0.85])
                l_tchr = ColorfulLabel(text=tname if tname else "---", size_hint_x=0.4, bg_color=[0.2, 0.2, 0.2, 0.9])
                
                btn_edit = Button(text="✏️ EDIT", size_hint_x=0.2, background_color=(0.9, 0.6, 0.1, 1), bold=True)
                btn_edit.bind(on_release=lambda instance, s=sub, l=l_tchr: self.edit_teacher_popup(cls, s, l))
                
                row.add_widget(l_sub); row.add_widget(l_tchr); row.add_widget(btn_edit)
                self.ids.mapping_list.add_widget(row)
                
        if count == 0:
            self.ids.mapping_list.add_widget(Label(text=f"Class {cls} ka data nahi mila!\nCheck your Google Sheet.", color=(1,0.2,0.2,1), bold=True))

    def edit_teacher_popup(self, cls_name, sub_name, lbl_widget):
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text=f"Assign Teacher for:\nClass {cls_name} - {sub_name}", bold=True, halign="center"))
        spin = Spinner(text="Select New Teacher", values=self.all_teachers, size_hint_y=None, height="60dp", background_color=(0,0.5,0.8,1))
        btn_close = Button(text="CANCEL", background_color=(0.5,0.5,0.5,1), size_hint_y=None, height="50dp")
        
        box.add_widget(spin); box.add_widget(btn_close)
        popup = Popup(title="✏️ CHOOSE TEACHER", content=box, size_hint=(0.85, 0.45), auto_dismiss=False)
        btn_close.bind(on_release=popup.dismiss)
        
        def on_spin_select(spinner, text):
            if text != "Select New Teacher":
                lbl_widget.text = text
                lbl_widget.bg_color = [0, 0.8, 0.2, 1] 
                for t in self.t_data:
                    keys = list(t.keys())
                    c = str(t[keys[2]])
                    if c.endswith('.0'): c = c[:-2]
                    s = str(t[keys[3]])
                    if c == cls_name and s == sub_name:
                        t[keys[0]] = text
                save_cache("teachers_master_data", self.t_data)
                
                payload = {"action": "save_single_mapping", "class_name": cls_name, "subject": sub_name, "teacher_name": text}
                threading.Thread(target=self.post_data_silent, args=(payload, "Teacher Assigned Successfully!")).start()
                popup.dismiss()
                
        spin.bind(text=on_spin_select)
        popup.open()

    def push_to_excel(self):
        payload = {"action": "push_mappings_to_excel"}
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text="⏳ Please Wait, Syncing to Excel...\nThis takes 10-15 seconds.", bold=True, halign='center'))
        popup = Popup(title="SYNCING...", content=box, size_hint=(0.8, 0.3), auto_dismiss=False)
        popup.open()
        threading.Thread(target=self.post_data_sync, args=(payload, "EXCEL FILES UPDATED SUCCESSFULLY!", popup)).start()

    def manage_teachers_popup(self):
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text="ADD NEW TEACHER:", bold=True, color=(1,1,1,1), size_hint_y=None, height="30dp"))
        inp = TextInput(hint_text="Teacher Name", font_size='18sp', halign='center', multiline=False, size_hint_y=None, height="50dp")
        inp_mob = SmoothInput(hint_text="Mobile No. (For Login)", size_hint_y=None, height="50dp")
        btn_add = Button(text="ADD TEACHER", background_color=(0,0.8,0.3,1), bold=True, size_hint_y=None, height="50dp")
        box.add_widget(inp); box.add_widget(inp_mob); box.add_widget(btn_add)
        
        box.add_widget(Label(text="REMOVE TEACHER:", bold=True, color=(1,0.5,0.5,1), size_hint_y=None, height="30dp"))
        spin = Spinner(text="Select to Remove", values=self.all_teachers, size_hint_y=None, height="50dp")
        btn_rem = Button(text="REMOVE TEACHER", background_color=(0.9,0.1,0.1,1), bold=True, size_hint_y=None, height="50dp")
        box.add_widget(spin); box.add_widget(btn_rem)
        
        btn_close = Button(text="CLOSE", background_color=(0.5,0.5,0.5,1), size_hint_y=None, height="50dp")
        box.add_widget(btn_close)
        
        popup = Popup(title="Manage Teachers", content=box, size_hint=(0.95, 0.95), auto_dismiss=False)
        btn_close.bind(on_release=popup.dismiss)
        
        def do_add(inst):
            if inp.text.strip() and inp_mob.text.strip():
                popup.dismiss()
                payload = {"action": "manage_teacher", "sub_action": "add", "teacher_name": inp.text.strip(), "teacher_mobile": inp_mob.text.strip()}
                threading.Thread(target=self.post_data_silent, args=(payload, "Teacher Added Successfully!")).start()
        btn_add.bind(on_release=do_add)
        
        def do_rem(inst):
            if spin.text != "Select to Remove":
                popup.dismiss()
                payload = {"action": "manage_teacher", "sub_action": "remove", "teacher_name": spin.text}
                threading.Thread(target=self.post_data_silent, args=(payload, "Teacher Removed Successfully!")).start()
        btn_rem.bind(on_release=do_rem)
        popup.open()

    def change_admin_popup(self):
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        inp_name = TextInput(text=self.admin_name, hint_text="New Admin Name", font_size='18sp', halign='center', multiline=False, size_hint_y=None, height="50dp")
        inp_mob = SmoothInput(text=self.admin_mob, hint_text="New Admin Mobile", size_hint_y=None, height="50dp")
        btn_save = Button(text="UPDATE ADMIN", background_color=(0,0.7,0.4,1), bold=True, size_hint_y=None, height="50dp")
        btn_close = Button(text="CANCEL", background_color=(0.5,0.5,0.5,1), size_hint_y=None, height="50dp")
        box.add_widget(inp_name); box.add_widget(inp_mob); box.add_widget(btn_save); box.add_widget(btn_close)
        
        popup = Popup(title="Change Principal/Admin", content=box, size_hint=(0.9, 0.5), auto_dismiss=False)
        btn_close.bind(on_release=popup.dismiss)
        
        def do_save(inst):
            if inp_name.text.strip() and inp_mob.text.strip():
                popup.dismiss()
                payload = {"action": "update_admin", "admin_name": inp_name.text.strip(), "admin_mobile": inp_mob.text.strip()}
                threading.Thread(target=self.post_data_silent, args=(payload, "Admin Details Updated Successfully!")).start()
        btn_save.bind(on_release=do_save)
        popup.open()

    def post_data_silent(self, payload, msg="SAVED SUCCESSFULLY"):
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text="⏳ Please Wait, Saving Data...", bold=True, halign='center'))
        popup = Popup(title="PROCESSING...", content=box, size_hint=(0.8, 0.3), auto_dismiss=False)
        Clock.schedule_once(lambda dt: popup.open(), 0)
        
        def run_post():
            try:
                ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(SCRIPT_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
                urllib.request.urlopen(req, context=ctx, timeout=40)
                
                req2 = urllib.request.Request(f"{SCRIPT_URL}?action=get_teachers")
                res2 = urllib.request.urlopen(req2, context=ctx, timeout=20)
                data = json.loads(res2.read().decode("utf-8"))
                save_cache("teachers_master_data", data)
                
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                if msg: Clock.schedule_once(lambda dt: show_success_popup("SUCCESS", msg), 0)
                Clock.schedule_once(lambda dt: self.update_lists(), 1.5)
            except Exception as e:
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                Clock.schedule_once(lambda dt: show_error_popup(f"ERROR: {str(e)}"), 0)
        threading.Thread(target=run_post).start()

    def post_data_sync(self, payload, msg, popup):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(SCRIPT_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
            urllib.request.urlopen(req, context=ctx, timeout=60)
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: show_success_popup("SUCCESS", msg), 0.5)
        except Exception as e:
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: show_error_popup(f"ERROR: {str(e)}"), 0.5)

class BaseDashboard(Screen):
    def check_notice(self):
        app = App.get_running_app()
        if not getattr(app, 'notice_shown', False):
            msg = "🚨 IMPORTANT NOTICE 🚨\n\nMarks feed karne se pehle check kar lein ki sabhi students ka naam list me aa raha hai ya nahi.\n\nAgar koi naya student add hua hai ya list update nahi hai, to Dashboard par '🔄 SYNC ALL STUDENTS DATA' button dabakar list refresh zaroor karein!"
            box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
            lbl = Label(text=msg, color=(0.2, 1.0, 0.2, 1), font_size='18sp', halign='center', valign='middle', bold=True)
            lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None))) 
            box.add_widget(lbl)
            btn_close = Button(text="OK, I UNDERSTAND", background_color=(0.1, 0.7, 0.3, 1), bold=True, size_hint_y=None, height="60dp")
            box.add_widget(btn_close)
            popup = Popup(title="Sanskrit App Update", title_color=(1,1,1,1), content=box, size_hint=(0.9, 0.6), auto_dismiss=False, background_color=(0.1, 0.2, 0.3, 0.9))
            btn_close.bind(on_release=popup.dismiss)
            popup.open()
            app.notice_shown = True

    def sync_rosters(self):
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        lbl = Label(text="Downloading Master Data from Ocean...\n\nPlease wait 10-15 seconds.", color=(0.5,1,1,1), font_size='18sp', bold=True, halign='center')
        lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None))) 
        box.add_widget(lbl)
        popup = Popup(title="🔄 SYNCING...", title_color=(1,1,1,1), content=box, size_hint=(0.8, 0.4), auto_dismiss=False)
        popup.open()
        threading.Thread(target=self.do_sync, args=(popup,)).start()
        
    def do_sync(self, popup):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = f"{SCRIPT_URL}?action=sync_all_rosters"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx, timeout=60) as res:
                raw_data = res.read().decode('utf-8')
                data = json.loads(raw_data)
                if isinstance(data, dict) and "error" in data: raise Exception(data["error"])
                save_cache("master_roster", data)
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                Clock.schedule_once(lambda dt: show_success_popup("✅ SYNC COMPLETE", "All classes data successfully downloaded!"), 0.5)
        except Exception as err:
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: show_error_popup("SYNC FAILED:\n" + str(err)), 0.5)

class PrincipalDashboard(BaseDashboard): pass
class TeacherDashboard(BaseDashboard): pass

class ResetScreen(Screen):
    def go_back(self):
        self.ids.msg_lbl.text = ""
        self.manager.current = 'principal_dash'
    def show_msg(self, text, color):
        self.ids.msg_lbl.color = color; self.ids.msg_lbl.text = text
    def confirm_reset(self):
        cls = self.ids.class_spin.text; subj = self.ids.subject_spin.text
        if 'Select' in cls or 'Select' in subj: return self.show_msg("Select both!", (1,0,0,1))
        box = BoxLayout(orientation='vertical', padding="10dp", spacing="10dp")
        box.add_widget(Label(text=f"WARNING: Erase {subj} for Class {cls}?", color=(1,0,0,1), bold=True))
        btn_box = BoxLayout(size_hint_y=None, height="50dp", spacing="10dp")
        btn_no = Button(text="CANCEL", background_color=(0.5,0.5,0.5,1))
        btn_yes = Button(text="DELETE", background_color=(1,0,0,1), bold=True)
        btn_box.add_widget(btn_no); btn_box.add_widget(btn_yes); box.add_widget(btn_box)
        popup = Popup(title="CONFIRM DELETION", title_color=(1,0,0,1), content=box, size_hint=(0.8, 0.4))
        btn_no.bind(on_release=popup.dismiss)
        btn_yes.bind(on_release=lambda x: [popup.dismiss(), self.execute_reset()])
        popup.open()
        
    def execute_reset(self):
        cls = self.ids.class_spin.text; subj = self.ids.subject_spin.text
        reset_type = "master" if "MASTER" in subj else "subject"
        self.show_msg("Sending Command...", (0,0.8,0.8,1))
        payload = {"action": "reset_marks", "class_name": cls, "reset_type": reset_type, "subject": subj}
        threading.Thread(target=self.post_reset, args=(payload,)).start()

    def post_reset(self, payload):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(SCRIPT_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, context=ctx, timeout=30) as res:
                resp = json.loads(res.read().decode('utf-8'))
                if "error" in resp: Clock.schedule_once(lambda dt: show_error_popup("ERROR:\n" + resp["error"]), 0)
                else: Clock.schedule_once(lambda dt: self.show_msg("Reset Success!", (0,1,0,1)), 0)
        except Exception as err:
            Clock.schedule_once(lambda dt: show_error_popup("ERROR:\n" + str(err)), 0)

class TeacherStatusScreen(Screen):
    
    # 🚀 REAL NATIVE ANDROID PDF GENERATION (ReportLab)
    def open_pdf_report(self):
        if not hasattr(self, 'live_data') or not self.live_data:
            show_alert_popup("ERROR", "Please 'FETCH LIVE STATUS' first to generate PDF.")
            return
            
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text="⏳ Generating Professional A4 PDF...", bold=True, halign='center'))
        popup = Popup(title="GENERATING REPORT...", content=box, size_hint=(0.8, 0.3), auto_dismiss=False)
        popup.open()
        
        threading.Thread(target=self.build_and_open_pdf, args=(popup,)).start()

    def build_and_open_pdf(self, popup):
        try:
            app_dir = App.get_running_app().user_data_dir
            pdf_path = os.path.join(app_dir, "Teacher_Marks_Entry_Report.pdf")
            
            font_filename = "NotoSansDevanagari-Regular.ttf"
            font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), font_filename)
            
            font_registered = False
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('HindiFont', font_path))
                font_registered = True
            font_name = 'HindiFont' if font_registered else 'Helvetica'

            doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            
            title_style = ParagraphStyle(name='Title', fontName=font_name, fontSize=18, alignment=1, spaceAfter=20)
            elements.append(Paragraph("Teacher Marks Entry Status Report", title_style))
            
            table_data = [["Teacher Name", "Class", "Subject", "Status"]]
            for item in self.live_data:
                keys = list(item.keys())
                teacher = str(item.get("शिक्षक", item.get("Teacher Name", item.get(keys[0], ""))))
                cls = str(item.get("कक्षा", item.get("Class", item.get(keys[1], ""))))
                sub = str(item.get("विषय", item.get("Subject", item.get(keys[2], ""))))
                status = str(item.get("स्थिति", item.get("Status", item.get(keys[3], ""))))
                
                table_data.append([Paragraph(teacher, ParagraphStyle('t', fontName=font_name)), 
                                   Paragraph(cls, ParagraphStyle('c', fontName=font_name)), 
                                   Paragraph(sub, ParagraphStyle('s', fontName=font_name)), 
                                   Paragraph(status, ParagraphStyle('st', fontName=font_name))])

            t = Table(table_data, colWidths=[160, 60, 160, 100])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#34495e")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 10),
                ('TOPPADDING', (0,0), (-1,0), 10),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f4f7f6")),
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#dddddd"))
            ]))
            elements.append(t)
            doc.build(elements)
            
            absolute_path = os.path.abspath(pdf_path)
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: self.trigger_android_pdf_viewer(absolute_path), 0.5)

        except Exception as e:
            traceback.print_exc()
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: show_error_popup(f"PDF GENERATION ERROR:\n{str(e)}"), 0.5)

    def trigger_android_pdf_viewer(self, abs_pdf_path):
        if platform == 'android':
            try:
                from jnius import autoclass, cast
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                
                StrictMode = autoclass('android.os.StrictMode')
                builder = StrictMode.VmPolicy.Builder()
                StrictMode.setVmPolicy(builder.build())
                
                file_obj = File(abs_pdf_path)
                uri = Uri.fromFile(file_obj)
                
                intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(uri, "application/pdf")
                intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_GRANT_READ_URI_PERMISSION)
                
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                activity.startActivity(intent)
            except Exception as e:
                show_error_popup(f"PDF Saved to:\n{abs_pdf_path}\nCould not open viewer: {str(e)}")
        else:
            webbrowser.open('file://' + abs_pdf_path)

    def share_pdf_report(self):
        app_dir = App.get_running_app().user_data_dir
        pdf_path = os.path.join(app_dir, "Teacher_Marks_Entry_Report.pdf")
        
        if not os.path.exists(pdf_path):
            show_alert_popup("ERROR", "Pehle 'OPEN PDF' par click karke report generate karein!")
            return
            
        if platform == 'android':
            try:
                from jnius import autoclass, cast
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                
                StrictMode = autoclass('android.os.StrictMode')
                builder = StrictMode.VmPolicy.Builder()
                StrictMode.setVmPolicy(builder.build())
                
                file_obj = File(pdf_path)
                uri = Uri.fromFile(file_obj)
                
                intent = Intent(Intent.ACTION_SEND)
                intent.setType("application/pdf")
                intent.putExtra(Intent.EXTRA_STREAM, uri)
                intent.setFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                
                currentActivity = cast('android.app.Activity', autoclass('org.kivy.android.PythonActivity').mActivity)
                chooser = Intent.createChooser(intent, cast('java.lang.CharSequence', "Share Teacher Status PDF"))
                currentActivity.startActivity(chooser)
            except Exception as e:
                show_error_popup(f"Share Error:\n{str(e)}")
        else:
            show_alert_popup("NOTE", "Share feature sirf Android mobile par chalega.")

    def fetch_status(self):
        self.ids.status_list.clear_widgets()
        self.ids.status_list.add_widget(Label(text="Fetching Live Percentage from Ocean...", color=(0,1,1,1)))
        threading.Thread(target=self.get_teachers).start()
        
    def get_teachers(self):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            url = f"{SCRIPT_URL}?action=get_live_status"
            with urllib.request.urlopen(urllib.request.Request(url), context=ctx, timeout=40) as res:
                self.live_data = json.loads(res.read().decode("utf-8"))
                Clock.schedule_once(lambda dt: self.show_teachers(self.live_data), 0)
        except Exception as err:
            Clock.schedule_once(lambda dt: show_error_popup("TEACHER STATUS ERROR:\n" + str(err)), 0)

    def show_teachers(self, data):
        self.ids.status_list.clear_widgets()
        if len(data) > 0 and "error" in data[0]:
            self.ids.status_list.add_widget(Label(text=f"Error: {data[0]['error']}", color=(1,0,0,1)))
            return
            
        temp_groups = {}
        for t in data:
            name, cls_name, sub, status_val = "", "-", "-", "0%"
            for k, v in t.items():
                kl = str(k).lower().strip()
                if 'name' in kl or 'नाम' in kl or 'शिक्षक' in kl: name = str(v).strip()
                elif 'class' in kl or 'कक्षा' in kl or 'clss' in kl: cls_name = str(v).strip()
                elif 'subject' in kl or 'विषय' in kl or 'sub' in kl: sub = str(v).strip()
                elif 'status' in kl or 'स्थिति' in kl: status_val = str(v).strip()
            
            if name == "" or name == "None": continue 
            if name not in temp_groups: temp_groups[name] = {}
            uk = f"Class {cls_name} | {sub}"
            temp_groups[name][uk] = status_val

        for teacher, tasks in temp_groups.items():
            b = BoxLayout(orientation='vertical', size_hint_y=None, height=f"{35 + len(tasks)*30}dp")
            b.add_widget(Button(text=teacher, background_color=(0,0.5,0.7,0.9), size_hint_y=None, height="35dp", bold=True))
            for k, st in tasks.items():
                r = BoxLayout(size_hint_y=None, height="30dp")
                r.add_widget(Label(text=k, color=(0.8,1,1,1), size_hint_x=0.6))
                
                status_str = st
                color = (1,1,1,1)
                if '%' in status_str:
                    try:
                        val = int(status_str.replace('%','').strip())
                        if val == 0: status_str = "0% (Not Started)"; color = (1, 0.2, 0.2, 1) 
                        elif val == 100: status_str = "100% (Completed)"; color = (0.2, 1, 0.2, 1) 
                        else: status_str = f"{val}% (In Progress)"; color = (1, 0.8, 0, 1) 
                    except: pass
                
                r.add_widget(Label(text=status_str, color=color, size_hint_x=0.4, bold=True))
                b.add_widget(r)
            self.ids.status_list.add_widget(b)

class MarksEntryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_boxes = {}
        self.input_widgets = [] 
        self.current_max_marks = 0 

    def go_back(self):
        m = App.get_running_app().store.get('user')['mobile']
        self.manager.current = 'principal_dash' if App.get_running_app().store.get('user')['is_admin'] else 'teacher_dash'

    def on_enter_screen(self):
        app = App.get_running_app()
        user = app.store.get('user')
        self.is_admin = user.get('is_admin', False)
        self.t_name = user.get('name', '')
        
        t_data = load_cache("teachers_master_data") or []
        if self.is_admin:
            self.ids.class_spin.values = ('1', '2', '3', '4', '6', '7', '9', '11')
            self.my_mappings = []
        else:
            classes = set()
            self.my_mappings = []
            for t in t_data:
                keys = list(t.keys())
                if len(keys) >= 4:
                    n = str(t[keys[0]]).strip()
                    if n.lower() == self.t_name.lower() and n != "":
                        c = str(t[keys[2]]).strip()
                        s = str(t[keys[3]]).strip()
                        classes.add(c)
                        self.my_mappings.append({'class': c, 'sub': s})
            self.ids.class_spin.values = tuple(sorted(list(classes)))
            
        self.ids.class_spin.text = 'Select Class'
        self.ids.subject_spin.text = 'Select Subject'
        self.ids.exam_spin.text = 'Select Exam'
        self.ids.part_spin.text = 'Select Type'

    def auto_clear_list(self, *args):
        if hasattr(self, 'ids') and 'student_list' in self.ids:
            self.ids.student_list.clear_widgets()
            self.ids.header_box.clear_widgets()
            self.ids.status_msg_lbl.opacity = 0
            self.ids.status_msg_lbl.height = "0dp"

    def on_class_change(self, *args):
        self.auto_clear_list()
        cls = self.ids.class_spin.text
        if 'Select' in cls: return
        
        all_subs = []
        if cls in ['1', '2', '3', '4']:
            all_subs = ['Hindi', 'English', 'Maths', 'Sanskrit', 'EVS', 'Work Experience', 'Art Education', 'Health & Physical Edu.', 'Attendance']
        elif cls in ['6', '7']:
            all_subs = ['Hindi', 'English', 'Maths', 'Sanskrit', 'Science', 'Social Science', 'Work Experience', 'Art Education', 'Health & Physical Edu.', 'Attendance']
        elif cls == '9':
            all_subs = ['Hindi', 'English', 'Maths', 'Sanskrit', 'Science', 'Social Science', 'Computer', 'Art Education', 'Health & Physical Edu.', 'Attendance']
        elif cls == '11':
            all_subs = ['Hindi', 'English', 'Sanskrit Vangmay', 'Sahitya Shastra', 'History', 'Life Skills', 'Golden India', 'Attendance']
            
        if self.is_admin:
            self.ids.subject_spin.values = tuple(all_subs)
        else:
            allowed_subs = []
            for m in self.my_mappings:
                if m['class'] == cls:
                    hi_sub = m['sub'].lower()
                    for s in all_subs:
                        if s.lower() in hi_sub or hi_sub in s.lower():
                            allowed_subs.append(s); break
                    if 'हिन्दी' in hi_sub: allowed_subs.append('Hindi')
                    if 'अंग्रेजी' in hi_sub: allowed_subs.append('English')
                    if 'गणित' in hi_sub: allowed_subs.append('Maths')
                    if 'संस्कृत' in hi_sub: allowed_subs.append('Sanskrit')
                    if 'विज्ञान' in hi_sub and 'सा.' not in hi_sub: allowed_subs.append('Science')
                    if 'सा. विज्ञान' in hi_sub or 'सामाजिक' in hi_sub: allowed_subs.append('Social Science')
                    if 'पर्यावरण' in hi_sub: allowed_subs.append('EVS')
                    if 'कार्यानुभव' in hi_sub or 'supw' in hi_sub: allowed_subs.append('Work Experience')
                    if 'कला' in hi_sub: allowed_subs.append('Art Education')
                    if 'स्वास्थ्य' in hi_sub: allowed_subs.append('Health & Physical Edu.')
                    if 'वाङ्मय' in hi_sub: allowed_subs.append('Sanskrit Vangmay')
                    if 'साहित्य' in hi_sub: allowed_subs.append('Sahitya Shastra')
                    if 'इतिहास' in hi_sub: allowed_subs.append('History')
                    if 'स्वर्णिम' in hi_sub: allowed_subs.append('Golden India')
                    if 'कौशल' in hi_sub: allowed_subs.append('Life Skills')
                    if 'info' in hi_sub or 'computer' in hi_sub: allowed_subs.append('Computer')
            
            allowed_subs.append('Attendance') 
            final_subs = []
            for a in allowed_subs:
                if a not in final_subs and a in all_subs: final_subs.append(a)
            self.ids.subject_spin.values = tuple(final_subs)
            
        self.ids.subject_spin.text = 'Select Subject'
        self.ids.exam_spin.text = 'Select Exam'
        self.ids.part_spin.text = 'Select Type'

    def update_options(self, *args):
        self.auto_clear_list()
        if not hasattr(self, 'ids') or 'subject_spin' not in self.ids: return
            
        cls = self.ids.class_spin.text; subj = self.ids.subject_spin.text
        exam = self.ids.exam_spin.text; part = self.ids.part_spin.text
        max_val = 999 
        
        if 'Select' in subj: return

        if subj == 'Attendance':
            self.ids.exam_spin.values = ('Attendance',)
            self.ids.exam_spin.text = 'Attendance'; exam = 'Attendance'
            self.ids.part_spin.values = ('BOTH (Meeting & Present)',)
            self.ids.part_spin.text = 'BOTH (Meeting & Present)'; part = 'BOTH'
            max_val = 999
            
        elif cls in ['1', '2']:
            if subj in ['Hindi', 'English', 'Maths', 'Sanskrit']:
                self.ids.exam_spin.values = ('Half Yearly', 'Annual')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'Half Yearly'; exam = 'Half Yearly'
                self.ids.part_spin.values = ('Written', 'Oral/Activity')
                if part not in self.ids.part_spin.values: self.ids.part_spin.text = 'Written'; part = 'Written'
                max_val = 30 if part == 'Written' else 70
            elif subj in ['EVS', 'Work Experience', 'Art Education', 'Health & Physical Edu.']:
                self.ids.exam_spin.values = ('Half Yearly', 'Annual')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'Half Yearly'; exam = 'Half Yearly'
                self.ids.part_spin.values = ('Marks',)
                if part != 'Marks': self.ids.part_spin.text = 'Marks'; part = 'Marks'
                max_val = 50 if subj in ['EVS', 'Health & Physical Edu.'] else 25

        elif cls in ['3', '4']:
            co_scholastic = ['Work Experience', 'Art Education', 'Health & Physical Edu.']
            if subj in co_scholastic:
                self.ids.exam_spin.values = ('Parakh 1', 'Parakh 2', 'Parakh 3', 'Parakh 4', 'Parakh 5')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'Parakh 1'; exam = 'Parakh 1'
                self.ids.part_spin.values = ('Marks',)
                if part != 'Marks': self.ids.part_spin.text = 'Marks'; part = 'Marks'
                max_val = 20
            else:
                self.ids.exam_spin.values = ('T1', 'T2', 'T3', 'Half Yearly', 'Annual')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'T1'; exam = 'T1'
                if exam in ['T1', 'T2']: self.ids.part_spin.values = ('Written',)
                elif exam == 'T3': self.ids.part_spin.values = ('Written', 'Tree Plantation')
                elif exam in ['Half Yearly', 'Annual']:
                    if subj in ['Hindi', 'English', 'Maths']: self.ids.part_spin.values = ('Written', 'Oral', 'CBA')
                    else: self.ids.part_spin.values = ('Written', 'Oral')
                if part not in self.ids.part_spin.values: self.ids.part_spin.text = self.ids.part_spin.values[0]; part = self.ids.part_spin.values[0]
                
                if exam in ['T1', 'T2']: max_val = 10
                elif exam == 'T3': max_val = (4 if subj == 'EVS' else 2) if part == 'Tree Plantation' else (6 if subj == 'EVS' else 8)
                elif exam == 'Half Yearly':
                    if subj in ['Hindi', 'English', 'Maths']: max_val = 35 if part == 'Written' else (15 if part == 'Oral' else 20)
                    else: max_val = 50 if part == 'Written' else 20
                elif exam == 'Annual':
                    if subj in ['Hindi', 'English', 'Maths']: max_val = 50 if part == 'Written' else (30 if part == 'Oral' else 20)
                    else: max_val = 60 if part == 'Written' else 40

        elif cls in ['6', '7']:
            co_scholastic = ['Work Experience', 'Art Education', 'Health & Physical Edu.']
            if subj in co_scholastic:
                self.ids.exam_spin.values = ('Parakh 1', 'Parakh 2', 'Parakh 3', 'Parakh 4', 'Parakh 5')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'Parakh 1'; exam = 'Parakh 1'
                self.ids.part_spin.values = ('Marks',)
                if part != 'Marks': self.ids.part_spin.text = 'Marks'; part = 'Marks'
                max_val = 20
            else:
                self.ids.exam_spin.values = ('T1', 'T2', 'T3', 'Half Yearly', 'Annual')
                if exam not in self.ids.exam_spin.values and exam != 'Select Exam': self.ids.exam_spin.text = 'T1'; exam = 'T1'
                if exam in ['T1', 'T2']: self.ids.part_spin.values = ('Written', 'Oral')
                elif exam == 'T3': self.ids.part_spin.values = ('Written', 'Oral', 'Tree Plantation')
                elif exam in ['Half Yearly', 'Annual']:
                    if subj in ['Hindi', 'English', 'Maths']: self.ids.part_spin.values = ('Written', 'Oral', 'CBA')
                    else: self.ids.part_spin.values = ('Written', 'Oral')
                if part not in self.ids.part_spin.values: self.ids.part_spin.text = 'Written'; part = 'Written'
                
                if exam in ['T1', 'T2']: max_val = 5
                elif exam == 'T3': max_val = (3 if part=='Written' else (2 if part=='Oral' else 5)) if subj in ['Science','EVS'] else (5 if part=='Written' else (4 if part=='Oral' else 1))
                elif exam == 'Half Yearly': max_val = (35 if part=='Written' else (15 if part=='Oral' else 20)) if subj in ['Hindi','English','Maths'] else (50 if part=='Written' else 20)
                elif exam == 'Annual': max_val = (50 if part=='Written' else (30 if part=='Oral' else 20)) if subj in ['Hindi','English','Maths'] else (70 if part=='Written' else 30)

        elif cls == '9':
            if subj in ['Hindi', 'English', 'Maths', 'Sanskrit', 'Science', 'Social Science']:
                self.ids.exam_spin.values = ('T1', 'T2', 'T3', 'Half Yearly', 'Annual')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'T1'; exam = 'T1'
                self.ids.part_spin.values = ('Theory',)
                if part != 'Theory': self.ids.part_spin.text = 'Theory'; part = 'Theory'
                if exam in ['T1', 'T2', 'T3']: max_val = 5
                elif exam == 'Half Yearly': max_val = 35
                else: max_val = 50
            elif subj == 'Computer':
                self.ids.exam_spin.values = ('T2', 'T3', 'Half Yearly', 'Annual')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'Half Yearly'; exam = 'Half Yearly'
                self.ids.part_spin.values = ('Theory',) if exam in ['T2', 'T3'] else ('Theory', 'Practical')
                if part not in self.ids.part_spin.values: self.ids.part_spin.text = 'Theory'; part = 'Theory'
                max_val = 50 if part=='Theory' else 20
            elif subj == 'Health & Physical Edu.':
                self.ids.exam_spin.values = ('T1', 'T2', 'T3', 'Half Yearly', 'Annual')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'Half Yearly'; exam = 'Half Yearly'
                self.ids.part_spin.values = ('Theory', 'Practical')
                if part not in self.ids.part_spin.values: self.ids.part_spin.text = 'Theory'; part = 'Theory'
                max_val = 70 if part=='Theory' else 30
            elif subj == 'Art Education':
                self.ids.exam_spin.values = ('Annual',)
                if exam != 'Annual': self.ids.exam_spin.text = 'Annual'; exam = 'Annual'
                self.ids.part_spin.values = ('Theory', 'Practical', 'Presentation Work')
                if part not in self.ids.part_spin.values: self.ids.part_spin.text = 'Theory'; part = 'Theory'
                max_val = 100
            
        elif cls == '11':
            if subj == 'Life Skills':
                self.ids.exam_spin.values = ('Annual',)
                if exam != 'Annual': self.ids.exam_spin.text = 'Annual'; exam = 'Annual'
                self.ids.part_spin.values = ('Compulsory', 'Alternative', 'Written')
                if part not in self.ids.part_spin.values: self.ids.part_spin.text = 'Written'; part = 'Written'
                max_val = 30 if part in ['Compulsory', 'Alternative'] else 40
            else:
                self.ids.exam_spin.values = ('T1', 'T2', 'T3', 'Half Yearly', 'Annual')
                if exam not in self.ids.exam_spin.values: self.ids.exam_spin.text = 'T1'; exam = 'T1'
                if subj in ['Hindi', 'English', 'History', 'Golden India', 'Sanskrit Vangmay', 'Sahitya Shastra']:
                    self.ids.part_spin.values = ('Written',)
                    if part != 'Written': self.ids.part_spin.text = 'Written'; part = 'Written'
                    if exam in ['T1', 'T2', 'T3']: max_val = 10
                    elif exam == 'Half Yearly': max_val = 70
                    else: max_val = 100
                
        self.current_max_marks = max_val

    def start_fetch(self):
        cls = self.ids.class_spin.text; subj = self.ids.subject_spin.text
        exam = self.ids.exam_spin.text; part = self.ids.part_spin.text
        if 'Select' in cls or 'Select' in subj or 'Select' in exam or 'Select' in part:
            return show_alert_popup("🚨 INCOMPLETE INFO", "Kripya Class, Subject, Exam aur Type select karein!")
            
        self.auto_clear_list()
        master = load_cache("master_roster")
        if master and cls in master and len(master[cls]) > 0:
            self.build_roster_ui(master[cls])
            self.ids.status_msg_lbl.text = "Fetching marks silently from Ocean..."
            self.ids.status_msg_lbl.opacity = 1; self.ids.status_msg_lbl.height = "25dp"
            threading.Thread(target=self.fetch_marks_only, args=(cls, subj, exam, part)).start()
        else:
            self.ids.student_list.add_widget(Label(text="Fetching LIVE DATA from Ocean...", color=(0,1,1,1), size_hint_y=None, height="30dp"))
            threading.Thread(target=self.fetch_live_full, args=(cls, subj, exam, part)).start()

    def build_roster_ui(self, roster_data):
        self.ids.student_list.clear_widgets(); self.ids.header_box.clear_widgets()
        self.input_boxes = {}; self.input_widgets = []
        is_att = (self.ids.subject_spin.text == 'Attendance')
        
        hl1 = ColorfulLabel(text="Roll", size_hint_x=0.15); hl1.bg_color = [0.8, 0.3, 0.1, 0.85] 
        hl2 = ColorfulLabel(text="Student Name", size_hint_x=0.45); hl2.bg_color = [0.1, 0.4, 0.8, 0.85] 
        self.ids.header_box.add_widget(hl1); self.ids.header_box.add_widget(hl2)
        
        if is_att:
            hl3 = ColorfulLabel(text="Meetings", size_hint_x=0.20); hl3.bg_color = [0.1, 0.6, 0.3, 0.85] 
            hl4 = ColorfulLabel(text="Present", size_hint_x=0.20); hl4.bg_color = [0.7, 0.2, 0.6, 0.85] 
            self.ids.header_box.add_widget(hl3); self.ids.header_box.add_widget(hl4)
        else:
            mx_txt = f"Marks (Max: {self.current_max_marks})" if self.current_max_marks != 999 else "Marks"
            hl3 = ColorfulLabel(text=mx_txt, size_hint_x=0.40); hl3.bg_color = [0.1, 0.6, 0.3, 0.85] 
            self.ids.header_box.add_widget(hl3)

        for st in roster_data:
            name = st['Name']; roll = st['Roll']
            row = BoxLayout(size_hint_y=None, height="50dp", spacing="4dp")
            l1 = ColorfulLabel(text=roll, size_hint_x=0.15); l1.bg_color = [0.8, 0.3, 0.1, 0.85] 
            l2 = ColorfulLabel(text=name, size_hint_x=0.45, halign='left', valign='center'); l2.bg_color = [0.1, 0.5, 0.7, 0.85] 
            l2.bind(size=l2.setter('text_size'))
            row.add_widget(l1); row.add_widget(l2)
            
            if is_att:
                in1 = SmoothInput(text=str(st.get('marks1','')), hint_text="Meet", size_hint_x=0.20)
                in2 = SmoothInput(text=str(st.get('marks2','')), hint_text="Pres", size_hint_x=0.20)
                in1.bind(on_text_validate=self.focus_next_input); in2.bind(on_text_validate=self.focus_next_input)
                row.add_widget(in1); row.add_widget(in2)
                self.input_widgets.extend([in1, in2]); self.input_boxes[roll] = {'in1': in1, 'in2': in2}
            else:
                in_m = SmoothInput(text=str(st.get('marks','')), hint_text="AB/0", size_hint_x=0.40)
                in_m.bind(on_text_validate=self.focus_next_input)
                row.add_widget(in_m); self.input_widgets.append(in_m)
                self.input_boxes[roll] = {'in_m': in_m}
            self.ids.student_list.add_widget(row)

    def fetch_marks_only(self, cls, subj, exam, part):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            s = urllib.parse.quote(subj); e = urllib.parse.quote(exam); p = urllib.parse.quote(part)
            url = f"{SCRIPT_URL}?action=get_students&class_name={cls}&subject={s}&exam={e}&type={p}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx, timeout=30) as res:
                data = json.loads(res.read().decode('utf-8'))
                if isinstance(data, list):
                    roster_data = [{'Name': d.get('Name',''), 'Roll': d.get('Roll','')} for d in data]
                    master = load_cache("master_roster") or {}
                    master[cls] = roster_data; save_cache("master_roster", master)
                Clock.schedule_once(lambda dt: self.update_marks_ui(data), 0)
        except Exception as err:
            Clock.schedule_once(lambda dt: self.hide_status(f"Fetch failed: {str(err)[:20]}"), 0)

    def fetch_live_full(self, cls, subj, exam, part):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            s = urllib.parse.quote(subj); e = urllib.parse.quote(exam); p = urllib.parse.quote(part)
            url = f"{SCRIPT_URL}?action=get_students&class_name={cls}&subject={s}&exam={e}&type={p}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx, timeout=30) as res:
                data = json.loads(res.read().decode('utf-8'))
                Clock.schedule_once(lambda dt: self.build_roster_ui(data), 0)
        except Exception as err:
            Clock.schedule_once(lambda dt: show_error_popup("LIVE FETCH ERROR:\n" + str(err)), 0)

    def update_marks_ui(self, data):
        is_att = (self.ids.subject_spin.text == 'Attendance')
        if isinstance(data, list):
            for st in data:
                roll = str(st.get('Roll', ''))
                if roll in self.input_boxes:
                    if is_att:
                        if st.get('marks1') != "": self.input_boxes[roll]['in1'].text = str(st.get('marks1'))
                        if st.get('marks2') != "": self.input_boxes[roll]['in2'].text = str(st.get('marks2'))
                    else:
                        if st.get('marks') != "": self.input_boxes[roll]['in_m'].text = str(st.get('marks'))
        self.ids.status_msg_lbl.text = "Marks Fetched!"; self.ids.status_msg_lbl.color = (0.2, 1, 0.2, 1)
        Clock.schedule_once(lambda dt: self.hide_status(""), 2)
        
    def hide_status(self, msg):
        if msg: self.ids.status_msg_lbl.text = msg
        else: self.ids.status_msg_lbl.opacity = 0; self.ids.status_msg_lbl.height = "0dp"

    def focus_next_input(self, instance):
        try:
            idx = self.input_widgets.index(instance)
            if idx + 1 < len(self.input_widgets):
                next_wid = self.input_widgets[idx+1]
                Clock.schedule_once(lambda dt: setattr(next_wid, 'focus', True), 0.05)
                if self.ids.student_list.height > self.ids.scroll_view.height: self.ids.scroll_view.scroll_to(next_wid)
            else:
                instance.focus = False; self.save_all_marks() 
        except: pass

    def confirm_reset_activity(self):
        cls = self.ids.class_spin.text; subj = self.ids.subject_spin.text
        exam = self.ids.exam_spin.text; part = self.ids.part_spin.text
        if 'Select' in cls or 'Select' in subj or 'Select' in exam or 'Select' in part:
            return show_alert_popup("🚨 INCOMPLETE INFO", "Pehle Class, Subject, Exam aur Type select karein!")
            
        box = BoxLayout(orientation='vertical', padding="10dp", spacing="10dp")
        box.add_widget(Label(text=f"WARNING: Erase '{part}' of '{exam}'\nfor {subj} (Class {cls})?", color=(1,0,0,1), bold=True, halign='center'))
        btn_box = BoxLayout(size_hint_y=None, height="50dp", spacing="10dp")
        btn_no = Button(text="CANCEL", background_color=(0.5,0.5,0.5,1)); btn_yes = Button(text="YES, DELETE", background_color=(1,0,0,1), bold=True)
        btn_box.add_widget(btn_no); btn_box.add_widget(btn_yes); box.add_widget(btn_box)
        popup = Popup(title="CONFIRM ACTIVITY RESET", title_color=(1,0,0,1), content=box, size_hint=(0.85, 0.45), background_color=(0.1, 0.2, 0.3, 0.9))
        btn_no.bind(on_release=popup.dismiss); btn_yes.bind(on_release=lambda x: [popup.dismiss(), self.execute_reset_activity()]); popup.open()
        
    def execute_reset_activity(self):
        self.ids.student_list.clear_widgets()
        self.ids.student_list.add_widget(Label(text="[ DELETING MARKS FROM OCEAN... ]", color=(1, 0.2, 0.2, 1), bold=True, font_size='22sp'))
        payload = {"action": "reset_specific_activity", "class_name": self.ids.class_spin.text, "subject": self.ids.subject_spin.text, "exam": self.ids.exam_spin.text, "type": self.ids.part_spin.text}
        
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text="⏳ Please Wait, Deleting Data...", bold=True, halign='center'))
        popup = Popup(title="PROCESSING...", content=box, size_hint=(0.8, 0.3), auto_dismiss=False)
        Clock.schedule_once(lambda dt: popup.open(), 0)
        
        def run_post():
            try:
                ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(SCRIPT_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
                urllib.request.urlopen(req, context=ctx, timeout=40)
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                Clock.schedule_once(lambda dt: show_success_popup("DELETED", "Marks Deleted Successfully!"), 0.5)
            except Exception as e:
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                Clock.schedule_once(lambda dt: show_error_popup(f"ERROR: {str(e)}"), 0.5)
        threading.Thread(target=run_post).start()

    def save_all_marks(self):
        data_to_save = []; is_att = (self.ids.subject_spin.text == 'Attendance')
        for roll, items in self.input_boxes.items():
            if is_att:
                m1 = items['in1'].text.strip(); m2 = items['in2'].text.strip()
                if m1 or m2:
                    try:
                        v1 = int(m1) if m1 else 0; v2 = int(m2) if m2 else 0
                        if v2 > v1: return show_alert_popup("🚨 ERROR", f"Roll No {roll}: Present ({v2}) > Meetings ({v1}) nahi ho sakti!")
                        data_to_save.append({'roll': roll, 'marks1': v1, 'marks2': v2})
                    except: return show_alert_popup("🚨 ERROR", f"Roll No {roll}: Sirf numbers bharne hain!")
            else:
                m = items['in_m'].text.strip()
                if m:
                    if m.upper() != "AB":
                        try: 
                            v = int(m)
                            if self.current_max_marks != 999 and v > self.current_max_marks:
                                return show_alert_popup("🚨 ERROR", f"Roll No {roll}: Marks ({v}) Max Limit ({self.current_max_marks}) se jyada hain!")
                        except: return show_alert_popup("🚨 ERROR", f"Roll No {roll}: Sirf Numbers ya AB likhein.")
                    data_to_save.append({'roll': roll, 'marks': m.upper()})
                
        if not data_to_save: return
        self.ids.student_list.clear_widgets()
        lbl = Label(text="SAVING, PLEASE WAIT...", color=(1, 1, 0.2, 1), bold=True, font_size='26sp', halign='center', valign='middle', size_hint_y=None, height="120dp")
        lbl.bind(size=lbl.setter('text_size'))
        self.ids.student_list.add_widget(lbl)
        
        payload = {"action": "save_marks", "class_name": self.ids.class_spin.text, "subject": self.ids.subject_spin.text, "exam": self.ids.exam_spin.text, "type": self.ids.part_spin.text, "marks_data": data_to_save}
        
        box = BoxLayout(orientation='vertical', padding="15dp", spacing="15dp")
        box.add_widget(Label(text="⏳ Please Wait, Saving Data...", bold=True, halign='center'))
        popup = Popup(title="PROCESSING...", content=box, size_hint=(0.8, 0.3), auto_dismiss=False)
        Clock.schedule_once(lambda dt: popup.open(), 0)
        
        def run_post():
            try:
                ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(SCRIPT_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
                urllib.request.urlopen(req, context=ctx, timeout=30)
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                Clock.schedule_once(lambda dt: lbl.setter('text')(lbl, "SAVED SUCCESSFULLY"), 0)
                Clock.schedule_once(lambda dt: lbl.setter('color')(lbl, (0.2, 1, 0.2, 1)), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                Clock.schedule_once(lambda dt: show_error_popup(f"ERROR: {str(e)}"), 0.5)
        threading.Thread(target=run_post).start()

class SanskritSchoolApp(App):
    def build(self):
        global cache_store
        data_dir = getattr(self, 'user_data_dir', '.')
        try:
            cp = os.path.join(data_dir, 'session.json')
            try: self.store = JsonStore(cp)
            except:
                os.remove(cp); self.store = JsonStore(cp)
        except: pass 
        try:
            cp = os.path.join(data_dir, 'app_cache.json')
            try: self.app_cache = JsonStore(cp)
            except:
                os.remove(cp); self.app_cache = JsonStore(cp)
            cache_store = self.app_cache
        except: pass 
            
        self.root_widget = Builder.load_string(KV)
        if hasattr(self, 'store') and self.store.exists('user'):
            m = self.store.get('user')['mobile']
            self.root_widget.current = 'principal_dash' if self.store.get('user').get('is_admin', False) else 'teacher_dash'
        return self.root_widget
        
    def logout(self):
        if hasattr(self, 'store'): self.store.clear()
        self.root_widget.current = 'login'

if __name__ == '__main__':
    SanskritSchoolApp().run()
