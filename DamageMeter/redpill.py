#모비노기 데미지 프린터 v25.06.05
#아직 부족한 부분이 많습니다. 이슈 발생시 제보 주세요.


import tkinter as tk
from tkinter import font
from datetime import datetime
from scapy.all import sniff, IP, TCP, Raw, get_if_addr, conf

import re
import struct
import threading
import queue
import os
import time
import brotli

packetprocess = queue.Queue()
capture_lock = threading.Lock()

my_ip = get_if_addr(conf.iface)

ver = 'v25.06.05'

PORT = 16000

dmgskill = []
dmgburn = []
starttime = 0
running = False
dmgtype = bytes.fromhex('03 05 00 00')  # 데미지 타입, 게임 업데이트시 갱신 필요


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
    
def matchdata(data):
    matches = (
        data[0:2] == b'\x3A\x04' and
        data[2:9] == b'\x00\x00\x00\x00\x00\x00\x00'
    )
    return matches

def findpattern(data: bytes, pattern: bytes) -> list:
    positions = []
    pattern_len = len(pattern)
    i = 0
    while i <= len(data) - pattern_len:
        if data[i:i+pattern_len] == pattern:
            positions.append(i)
        i += 1
    return positions

def finddamage(data: bytes):
    target = int.from_bytes(data[8:12], byteorder='little')
    skilllen = int.from_bytes(data[16:20], byteorder='little')
    if skilllen > 99 or skilllen < 2: return
    skillname = data[20:20 + skilllen].decode('utf-16le')
    damage = int.from_bytes(data[20 + skilllen:20 + skilllen + 4], byteorder='little')
    if damage < 2 or damage > 100000000: return
    return [damage, target, skillname]

def get_damages(data: bytes):
    damages = []
    spoints = findpattern(data, dmgtype)
    for spoint in spoints:
        dtype = data[spoint + 4]
        if dtype == 0: continue
        if data[spoint + 8] == 1:
            try:
                enclen = int.from_bytes(data[spoint + 4:spoint + 8], byteorder='little')
                encdata = data[spoint + 9:spoint + 9 + enclen]
                decdata = brotli.decompress(encdata)
                dmgs = finddamage(decdata)
                if dmgs: damages.append([dmgs[0], dmgs[1], dtype , dmgs[2]])
            except Exception as e:
                print(f"Decompression error")

        if dtype == 67: #지속피해, 0x43
            target = int.from_bytes(data[spoint+17:spoint+21], byteorder='little')
            damage = int.from_bytes(data[spoint+29:spoint+33], byteorder='little')
            damages.append([damage,target,dtype,'DOT'])
        else:
            datalen = int.from_bytes(data[spoint + 4:spoint + 8], byteorder='little')
            slcdata = data[spoint + 9:spoint + 9 + datalen]
            dmgs = finddamage(slcdata)
            if dmgs: damages.append([dmgs[0], dmgs[1], dtype , dmgs[2]])
    return damages

def extractpkt(data: bytes):
    rslts = []
    spoints = findpattern(data, bytes.fromhex('00 80 aa aa aa ea'))
    for spoint in spoints:
        match_start = spoint - 3
        if match_start - 5 < 0:
            continue
        match_len = struct.unpack('<I', data[match_start -5 :match_start-1])[0]
        if match_len > len(data) - match_start:
            continue   
        msegment = data[match_start:match_start + match_len]
        try:
            decompress = brotli.decompress(msegment)
            rslts.append(decompress)
        except Exception as e:
            print(f"Decompression error")
            continue

    return rslts

def tryprint(raw_data):
    global dmgskill
    global dmgburn

    if len(raw_data) < 24:
        return  # 길이 필터링
    if not matchdata(raw_data): return # 헤더 필터링
    
    if dmgtype not in raw_data: return

    damages = get_damages(raw_data)
    for damage, target, dtype, skillname in damages:
        if dtype == 67:
            dmgburn.append([damage, target])
        else:
            dmgskill.append([damage, target])
        print(f"target : {target} / {skillname} / dmg : {damage}")


