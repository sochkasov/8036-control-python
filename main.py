#!/usr/bin/python
# coding=utf-8

import sys
import serial
import time
import logging
import struct

sys.path.append('/root/8036/pycharm-debug.egg')
import pydevd
#pydevd.settrace('192.168.8.100', port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)
pydevd.settrace('192.168.7.8', port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)

logging.basicConfig(level=logging.DEBUG, filename="./log.log")
logging.debug('A debug message!')

ser = serial.Serial()
ser.port = "/dev/ttyS0"
ser.baudrate = 9600
ser.bytesize = 8  #number of bits per bytes
ser.stopbits = 2  #number of stop bits
ser.timeout = 1  #non-block read
ser.parity = serial.PARITY_NONE  #set parity check: no parity
ser.xonxoff = serial.XOFF  #disable software flow control
ser.rtscts = False  #disable hardware (RTS/CTS) flow control
ser.dsrdtr = False  #disable hardware (DSR/DTR) flow control
ser.writeTimeout = 0  #timeout for write

try:
    ser.open()

except Exception, e:
    print "error open serial port: " + str(e)
    exit()

if ser.isOpen():
    try:
        ser.flushInput() #flush input buffer, discarding all its contents
        ser.flushOutput() #flush output buffer, aborting current output.

        ########################################################################
        # 1. ‘t’ Чтение значений температуры
        # Команда: 1 байт – ASCII-символ ‘t’
        # Ответ: 1 байт количество температурных датчиков (32), далее передаются значения температуры всех 32 датчиков.
        # Формат числа int(16-битное знаковое целое число со значением температуры, умноженное на 100).
        ########################################################################
        #import struct
        print 'get temperature(sensors)'
        ser.write("t")
        result_raw = ser.read(1)
        result_raw = ser.read(64)
        for sensor_id in range(0,len(result_raw),2):
            temp = float(ord(result_raw[sensor_id]) | (ord(result_raw[sensor_id+1]) << 8))/100
            print('t(' + str(sensor_id/2) + ')=' + '{0:4.2f}'.format(temp) + ' ˚C')

        ########################################################################
        # 3. ‘l’ Чтение логического состояния выходов (не зависимо от импульсного режима)
        # Команда: 1 байт – ASCII-символ ‘l’
        # Ответ: 2 байтное число, каждый бит которого соответствует состоянию нагрузки.
        # 11 бит соответствует 1 выходу,
        # 10 бит – 2 выходу
        # и т.д. до 0 бита, который соответствует 12 выходу
        ########################################################################
        print 'Logical status of outputs'
        ser.flush()
        ser.write("l")
        result_raw = ser.read(2)
        print("outputs state (BIN) >> " + '{0:08b}'.format(ord(result_raw[0])) + '{0:08b}'.format(ord(result_raw[1])))
        print("outputs state (DEX) >> " + str(ord(result_raw[0])) + " " + str(ord(result_raw[1])))

        ########################################################################
        # 4. ‘z’ Чтение реального состояния выходов в данный конкретный момент
        # Команда: 1 байт – ASCII-символ ‘z’
        # Ответ: 2 байтное число, каждый бит которого соответствует состоянию выхода:
        # 11 бит сопоставлен 1 выходу,
        # 10 бит – 2 выходу
        # и т.д. до 0 бита, который соответствует 12 выходу
        ########################################################################
        print 'Real status on outputs'
        ser.flush()
        ser.write("z")
        result_raw = ser.read(2)
        print("outputs state (BIN) >> " + '{0:08b}'.format(ord(result_raw[0])) + '{0:08b}'.format(ord(result_raw[1])))
        print("outputs state (DEX) >> " + str(ord(result_raw[0])) + " " + str(ord(result_raw[1])))

        ########################################################################
        # 5. ‘b’ Чтение уровня заряда батареи часов реального времени
        # Команда: 1 байт – ASCII-символ ‘b’
        # Ответ: 2 байтное слово соответствующее представлению числа от 0 до 1024,
        # что соответствует напряжению соответственно от 0 до 5В
        ########################################################################
        print 'Battary voltage'
        ser.flush()
        ser.write("b")
        result_raw = ser.read(2)
        result_txt = str( '{0:4.2f}'.format(float((float(ord(result_raw[0])) + float(ord(result_raw[1]))*256)*5/1024)))
        print(result_txt + 'V')

        ########################################################################
        # 6. ‘V’ Чтение версии ПО микроконтроллера
        # Команда: 1 байт – ASCII-символ ‘V’
        # Ответ: символ ‘V’,далее 1 байт – число, представляющее длину строки текста,
        # который следует после (в конце строки нет флага окончания строки 00h)
        ########################################################################
        print 'Current version firmware'
        ser.flush()
        ser.write("V")
        while ser.read(1) != "V":
            time.sleep(0.05)
        ver_str_len = ser.read(1)
        ver_str = ser.read(ord(ver_str_len))
        print("Version: " + ver_str)

        ########################################################################
        # 8. ‘c’ Чтение времени
        # Команда: 1 байт – ASCII-символ ‘с’
        # Ответ: 1 байт ’эхо” символ ‘с’, следуют данные календаря по структуре описанной нижу. Суммарно 8 байт.
        # Описание структуры:
        # struct struct_clock{
        # // байт №1
        # unsigned char seconds:4; / /секунды (4 бита)
        # unsigned char ten_seconds:3; // десятки секунд (3 бита)
        # unsigned char ch:1; // всегда = 0 (1 бит)
        # // байт №2
        # unsigned char minutes:4; // минуты
        # unsigned char ten_minutes:3; // десятки минут
        # unsigned char reserved_0:1;
        # // байт №3
        # unsigned char hours:4; // часы
        # unsigned char ten_hours:2;// десятки часа
        # unsigned char AMPM_24_mode:1; // всегда =0
        # unsigned char reserved_1:1; // зарезервирован
        # // байт №4
        # unsigned char day:3; // День недели (1-7)
        # unsigned char reserved_2:5;
        # // байт №5
        # unsigned char date:4; // число (1-31)
        # unsigned char ten_date:2; // число (десятки)
        # unsigned char reserved_3:2;
        # // байт №6
        # unsigned char month:4; // месяц (1-12)
        # unsigned char ten_month:1; // месяц(десятки)
        # unsigned char reserved_4:3;
        # // байт №7
        # unsigned char year:4; // год от 0 до 99
        # unsigned char ten_year:4; // десятки года
        # // байт №8
        # unsigned char RS:2; // всегда =0
        # unsigned char reserved_5:2;
        # unsigned char SQWE:1; // всегда =1
        # unsigned char reserved_6:2;
        # unsigned char OUT:1; // всегда =1
        # };
        ########################################################################
        print 'Get time'
        ser.flush()
        ser.write("c")
        # "c"
        while ser.read(1) != "c":
            time.sleep(0.05)
        # # bin struct data
        result_raw = ser.read(8)

        seconds = ((ord(result_raw[0]) & 0b01110000) >> 4) * 10 + (ord(result_raw[0]) & 0b00001111)
        minutes = ((ord(result_raw[1]) & 0b01110000) >> 4) * 10 + (ord(result_raw[1]) & 0b00001111)
        hours = ((ord(result_raw[2]) & 0b00110000) >> 4) * 10 + (ord(result_raw[2]) & 0b00001111)
        day = ord(result_raw[3]) & 0b00000111
        date = ((ord(result_raw[4]) & 0b00110000) >> 4) * 10 + (ord(result_raw[4]) & 0b00001111)
        month = ((ord(result_raw[5]) & 0b00010000) >> 4) * 10 + (ord(result_raw[5]) & 0b00001111)
        year = 2000 + ((ord(result_raw[6]) & 0b11110000) >> 4) * 10 + (ord(result_raw[6]) & 0b00001111)

        print('date: '+str(year)+'-'+str(month)+'-'+str(date)+' day:'+str(day)+' '+str(hours)+":"+str(minutes)+":"+str(seconds))

        ########################################################################
        # 9. ‘L’ Считывание программы управления в компьютер
        # Команда: 1 байт – ASCII-символ ‘L’
        # Ответ: 1 байт “’эхо” символ ‘L’, далее 832 байта данных. Передаются 32 записи,
        # каждая из которых соответствует нижеописанной структуре.
        # Каждая структура занимает 27 байт, поэтому, суммарно 27 * 32 = 864 байта
        # Описание структуры:
        #   struct DataToORFromPC{
        #       unsigned char time_on_h; // время старта час 0-23
        #       unsigned char time_on_m; // время старта минута 0-59
        #       unsigned char time_on_s; // время старта секунда 0-59
        #       unsigned char time_off_h; // время остановки час 0-23
        #       unsigned char time_off_m; // время остановки минута 0-59
        #       unsigned char time_off_s; // время остановки секунда 0-59
        #       unsigned char time_on_day; // число старта 1-31
        #       unsigned char time_off_day; // число остановки 1-31
        #       unsigned char time_on_month; // месяц старта от 1 до 12
        #       unsigned char time_off_month; // месяц остановки от 1 до 12
        #       unsigned char time_on_year; // ГОД СТАРТА от 0 до 99 (соответствует от 2000 до 2099)
        #       unsigned char time_off_year; // ГОД ОСТАНОВКИ от 0 до 99 (соответствует от 2000 до 2099)
        #       unsigned char time_load; // номер нагрузки от 0 до 7
        #       unsigned char time_loadsensor; // логический номер датчика уменьшенный на 1 , с которым работает данная программа
        #       unsigned short time_min; // минимум, для датчиков температуры это от -5500 до +12500 (-55 до 125град),
        #                                   для АЦП это от 0 до 1023(цифровые показания АЦП);
        #                                   при сравнении двух датчиков - номер второго датчика от 0 до 31
        #       unsigned short time_max; // максимум, для датчиков температуры это от -5500 до +12500 (-55 до 125град),
        #                                   для АЦП это от 0 до 1023(цифровые показания АЦП)
        #       unsigned char time_mode ; // режим 0=нагрев, 1= охлаждение, 2= будильник, 3=по таймеру
        #       unsigned char time_eze; //отрабатывать по дням=1, по дням недели=2, по месяцам=3, без периода=0
        #       unsigned long time_ezedata; // 32 бита соответствующие выбранной периодичности
        #       unsigned char time_bud; // служебный (считать и записать в то же состояние)
        #       unsigned char enable; // разрешение работы данного канала
        #       unsigned char sensortype; // Бит 3: 1– сравнение двух датчиков, если 0, то проверить бит 0:
        #                                   0 – DS18B20, 1 – аналоговый вход;
        #                                   бит 1:– Закон ИЛИ/И.
        #   };
        ########################################################################
        print 'get programm'
        ser.flush()
        result_data = []
        ser.write("L")
        # "L"
        while ser.read(1) != "L":
            time.sleep(0.05)
        # Content in graphical format
        for sensor_id in range(0,32,1):
            result_raw = ser.read(26)
            result_data.append(result_raw)
            print(str(sensor_id) + ': ' + str(result_raw.encode("HEX")))

        time.sleep(1)
        ########################################################################
        # 11. ‘D’ Считывание серийных номеров зарегистрированных датчиков Dallas
        # Команда: 1 байт – ASCII-символ ‘D’
        # Ответ: 1 байт «эхо» - символ ‘D’,
        # после передается 32 поля серийных номеров DS18B20 по 8 байт (суммарно 256 байт),
        # если датчик не зарегистрирован на центральном блоке – то получить его серийный номер не получится
        ########################################################################
        print 'get sensor from line'
        ser.flush()
        time.sleep(1)
        ser.write("D")
        # "D"
        while ser.read(1) != "D":
            time.sleep(0.05)
        result_data = []
        # Content in graphical format
        for sensor_id in range(0,31,1):
            result_raw = ser.read(8)
            result_data.append(result_raw)
            print(str(result_raw.encode("HEX")))


        ########################################################################
        # 20. ‘S’ Считывание содержимого дисплея
        # Команда: 1 байт – ASCII-символ ‘S’
        # Ответ: 1 байт «эхо» - символ ‘S’
        # 64 байта – содержимое графической памяти
        # 16 байт – верхняя строка
        # 16 байт – нижняя строка
        # Итого 96 байт. Смотреть таблицу символов дисплея!
        ########################################################################
        print 'Display content'
        ser.flushOutput()
        ser.write("S")
        # "S"
        while ser.read(1) != "S":
            time.sleep(0.05)

        # Content in graphical format
        result_raw_content_graph64 = ser.read(55)
        # Content in text format (up string)
        result_raw_content_txt1 = ser.read(16)
        # Content in text format (down string)
        result_raw_content_txt2 = ser.read(16)
        print(str(result_raw_content_txt1))
        print(str(result_raw_content_txt2))



        ser.close()

        #time.sleep(0.5)
#        numOfLines = 0
#        while True:
            #response = ser.readline()
#            response = ser.read(1)
#            if len(response) > 0:
#                print(">> " + response.encode('hex'))
#                numOfLines = numOfLines + 1
#                if (numOfLines >= 10):
#                    ser.close()
#                    break

#            ser.close()
#            break

    except  Exception,  e1:
        print "error communicating...: " + str(e1)

#ser.close()
else:
    print "cannot open serial port "