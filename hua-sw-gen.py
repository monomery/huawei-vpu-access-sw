# -*- coding: utf-8 -*-
"""
Скрипт генерации конфигурации для vlan per user. 
Первый vlan первого порта первого свитча - 101.
Поддерживает несколько режимом конфигурирования:
Первый режим - выводит полный конфиг.
Второй режим - базовый конфиг, с временным IP (10.90.90.90/24) и без вланов.
Данный режим подходит для предварительной настройки коммутатора и последующей его
донастройке через телнет/ssh удаленно с помощью третьего режима.
Третий режим - режим, когда генерируются только конфиги портов, а также конфиг 
IP-адреса и шлюза. 

"""

import ipaddress

#объявляем списки
trunk_ports = []
ports = []
final_config = []
#vlansdict = {} # не используется, для будущих проектов

#переменные, необходимо внести свои параметры.
username = 'admin'
password = 'password'
snmp_community = 'public'
ntp_server = '172.254.254.254'

trunk_port_input = str(input('Введите магистральные порты через запятую, например 25,26,28: '))
template_input_models = ['Введите цифру модели коммутатора, где:']
template_input_mode = ['Введите режим подготовки конфигурации:']

def configip(ipaddr_input, gw, modenumber): #обрабаываем ip-адрес и генерируем часть конфига с IP и GW

    ipaddr = ipaddress.ip_interface(ipaddr_input)
    netmask = ipaddr.netmask
    ip = ipaddr.ip
    config_ip = ['interface Vlanif1',
                 ' ip address {ip} {netmask}',
                 '#']
             
    if modenumber in [0, 2]:
        config_ip.append('ip route-static 0.0.0.0 0.0.0.0 {gw}')
        config_ip.append('#')
        final_config.append('\n'.join(config_ip).format(ip = ip, netmask = netmask, gw = gw))
    elif modenumber == 1:
        final_config.append('\n'.join(config_ip).format(ip = ip, netmask = netmask, gw = gw))
        

def interfacelist(): #генерируем общий списко интерфейсов на основании модели коммутатора
    
    models = ['S2320-28TP-EI-AC', 'S2350-28TP-EI-AC']
    
    for model in models:
        model_index = models.index(model)
        template_input_models.append(f'{model_index} - {model}  ')
    modelnumber = int(input('\n'.join(template_input_models)))
    
    
    #проходим по списку моделей коммутаторов и генерируем список портов
    
    if modelnumber == 0:
        for interface in range(1, 21):
            ports.append(f'Ethernet 0/0/{interface}')
        for interface in range(1, 7):
            ports.append(f'GigabitEthernet 0/0/{interface}')
    elif modelnumber == 1:
        for interface in range(1, 25):
            ports.append(f'Ethernet 0/0/{interface}')
        for interface in range(1, 5):
            ports.append(f'GigabitEthernet 0/0/{interface}')
    else:
        print('error')
    
def trunkports(): #получаем список транковых портов (trunk_ports)
    trunks = trunk_port_input.split(',')
    access_ports = ports.copy()
    for trunk in trunks:
        trunk = int(trunk) - 1
        trunk_ports.append(ports[trunk])        
        access_ports.remove(ports[trunk])


def trunkports_config(port, vlans): #шаблон для транковых портов
    trunk_template = [' port link-type trunk',
                      ' port trunk allow-pass vlan {vlans}',
                      '#']
    final_config.append(f'interface {port}')
    final_config.append('\n'.join(trunk_template).format(vlans=vlans))

def userports_config(port, vlan): #шаблон для аксесс портов
    access_template = [' port link-type access',
                       ' port default vlan {vlan}',
                       ' port-isolate enable group 1',
                       ' loopback-detect enable',
                       ' multicast-suppression packets 64',
                       ' broadcast-suppression packets 64',
                       ' storm-control action block',
                       ' storm-control enable log',
                       '#']
    final_config.append(f'interface {port}')
    final_config.append('\n'.join(access_template).format(vlan=vlan))
    
def mainconfig(): #шаблон базового конфига
    main_template = ['telnet server enable',
                     '#',
                     'clock timezone Moscow,St.Petersburg,Volgograd add 03:00:00',
                     '#',
                     'aaa',
                     ' undo user-password complexity-check',
                     ' undo local-user admin',
                     ' local-user {username} password irreversible-cipher {password}',
                     ' local-user {username} privilege level 15',
                     ' local-user {username} service-type telnet terminal ssh ftp x25-pad http',
                     '#',
                     'ntp-service server disable',
                     'ntp-service ipv6 server disable',
                     'ntp-service unicast-server {ntp_server}',
                     '#',
                     'snmp-agent',
                     'snmp-agent community complexity-check disable',
                     'snmp-agent community read cipher {snmp_community}',
                     'snmp-agent sys-info version v2c',
                     'undo snmp-agent sys-info version v3',
                     '#',
                     'user-interface con 0',
                     ' authentication-mode none',
                     'user-interface vty 0 4',
                     ' authentication-mode aaa',
                     ' user privilege level 15',
                     ' protocol inbound all',
                     'user-interface vty 16 20',
                     '#']
    final_config.append('\n'.join(main_template).format(username = username, 
                        password = password, ntp_server = ntp_server,
                        snmp_community = snmp_community))

def vlanconfiguration(): #генератор конифгурации вланов
    sw_number_input = int(input('Введите номер коммутатора в биллинге: '))
    vlans_input = str(input('Введите вланы коммутатора: '))
    first_access_vlan = (sw_number_input*30)+71
    trunkvlans = vlans_input.replace('-', ' to ')
    final_config.append(f'vlan batch {trunkvlans}\n#')
    trunkports()
#    trunkdict = {} 
#    accessdict = {}
    for port in ports:
        if port in trunk_ports:
#            trunkdict[port] = vlans_input
#            vlansdict.update(trunkdict)
            trunkports_config(port, trunkvlans)
        else:
            access_vlans = ports.index(port) + first_access_vlan
#            accessdict[port] = access_vlans
#            vlansdict.update(accessdict)
            userports_config(port, access_vlans)
           

def modelist(): #главная функция, вызывает остальные функции
    
    config_mode = ['Полный конфиг',
                   'Базовый конфиг конфиг с временным IP и без вланов',
                   'Только вланы и постоянный IP']
    for mode in config_mode:
        mode_index = config_mode.index(mode)
        template_input_mode.append(f'{mode_index} - {mode}  ')
    modenumber = int(input('\n'.join(template_input_mode)))
    
    #проходим по списку моделей коммутаторов и генерируем список портов
    
    if modenumber == 0:
        interfacelist()
        mainconfig()
        vlanconfiguration()
        ipaddr_input = str(input('Введите ip-адрес: '))
        gw = str(input('Введите gateway: '))
        configip(ipaddr_input, gw, modenumber)
    elif modenumber == 1:
        mainconfig()
        configip('10.90.90.90/24', '10.90.90.92', modenumber) #передаем временный IP и GW
    else:
        interfacelist()
        vlanconfiguration()        
        ipaddr_input = str(input('Введите ip-адрес: '))
        gw = str(input('Введите gateway:'))
        configip(ipaddr_input, gw, modenumber)


modelist()
#Выводим финальную версию конфигурации:
print('Готовый конфиг для коммутатора: \n#')
print('\n'.join(final_config))

