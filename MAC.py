#!/usr/bin/env python3

"""
MACspoof v2.1 - Professional MAC Address Spoofer
Dark Tool by XORAOS
"""

import subprocess
import re
import random
import time
import argparse
import sys
import os
import logging
from datetime import datetime

# ============ КОНФИГ ============

HOME = os.path.expanduser("~")
LOG_DIR = os.path.join(HOME, ".macspoof")
LOG_FILE = os.path.join(LOG_DIR, "macspoof.log")
CONFIG_DIR = os.path.join(HOME, ".config", "macspoof")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.txt")

for d in [LOG_DIR, CONFIG_DIR]:
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def get_interfaces():
    try:
        result = subprocess.run(
            ["ip", "link", "show"],
            capture_output=True,
            text=True,
            check=True
        )
        interfaces = re.findall(r'\d+: (\w+):', result.stdout)
        return [i for i in interfaces if i != 'lo']
    except Exception as e:
        logger.error(f"Ошибка получения интерфейсов: {e}")
        return []

def get_current_mac(interface):
    try:
        result = subprocess.run(
            ["ip", "link", "show", interface],
            capture_output=True,
            text=True,
            check=True
        )
        match = re.search(r'link/ether ([0-9a-fA-F:]{17})', result.stdout)
        return match.group(1).lower() if match else None
    except Exception as e:
        logger.error(f"Ошибка получения MAC для {interface}: {e}")
        return None

def generate_random_mac():
    mac = [0x02, 0x00, 0x00, 0x00, 0x00, 0x00]
    for i in range(1, 6):
        mac[i] = random.randint(0x00, 0xFF)
    return ':'.join(f'{b:02x}' for b in mac)

def generate_vendor_mac(vendor_prefix=None):
    vendor_prefixes = {
        'intel': ['00:15:00', '00:1B:21', '00:25:64', '00:1E:67'],
        'realtek': ['00:19:DB', '00:1A:EF', '00:E0:4C'],
        'broadcom': ['00:10:18', '00:11:43', '00:1A:6B'],
        'qualcomm': ['00:24:7E', '00:26:55', '00:28:6B'],
        'apple': ['00:1B:63', '00:1E:52', '00:1F:03'],
        'cisco': ['00:00:0C', '00:1F:CA', '00:1D:45'],
        'dell': ['00:1E:4F', '00:23:AE', '00:1D:09'],
        'hp': ['00:1E:0B', '00:1F:29', '00:26:55'],
        'asus': ['00:26:18', '00:1F:3A', '00:24:8C'],
        'msi': ['00:1E:8C', '00:24:1D', '00:26:55'],
        'random': None
    }
    
    if vendor_prefix and vendor_prefix in vendor_prefixes:
        prefix = random.choice(vendor_prefixes[vendor_prefix])
    else:
        prefix = f"{random.randint(0x00, 0xFF):02x}:{random.randint(0x00, 0xFF):02x}:{random.randint(0x00, 0xFF):02x}"
    
    suffix = f"{random.randint(0x00, 0xFF):02x}:{random.randint(0x00, 0xFF):02x}:{random.randint(0x00, 0xFF):02x}"
    return f"{prefix}:{suffix}"

