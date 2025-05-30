#모비노기 데미지 프린터 v25.05.26
#미완성 코드입니다!!!!


import tkinter as tk
from tkinter import font
from datetime import datetime
from scapy.all import sniff, IP, Raw, get_if_addr, conf
import re
import struct
import threading
import queue
import os
import time

packetprocess = queue.Queue()
capture_lock = threading.Lock()

my_ip = get_if_addr(conf.iface)

PORT = 16000

dmgskill = []
dmgburn = []
starttime = 0



joblist = [ # 인식 가능한 직업 및 스킬 앞자리 리스트, 추가 필요
    'RangeDefaultAttack',
    'MeleeDefaultAttack',
    'FireMage_',
    'Idle',
    'Elemental_',
    'GreatSwordWarrior_',
    'Arbalist_',
    'ChargingFist_',
    'Fighter_',
    'HighMage_',
    'IceMage_',
    'SwordMaster_',
    'NoviceWarrior_',
    'ExpertWarrior_',
    'Monk_',
    'LongBowMan_',
    'HighArcher_',
    'Priest_',
]

blacklist = [
    '_Backdraft_Trail_',
    'FireStorm_Tie',
    'Script',
    'SkillAI',
    'LoopAI',
    '_Buff_End',
]

def input_listener():
    global packetprocess
    while True:
        try:
            command = input()
            with capture_lock:
                if command.upper() == 'X':
                    os._exit(0)
        except EOFError:
            break

def toutf16le(text):
    return text.encode('utf-16le')

def utf16leprint(hex_bytes, min_chars: int = 4):
    results = []
    rsoffset = 0
    rsdone = False
    i = 0
    while i < len(hex_bytes) - min_chars * 2:
        try:
            chunk = hex_bytes[i:i + min_chars * 2]
            decoded = chunk.decode('utf-16le')

            if not re.fullmatch(r"[a-zA-Z0-9가-힣 _\-\.\:/()\[\]]+", decoded):
                i += 2
                continue

            for j in range(i + min_chars * 2, len(hex_bytes), 2):
                try:
                    extended = hex_bytes[i:j].decode('utf-16le')
                    if not re.fullmatch(r"[a-zA-Z0-9가-힣 _\-\.\:/()\[\]]+", extended):
                        break
                    if not rsdone: rsoffset = j
                    decoded = extended
                except:
                    print('err')
                    break
            rsdone = True
            results.append(decoded)
            i = j 
        except:
            i += 2

    return [results,rsoffset]

def bytetoint(hex_bytes, offset = 0):
    if len(hex_bytes) + 4 < offset:
        return 0
    chunk = hex_bytes[offset:offset+4]
    #print(chunk.hex(" "))
    if len(chunk) == 4:
        int_val = struct.unpack('<I', chunk)[0]
        return int_val
    
def matchdata(data):
    matches = (
        data[0:2] == b'\x3A\x04' and
        data[2:9] == b'\x00\x00\x00\x00\x00\x00\x00'
    )
    return matches

def getburn(data: bytes):
    # 00 00 00 03 05 00 00 43 00 00 00 00 + 20
    pattern = b'\x00\x00\x00\x03\x05\x00\x00\x43\x00\x00\x00\x00'
    damages = []
    for match in re.finditer(pattern, data, flags=re.DOTALL):
        matchend = match.end() + 20
        if len(data) >= matchend + 4:
            vbytes = data[matchend:matchend+4]
            if vbytes[1] == 0x00 and vbytes[2] != 0x00 and vbytes[3] == 0x00: continue
            value = int.from_bytes(vbytes, byteorder='little')
            if value > 99: 
                damages.append(value)
    if len(damages) > 0: return damages
    return [0]

def get_damages(data: bytes, pattern_bytes) -> list[tuple[str, int]]:
    results = []
    start_pos = 0
    
    while True:
        pattern_index = data.find(pattern_bytes, start_pos)
        
        if pattern_index == -1:
            break
        
        if pattern_index < 4:
            start_pos = pattern_index + len(pattern_bytes)
            continue
        
        try:
            skill_name_length = struct.unpack('<I', data[pattern_index-4:pattern_index])[0]
            
            skill_name_start = pattern_index
            skill_name_end = skill_name_start + skill_name_length
            
            if skill_name_end + 2 > len(data):
                start_pos = pattern_index + len(pattern_bytes)
                continue
            
            skill_name_bytes = data[skill_name_start:skill_name_end]
            skill_name = skill_name_bytes.decode('utf-16le', errors='ignore')
            
            damage_bytes = data[skill_name_end:skill_name_end + 2]
            damage = struct.unpack('<H', damage_bytes)[0]
            
            results.append((skill_name, damage))
            
            start_pos = skill_name_end + 2
            
        except Exception as e:
            start_pos = pattern_index + len(pattern_bytes)
            continue
    
    return results