class DamageTrackerApp: #챗지피티 최고
    def __init__(self, root):
        global running
        self.root = root
        self.root.title("Redpill beta " + ver)
        self.root.geometry("300x500")
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
        self.full_dmg_label = tk.Label(root, text="총합 데미지", font=big_bold_font)
        self.dps_label = tk.Label(root, text="DPS", font=big_bold_font)

        # 버튼
        self.start_button = tk.Button(root, text="Start", command=self.start, width=40)
        self.stop_button = tk.Button(root, text="Stop", command=self.stop, width=40)
        self.reset_button = tk.Button(root, text="Reset", command=self.reset, width=40)

        self.chkvar = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(self.root, text='단일 타겟(가장 먼저 맞은 타겟)', variable=self.chkvar)

        self.totop = tk.BooleanVar(value=False)
        topcheck = tk.Checkbutton(root, text="항상 위에 고정", variable=self.totop, command=self.toggle_always_on_top)
        
        # 배치
        widgets = [
            self.time_label,
            self.dmg1_label,
            self.dmg2_label,
            self.min_dmg_label,
            self.max_dmg_label,
            self.full_dmg_label,
            self.dps_label,
            self.start_button,
            self.stop_button,
            self.reset_button,
            chk,
            topcheck,
        ]
        for widget in widgets:
            widget.pack(pady=5)

        running = False
    def toggle_always_on_top(self):
        root.attributes('-topmost', self.totop.get())

    def update_damages(self):
        global dmgskill
        global dmgburn
        global starttime
        global running
        while running:
            if len(dmgskill) == 0 and len(dmgburn) == 0: continue
            if starttime == 0:
                starttime = datetime.now()
            skilldmgs = []
            burndmgs = []
            entity = 0
            for dmg in dmgskill:
                if self.chkvar.get():
                    if entity == 0:
                        entity = dmg[1]
                    if dmg[1] == entity:
                        skilldmgs.append(dmg[0])
                else:
                    skilldmgs.append(dmg[0])
            for dmg in dmgburn:
                if self.chkvar.get():
                    if dmg[1] == entity:
                        burndmgs.append(dmg[0])
                else:
                    burndmgs.append(dmg[0])
            calctime = datetime.now() - starttime
            estime = str(calctime).split('.')[0]
            self.time_label.config(text=f"Time: {estime}")

            self.dmg1_label.config(text=f"스킬 : {sum(skilldmgs)}")
            self.dmg2_label.config(text=f"지속 : {sum(burndmgs)}")

            if len(skilldmgs) != 0:
                sumdmg = sum(skilldmgs) + sum(burndmgs)
                sectime = calctime.total_seconds()
                if sectime == 0:    
                    dpss = sumdmg
                else:
                    dpss = round(sumdmg / calctime.total_seconds(),2)
                self.min_dmg_label.config(text=f"최소 : {min(skilldmgs)}")
                self.max_dmg_label.config(text=f"최대 : {max(skilldmgs)}")
                self.full_dmg_label.config(text=f"총합 : {(sum(skilldmgs) + sum(burndmgs))}")
                self.dps_label.config(text=f"DPS : {dpss}")

            time.sleep(0.2)

    def start(self):
        global dmgskill
        global dmgburn
        global running
        dmgskill = []
        dmgburn = []
        if not running:
            running = True
            threading.Thread(target=self.update_damages, daemon=True).start()

    def stop(self):
        global running
        running = False

    def reset(self):
        global dmgskill
        global dmgburn
        global starttime
        global running
        dmgskill = []
        dmgburn = []
        starttime = 0
        running = False
        self.dmg1_label.config(text="스킬 : 0")
        self.dmg2_label.config(text="지속 : 0")
        self.min_dmg_label.config(text="최소 : 0")
        self.max_dmg_label.config(text="최대 : 0")
        self.full_dmg_label.config(text="총합 : 0")
        self.dps_label.config(text="DPS : 0")
    

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


lock = threading.Lock()
tcp_segments = []


def packet_callback(packet):
    if TCP in packet and Raw in packet:
        seq = packet[TCP].seq
        payload = bytes(packet[Raw].load)

        with lock:
            tcp_segments.append((seq, payload))

        if packet[TCP].flags.F or packet[TCP].flags.P:
            process_if_complete()


def process_if_complete():
    with lock:
        if not tcp_segments:
            return  # 수신된 세그먼트가 없음

        tcp_segments.sort()

        full_data = bytearray()
        expected_seq = None
        valid_segment_count = 0
        consumed_until = 0  # 처리한 세그먼트 수

        for i, (seq, data) in enumerate(tcp_segments):
            if expected_seq is None:
                expected_seq = seq

            if seq > expected_seq:
                # 중간에 누락 발생 → 조합 중단, 이후 도착까지 대기
                break

            elif seq < expected_seq:
                overlap = expected_seq - seq
                if overlap >= len(data):
                    continue  # 전부 중복 → 무시
                data = data[overlap:]

            full_data.extend(data)
            expected_seq += len(data)
            valid_segment_count += 1
            consumed_until = i + 1

        if not full_data:
            return  # 유효한 payload 없음 → 처리 안함

        reassembled_payload = bytes(full_data)

        if valid_segment_count >= 2:
        #    print(f"✅ Reassembled {valid_segment_count} segments, length {len(reassembled_payload)} bytes")
            ''

        packetprocess.put(reassembled_payload)

        # 조합된 부분만 삭제, 나머지는 남겨둠 (다음 시도에서 사용)
        del tcp_segments[:consumed_until]


pktprocess = threading.Thread(target=processor, daemon=True)
pktprocess.start()
pktcapinput = threading.Thread(target=sniffpkt, daemon=True)
pktcapinput.start()



if __name__ == "__main__":
    root = tk.Tk()
    app = DamageTrackerApp(root)
    root.mainloop()
#sniff(filter=f"tcp port {PORT}", prn=packet_callback, store=0)