def set_mac(interface, mac):
    try:
        subprocess.run(["ip", "link", "set", interface, "down"], check=True, capture_output=True)
        subprocess.run(["ip", "link", "set", interface, "address", mac], check=True, capture_output=True)
        subprocess.run(["ip", "link", "set", interface, "up"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка установки MAC для {interface}: {e.stderr.decode() if e.stderr else str(e)}")
        return False

def reset_mac(interface):
    try:
        result = subprocess.run(
            ["ethtool", "-P", interface],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            permanent_mac = re.search(r'Permanent address: ([0-9a-fA-F:]{17})', result.stdout)
            if permanent_mac:
                return set_mac(interface, permanent_mac.group(1))
        
        subprocess.run(["udevadm", "trigger", "--subsystem-match=net", "--action=add"], check=True)
        time.sleep(1)
        subprocess.run(["systemctl", "restart", "NetworkManager"], check=True)
        time.sleep(2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сброса MAC: {e}")
        return False

def spoof_interface(interface, vendor=None, random_mac=None):
    logger.info(f"{BLUE}[*] Обработка интерфейса: {interface}{RESET}")
    
    current_mac = get_current_mac(interface)
    if not current_mac:
        logger.error(f"{RED}[!] Не удалось получить MAC для {interface}{RESET}")
        return False
    
    logger.info(f"{YELLOW}[*] Текущий MAC: {current_mac}{RESET}")
    
    if random_mac:
        new_mac = random_mac.lower()
    elif vendor:
        new_mac = generate_vendor_mac(vendor)
    else:
        new_mac = generate_random_mac()
    
    logger.info(f"{GREEN}[*] Новый MAC: {new_mac}{RESET}")
    
    if set_mac(interface, new_mac):
        time.sleep(1) 
        
        verified_mac = get_current_mac(interface)
        if verified_mac and verified_mac.lower() == new_mac.lower():
            logger.info(f"{GREEN}[✓] MAC успешно изменён на {verified_mac}{RESET}")
            
            result = subprocess.run(["ip", "link", "show", interface], capture_output=True, text=True)
            if result.stdout:
                match = re.search(r'link/ether ([0-9a-fA-F:]{17})', result.stdout)
                if match:
                    final_mac = match.group(1).lower()
                    if final_mac == new_mac.lower():
                        logger.info(f"{GREEN}[✓] Двойная проверка пройдена: {final_mac}{RESET}")
                        return True
            
            return True
        else:
            logger.error(f"{RED}[!] MAC не изменился. Ожидалось: {new_mac}, получили: {verified_mac}{RESET}")
            return False
    else:
        logger.error(f"{RED}[!] Не удалось установить MAC{RESET}")
        return False

def scan_network(interface):
    try:
        logger.info(f"{BLUE}[*] Сканирование сети через {interface}...{RESET}")
        result = subprocess.run(
            ["nmap", "-sn", "192.168.1.0/24"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.stdout:
            logger.info(f"{GREEN}[*] Устройства в сети:{RESET}")
            for line in result.stdout.split('\n'):
                if "Nmap scan" in line or "MAC Address" in line:
                    logger.info(f"  {line}")
        else:
            logger.warning(f"{YELLOW}[!] nmap не установлен или не удалось просканировать{RESET}")
    except Exception as e:
        logger.error(f"Ошибка сканирования: {e}")

def save_config(interface, vendor):
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(f"INTERFACE={interface}\n")
            f.write(f"VENDOR={vendor if vendor else 'random'}\n")
            f.write(f"LAST_SPOOF={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        logger.info(f"{GREEN}[✓] Конфиг сохранён: {CONFIG_FILE}{RESET}")
    except Exception as e:
        logger.error(f"Ошибка сохранения конфига: {e}")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None, None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            lines = f.readlines()
            interface = None
            vendor = None
            for line in lines:
                if line.startswith("INTERFACE="):
                    interface = line.split("=")[1].strip()
                elif line.startswith("VENDOR="):
                    vendor = line.split("=")[1].strip()
            return interface, vendor
    except Exception as e:
        logger.error(f"Ошибка загрузки конфига: {e}")
        return None, None


def main():
    parser = argparse.ArgumentParser(
        description="MACspoof v2.1 - Professional MAC Address Spoofer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  sudo python MAC.py -i wlan0                # Случайный MAC
  sudo python MAC.py -i wlan0 -v intel       # MAC от Intel
  sudo python MAC.py -i wlan0 -m 00:11:22:33:44:55  # Конкретный MAC
  sudo python MAC.py -a                      # Все интерфейсы
  sudo python MAC.py -i wlan0 --reset        # Сброс до заводского
  python MAC.py --list                       # Список интерфейсов
        """
    )
    
    parser.add_argument("-i", "--interface", help="Интерфейс")
    parser.add_argument("-a", "--all", action="store_true", help="Все интерфейсы")
    parser.add_argument("-v", "--vendor", choices=['intel', 'realtek', 'broadcom', 'qualcomm', 'apple', 'cisco', 'dell', 'hp', 'asus', 'msi'], 
                       help="Вендор")
    parser.add_argument("-m", "--mac", help="Конкретный MAC (XX:XX:XX:XX:XX:XX)")
    parser.add_argument("--reset", action="store_true", help="Сбросить MAC")
    parser.add_argument("--scan", action="store_true", help="Сканировать сеть")
    parser.add_argument("--save", action="store_true", help="Сохранить конфиг")
    parser.add_argument("--load", action="store_true", help="Загрузить конфиг")
    parser.add_argument("--list", action="store_true", help="Список интерфейсов")
    
    args = parser.parse_args()
    
    if os.geteuid() != 0 and not args.list:
        print(f"{RED}[!] Запусти с sudo или от root{RESET}")
        print(f"{YELLOW}[*] Используй: sudo python {sys.argv[0]} ...{RESET}")
        sys.exit(1)
    
    if args.list:
        interfaces = get_interfaces()
        print(f"{BLUE}Доступные интерфейсы:{RESET}")
        for i in interfaces:
            mac = get_current_mac(i)
            print(f"  {i}: {mac if mac else 'N/A'}")
        sys.exit(0)
    
    if args.load:
        interface, vendor = load_config()
        if interface:
            print(f"{GREEN}[*] Загружен конфиг: интерфейс {interface}, вендор {vendor}{RESET}")
            args.interface = interface
            if vendor and vendor != 'random':
                args.vendor = vendor
        else:
            print(f"{YELLOW}[!] Конфиг не найден{RESET}")
            sys.exit(1)
    
    if args.all:
        interfaces = get_interfaces()
        if not interfaces:
            print(f"{RED}[!] Нет доступных интерфейсов{RESET}")
            sys.exit(1)
        
        success_count = 0
        for interface in interfaces:
            if spoof_interface(interface, args.vendor, args.mac):
                success_count += 1
            if args.scan:
                scan_network(interface)
        
        print(f"{GREEN}[✓] Спуфинг завершён. Успешно: {success_count}/{len(interfaces)}{RESET}")
        sys.exit(0)
    
    if args.interface:
        if args.reset:
            if reset_mac(args.interface):
                print(f"{GREEN}[✓] MAC сброшен для {args.interface}{RESET}")
            else:
                print(f"{RED}[!] Не удалось сбросить MAC{RESET}")
            sys.exit(0)
        
        if spoof_interface(args.interface, args.vendor, args.mac):
            if args.scan:
                scan_network(args.interface)
            if args.save:
                save_config(args.interface, args.vendor)
            print(f"{GREEN}[✓] Готово!{RESET}")
        else:
            print(f"{RED}[!] Ошибка!{RESET}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[!] Прервано пользователем{RESET}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"{RED}[!] Критическая ошибка: {e}{RESET}")
        sys.exit(1)