def tryprint(raw_data):
    global dmgskill
    global dmgburn
    
    if len(raw_data) < 24: return # 길이 필터링
    #if not matchdata(raw_data): return # 헤더 필터링
    for x in blacklist:
        if toutf16le(x) in raw_data: return # str 필터링
        ''
    # int 변환, hex보다 비교가 쪼끔 쉬움
    '''
    for i in range(0, len(raw_data), 4):
        chunk = raw_data[i:i+4]
        if len(chunk) == 4:
            int_val = struct.unpack('<I', chunk)[0]
            printint += f"{int_val} "
            valsint.append(int_val)
    '''


    burndamage = getburn(raw_data) # 지속 데미지 출력
    for x in burndamage:
        if x > 9:
            dmgburn.append(x)
            print('burn : ' + str(x))

    for x in joblist: # 데미지 출력, 직업 인식
        if toutf16le(x) in raw_data: 
            damages = get_damages(raw_data, toutf16le(x))
            for skill_name, damage in damages:
                if damage > 9:
                    dmgskill.append(damage)
                    print(f"{skill_name} : {damage}")
    return

class DamageTrackerApp: #챗지피티 최고
    def __init__(self, root):
        self.root = root
        self.root.title("Redpill beta")
        self.root.geometry("300x400")
        self.root.resizable(False, False)

        # 폰트
        bold_font = font.Font(weight="bold", size=13)
        big_bold_font = font.Font(weight="bold", size=16)

        # 라벨
        self.time_label = tk.Label(root, text="측정 시간 : ")
        self.dmg1_label = tk.Label(root, text="스킬 피해")
        self.dmg2_label = tk.Label(root, text="지속 피해")
        self.min_dmg_label = tk.Label(root, text="최소 데미지", font=bold_font)
        self.max_dmg_label = tk.Label(root, text="최대 데미지", font=bold_font)
        self.avg_dmg_label = tk.Label(root, text="평균 데미지", font=big_bold_font)

        # 버튼
        self.start_button = tk.Button(root, text="Start", command=self.start, width=40)
        self.stop_button = tk.Button(root, text="Stop", command=self.stop, width=40)
        self.reset_button = tk.Button(root, text="Reset", command=self.reset, width=40)

        # 배치
        widgets = [
            self.time_label,
            self.dmg1_label,
            self.dmg2_label,
            self.min_dmg_label,
            self.max_dmg_label,
            self.avg_dmg_label,
            self.start_button,
            self.stop_button,
            self.reset_button,
        ]
        for widget in widgets:
            widget.pack(pady=5)

        self.running = False

    def update_damages(self):
        global dmgskill
        global dmgburn
        global starttime
        while self.running:
            if len(dmgskill) == 0 and len(dmgburn) == 0: continue
            if starttime == 0:
                starttime = datetime.now()
            calctime = datetime.now() - starttime
            estime = str(calctime).split('.')[0]
            self.time_label.config(text=f"Time: {estime}")

            self.dmg1_label.config(text=f"스킬 : {sum(dmgskill)}")
            self.dmg2_label.config(text=f"지속 : {sum(dmgburn)}")

            if len(dmgskill) != 0:
                self.min_dmg_label.config(text=f"최소 : {min(dmgskill)}")
                self.max_dmg_label.config(text=f"최대 : {max(dmgskill)}")
                self.avg_dmg_label.config(text=f"평균: {round(sum(dmgskill) / len(dmgskill),2)}")

            time.sleep(0.2)

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.update_damages, daemon=True).start()

    def stop(self):
        self.running = False

    def reset(self):
        global dmgskill
        global dmgburn
        global starttime
        dmgskill = []
        dmgburn = []
        starttime = 0
        self.running = False
        self.dmg1_label.config(text="스킬 : 0")
        self.dmg2_label.config(text="지속 : 0")
        self.min_dmg_label.config(text="최소 : 0")
        self.max_dmg_label.config(text="최대 : 0")
        self.avg_dmg_label.config(text="평균 : 0")
    

def processor():
    while True:
        data = packetprocess.get()
        if data is None:
            print("exiting...")
            break
        tryprint(data)

def sniffpkt():
    print(f"starting tcp port : {PORT}...")
    sniff(filter=f"tcp port {PORT} and dst host {my_ip}", prn=packet_callback, store=0)

def packet_callback(packet):
    if Raw in packet:
        packetprocess.put(packet[Raw].load)
        #tryprint(packet[Raw].load)
                
pktprocess = threading.Thread(target=processor, daemon=True)
pktprocess.start()
pktcapinput = threading.Thread(target=sniffpkt, daemon=True)
pktcapinput.start()



if __name__ == "__main__":
    root = tk.Tk()
    app = DamageTrackerApp(root)
    root.mainloop()
#sniff(filter=f"tcp port {PORT}", prn=packet_callback, store=0)
