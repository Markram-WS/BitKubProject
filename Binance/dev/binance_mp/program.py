import time
import numpy as np
from datetime import datetime
import pandas as pd
import json
import os
import threading
import csv
#----------
import configparser
#----------
from binance_f import RequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *
from binance_f.model.constant import *

###############################################################################################
#----------------------------------------Binance API------------------------------------------#
###############################################################################################
import requests 
import hmac
import hashlib

class binanceAPI():
    def __init__(self,host,key,secret):
        self._api_host = host
        self._api_key = key
        self._api_secret  = bytes(secret, 'utf-8')
        self._subaccount_name = ""
        self.header = {
        'Accept': 'application/json',
        'User-Agent': 'binance/python',
        'X-MBX-APIKEY': self._api_key,
        }
        self.client =  RequestClient(api_key=key, secret_key=secret)
          
    def _json_encode(self,data):
        return json.dumps(data, separators=(',', ':'), sort_keys=True)

    def _sign(self,data):
        j = self._json_encode(data)
        h = hmac.new(self._api_secret, msg=j.encode(), digestmod=hashlib.sha256)
        return h.hexdigest()
    
    def _get(self,url,**data):
        if len(data) != 0:
            signature = self._sign(data)
            data['signature'] = signature
            print(self._json_encode(data))
            res = requests.get(self._api_host + url, headers=self.header ,data=self._json_encode(data))
        else:   
            res = requests.get(self._api_host + url)
        try:
            return json.loads(res.text)
        except:
            print(res)
    
    def _post(self,url,data ):
        signature = self._sign(data)
        data['sig'] = signature
        res = requests.post(self._api_host + url, headers=self.header, data=self._json_encode(data))
        try:
            return json.loads(res.text)
        except:
            print(res)
    #signature  => uc(hmac_sha256_hex($data, $api_secret)),
    def server_time(self):
        res = self._get(f'/fapi/v1/time')
        return res['serverTime']
    
    def get_ticker(self,market_name):
        res = self._get(f'/fapi/v1/depth?symbol={market_name}&limit=5')
        return {'bids':res['bids'][0][0],
                'bidv':res['bids'][0][1],
                'asks':res['asks'][0][0],
                'askv':res['asks'][0][1]}

    def timeframe(self,tf):
        if(tf==60):
            return '1m'
        elif(tf==300):
            return '5m'
        elif(tf==900):
            return '15m'
        elif(tf==3600):
            return '1h'
        elif(tf==86400):
            return '1d'
        
    def timestampToDatetime(self,tm):
        time_tuple = time.gmtime(tm)
        return time.strftime("%Y-%m-%d %H:%M:%S", time_tuple)
    
    def datetimeToTimestamp(self,tm):
        time_tuple = time.strptime(tm, "%Y-%m-%d %H:%M:%S")
        return int(time.mktime(time_tuple))

    def exchangeInfo(self):
        return self._get(f'/fapi/v1/exchangeInfo')
    
    def _listToDict_HistoricalPriceFN(self,price_list):
        price_dict={'time':[],
                 'open':[],
                 'high':[],
                 'low':[],
                 'close':[],
                 'volume':[]
                }
        for i in price_list:
            price_dict["time"].append(self.timestampToDatetime(int(i[0])/1000))
            price_dict["open"].append(float(i[1]))
            price_dict["high"].append(float(i[2]))
            price_dict["low"].append(float(i[3]))
            price_dict["close"].append(float(i[4]))
            price_dict["volume"].append(float(i[5]))
        return price_dict
    
    def historicalPrice(self,market_name,resolution,limit,start_time,end_time):
        try:
            res = self._get(f'/fapi/v1/klines?symbol={market_name}&interval={self.timeframe(resolution)}&startTime={int(start_time*1000)}&endTime={int(end_time*1000)}&limit={limit}')
            return self._listToDict_HistoricalPriceFN(res)
        except:
            return res
            
    def historicalPriceCon(self,market_name,resolution,limit,start_time,end_time):
        try:
            res = self._get(f'/fapi/v1/continuousKlines?pair={market_name}&contractType=PERPETUAL&interval={self.timeframe(resolution)}&startTime={int(start_time*1000)}&endTime={int(end_time*1000)}&limit={limit}')
            return self._listToDict_HistoricalPriceFN(res)
        except:
            return res
    
    def place_orders(self,symbol,side,positionSide,quantity,price,type_ord):
        if type_ord == 'MARKET':
            order = self.client.post_order(
                    symbol=symbol, 
                    side=side, 
                    ordertype='MARKET', 
                    quantity=quantity,
                    positionSide=positionSide)
        
        if type_ord == 'LIMIT':
            order = self.client.post_order(
                    symbol=symbol, 
                    side=side, 
                    ordertype='LIMIT', 
                    quantity=quantity,
                    price=price,
                    positionSide=positionSide)
        return order
                  
    def query_all_open_orders(self,symbol):
        return self.client.get_all_orders(symbol=symbol)

    def query_open_order(self,symbol,orderId):
        return self.client.get_order(symbol=symbol,orderId=orderId)

    def query_order(self,symbol,orderId):
        return self.client.get_order(symbol=symbol,orderId=orderId)
        

############################################################################################
#------------------------------------  symbol class   -------------------------------------#
############################################################################################
class symbol():
    def __init__(self,sym,API):
        self.symbol = sym
        self.ticker = {'ask':'','bid':'','askv':'','bidv':''}
        self.his_price={}
        self.API = API
        
    def get_ticker(self):
        try:
            ticker = self.API.get_ticker(self.symbol)
            self.ticker['bid'] = float(ticker['bids'])
            self.ticker['bidv'] = float(ticker['bidv'])
            self.ticker['ask'] = float(ticker['asks'])
            self.ticker['askv'] = float(ticker['askv'])
            return True
        except:
            return False
        
        
    def getHisPrice(self,tf,nbar):
        price = self.API.historicalPrice(self.symbol,tf,nbar,time.time()-(tf*nbar),time.time())
        self.his_price = pd.DataFrame.from_dict(price)     
        
    def ma(self,type_bar):
        return self.his_price[type_bar].mean()

    def refBar(self,type_bar,bar):
        return self.his_price[type_bar][len(self.his_price)-bar]
    
    def atr(self):
        tr=[]
        for i in range(len(self.his_price)):
            tr.append(
                max(
                    (self.his_price['high'][i]-self.his_price['low'][i]),
                    abs(self.his_price['high'][i]-self.his_price['close'][i]),
                    (self.his_price['low'][i]-self.his_price['close'][i])
                )) 
        return np.mean(tr)

###################################################################################
#---------------------------------  main program  --------------------------------#
###################################################################################
class main():
    def __init__(self):
        #self.API = bitkubAPI(API_HOST,API_KEY,API_SECRET)
        config = configparser.ConfigParser()
        config.read('config.ini') 
        
        #API
        self.API = binanceAPI(
            config['API']['host'],
            config['API']['key'].encode(),
            config['API']['secret']
        )
        self.api_connect = True
        
        #system
        self.margin = float(config['SYSTEM']['margin'])
        self.size = float(config['SYSTEM']['size'])
        self.fee = float(config['SYSTEM']['fee'])
        self.side = config['SYSTEM']['side'].split(',')
        self.symbol = config['SYSTEM']['symbol'].split(',')
        self.sys_name   = config['SYSTEM']['name']
        self.slippage   = float(config['SYSTEM']['slippage'])
        self.order = {}
        self.ticker = {}
        self.zone = 0
        self.system = True
        
        #indecator 
        self.timeframe = int(config['SYSTEM']['timeframe']) #min #day:1440  #5m:5
        self.period = int(config['SYSTEM']['period']) #bar

        #time
        self.tm = time.localtime() # get struct_time
        self.time_string = time.strftime("%Y-%m-%d, %H:%M:%S", self.tm)
        self.refSec = 0
        self.timeout = 0
        
        #HisPrice init
        self.sys = list([])
        for i in range(len(self.symbol)):self.sys.append(i)
        for i in range(len(self.sys)): 
            self.sys[i] = symbol(self.symbol[i],self.API)
        self.hisPrice_init()
            
    ########################### write data ###########################          
    def write_log(self,dict_order): 
        csv_columns=[]
        for i in dict_order.keys():
            csv_columns.append(i)
        if(os.path.isfile('log.csv') == False):
            with open('log.csv', 'w', newline='') as csv_object: 
                writer = csv.DictWriter(csv_object, fieldnames=csv_columns)
                writer.writeheader()
                writer.writerow(dict_order) 
        else:
            with open('log.csv', 'a', newline='') as csv_object: 
                writer = csv.DictWriter(csv_object, fieldnames=csv_columns)
                writer.writerow(dict_order)   
            
    def load_order (self):
        if(os.path.isfile('data.json') == True):
            with open('data.json') as infile:
                self.order = json.load(infile)   
            
    def save_order(self): 
        with open('data.json', 'w') as outfile: 
            json.dump(self.order, outfile)

    ########################### order #############################
    def cal_size(self,price):
        return  f'{round(self.size/price,1)}'

    ########################### getdata ###########################   
    def time_check(self):
        #get_time
        self.tm = time.localtime() # get struct_time
        self.time_string = time.strftime("%Y-%m-%d, %H:%M:%S", self.tm)
        return True
    
    def hisPrice_init(self):
        for i in range(len(self.sys)):
            self.sys[i].getHisPrice(self.timeframe,100)
        for i in range(len(self.sys)):
            if i == 0: 
                self.ma = self.sys[i].ma('close')
                self.refBar = self.sys[i].refBar('high',1)
            elif i == 1: 
                self.ma = round(self.ma - self.sys[i].ma('close') , 5)
                self.refBar = round(self.refBar - self.sys[i].refBar('high',1) , 5)
            else:
                print('getHisPrice function error')
        
    def getHisPrice(self):
        if(self.refSec != self.tm and self.tm.tm_sec % self.timeframe  == 0):
            self.refSec = self.tm.tm_sec
            hisdatas = list()
            for i in range(len(self.sys)):
                get_hisdata = threading.Thread(target=self.sys[i].getHisPrice, args=[self.timeframe, self.period])
                get_hisdata.start()
                hisdatas.append(get_hisdata)
            for i in hisdatas:
                i.join()
                
            for i in range(len(self.sys)):
                if i == 0: 
                    self.ma = self.sys[i].ma('close')
                    self.refBar = self.sys[i].refBar('high',1)
                elif i == 1: 
                    self.ma = round(self.ma - self.sys[i].ma('close') , 5)
                    self.refBar = round(self.refBar - self.sys[i].refBar('high',1) , 5)
                else:
                    print('getHisPrice function error')
    
    
    ########################### open order ###########################         
    #-----place open orders fn------
    def place_orders_open(self,sym,positionSide,size,price,order_comment):
        side='BUY' if positionSide == 'LONG' else 'SELL'
        print('-------------Test 1-------------')
        print(f'sym:{sym} side:{side} positionSide:{positionSide} size:{size} price:{price}')
        res = self.API.place_orders(sym,side,positionSide,size,price,'MARKET')
        print('-------------Test 2-------------')
        print(res)
        print(f'sym {sym}, side {side}, price {price}')
        return{ 'status':'open',
                'orderId' : res['orderId'],
                'open_date': res['updateTime'],
                'open_price': float(res['price']),
                'side':positionSide,
                'size': float(res['origQty']),
                'sl': '',
                'tp': '',
                'fee':round( (float(res['origQty']) * float(res['price']) )*self.fee ,5),
                'order_comment':f'{order_comment}',
                }
                        
    #-----long order-----side[i]           
    def long_open_conditon(self):
        #------check short_conditon
        long_conditon = all([  self.ticker['ask'] < self.ma,
                               abs(self.ticker['ask'] - self.zone) < self.margin/80,
                               str(self.zone) not in self.order.keys()
                          ])

        if(self.time_check() and long_conditon):
            dict_order=list([])
            for i in range(len(self.sys)):
                price = self.sys[i].ticker['ask'] if self.side[i] == 'LONG' else self.sys[i].ticker['bid']
                zone = self.ticker['ask']
                #comment 
                comment =  f'open:{zone} sys{i}:[{price}]'
                #place_orders_open
                dict_order.append(self.place_orders_open(self.sys[i].symbol,self.side[i],self.cal_size(price),price,comment))
                
            print(f' --------------------------------------- open long {self.zone} ---------------------------------------')
            self.order[f'{self.zone}'] = {}
            for i in range(len(self.sys)):
                self.order[f'{self.zone}'][self.sys[i].symbol] = dict_order[i]
                print(dict_order[i])
            self.save_order()
            print('')
            
    #-----short order-----side[-i]            
    def short_open_conditon(self):
        #------check short_conditon
        short_conditon = all([ self.ticker['bid'] > self.ma,
                               abs(self.ticker['bid'] - self.zone) < self.margin/80,
                               str(self.zone) not in self.order.keys()
                          ])

        if(self.time_check() and short_conditon):
            dict_order=list([])
            for i in range(len(self.sys)):
                price = self.sys[i].ticker['ask'] if self.side[-i] == 'LONG' else self.sys[i].ticker['bid']
                zone = self.ticker['ask']
                #comment 
                comment =  f'open:{zone} sys{i}:[{price}]'
                #place_orders_open
                dict_order.append(self.place_orders_open(self.sys[i].symbol,self.side[-i],self.cal_size(price),price,comment))
                                  
            print(f' --------------------------------------- open short {self.zone} ---------------------------------------')
            self.order[f'{self.zone}'] = {}
            for i in range(len(self.sys)):
                self.order[f'{self.zone}'][self.sys[i].symbol] = dict_order[i]
                print(dict_order[i])
            self.save_order()
            print('')
        
    ########################### close_order ###########################       
    #-----place close orders fn------
    def place_orders_close(self,sym,positionSide,size,price,zone,order_comment):
        #place_orders('BTCUSDT','BUY','LONG',6,5000,'MARKET')
        side='SELL' if positionSide == 'LONG' else 'BUY'
        res = self.API.place_orders(sym,side,positionSide,size,price,'MARKET')
        self.order[f'{zone}'][sym]['status'] = 'close'
        self.order[f'{zone}'][sym]['close_id'] = res["orderId"]
        self.order[f'{zone}'][sym]['close_date'] = res["updateTime"]
        self.order[f'{zone}'][sym]['close_price'] = res["price"]
        close_val = float(res["price"])*float(self.order[f'{zone}'][sym]['size'])                   #USDT
        open_val = self.order[f'{zone}'][sym]['size'] * self.order[f'{zone}'][sym]['open_price']    #USDT
        self.order[f'{zone}'][sym]['fee'] = self.order[f'{zone}'][sym]['fee'] + (close_val * self.fee)
        
        #calculate order_profit
        if(self.order[f'{zone}'][sym]['side']=='LONG'):
            self.order[f'{zone}'][sym]['order_profit'] = close_val - open_val - self.order[f'{zone}'][sym]['fee'] 
        elif(self.order[f'{zone}'][sym]['side']=='SHORT'):
            self.order[f'{zone}'][sym]['order_profit'] = open_val - close_val - self.order[f'{zone}'][sym]['fee'] 
        else:
            print('error calculate order_profit')
            print('')
            self.system = False
            
     
        self.order[f'{zone}'][sym]['order_comment'] = f'{order_comment}'
        self.order[f'{zone}'][sym]['zone'] = zone
        return self.order[f'{zone}'][sym]
        
    #-----process close_order---------

    #-----CLOSE ORDER------
    def process_closeOrder(self,zone):
        zone = float(zone)
        fee=0
        open_order_sys1 = self.order[f'{zone}'][self.sys[0].symbol]['size'] * self.order[f'{zone}'][self.sys[0].symbol]['open_price']
        open_order_sys2 = self.order[f'{zone}'][self.sys[1].symbol]['size'] * self.order[f'{zone}'][self.sys[1].symbol]['open_price']
        fee = self.order[f'{zone}'][self.sys[0].symbol]['fee'] + self.order[f'{zone}'][self.sys[1].symbol]['fee']
        zProfit = 0  
        conditon_close=False
        #-----CLOSE LONG
        if(self.order[f'{zone}'][self.sys[0].symbol]['side'] == 'LONG'):      
            price = [self.sys[0].ticker['bid'],self.sys[1].ticker['ask']] 
            current_order_sys1 = ((self.order[f'{zone}'][self.sys[0].symbol]['size'] * price[0]) )
            current_order_sys2 = ((self.order[f'{zone}'][self.sys[1].symbol]['size'] * price[1]) )
            fee = (current_order_sys2 * self.fee) + (current_order_sys1 * self.fee)
            conditon_close = (current_order_sys1 - open_order_sys1) + (open_order_sys2-current_order_sys2) > self.margin + self.slippage + fee
            if(conditon_close): 

                dict_order=list([])            
                for i in range(len(self.sys)):
                    #comment
                    comment = self.order[f'{zone}'][self.sys[i].symbol]['order_comment'] + f'| close:{price[1]} sys{i}:[{price[0]},{price[1]}]'
                    #place_orders_close
                    dict_order.append(self.place_orders_close(self.sys[i].symbol,self.side[-i],self.order[f'{zone}'][self.sys[i].symbol]['size'],price[i],zone,comment))
                    #cal zProfit
                    zProfit = zProfit + dict_order[i]['order_profit']
                print(f' --------------------------------------- close long order ---------------------------------------')
                for i in range(len(self.sys)):
                    dict_order[i]['zone_profit']=zProfit
                    self.write_log(dict_order[i])
                    print(dict_order[i])
                print('')
                #SAVE LOG
                del self.order[f'{zone}']
                self.save_order()
            
        #---CLOSE SHORT
        elif(self.order[f'{zone}'][self.sys[0].symbol]['side'] == 'SHORT'):
            price = [self.sys[0].ticker['ask'],self.sys[1].ticker['bid']] 
            current_order_sys1 = ((self.order[f'{zone}'][self.sys[0].symbol]['size'] * price[0]) )
            current_order_sys2 = ((self.order[f'{zone}'][self.sys[1].symbol]['size'] * price[1]) )
            fee = (current_order_sys2 * self.fee) + (current_order_sys1 * self.fee)
            conditon_close = (open_order_sys1 - current_order_sys1) + (current_order_sys2-open_order_sys2) > self.margin + self.slippage + fee
            if(conditon_close): 
                for i in range(len(self.sys)):
                    #comment
                    comment = self.order[f'{zone}'][self.sys[i].symbol]['order_comment'] + f'| close:{price[1]} sys{i}:[{price[0]},{price[1]}]'
                    #place_orders_close
                    dict_order.append(self.place_orders_close(self.sys[i].symbol,self.side[i],self.order[f'{zone}'][self.sys[i].symbol]['size'],price[i],zone,comment))
                    #cal zProfit
                    zProfit = zProfit + dict_order[i]['order_profit'] 
                print(f' --------------------------------------- close short order ---------------------------------------')
                for i in range(len(self.sys)):
                    dict_order[i]['zone_profit']=zProfit
                    self.write_log(dict_order[i])
                    print(dict_order[i])
                print('')
                del self.order[f'{zone}']
                self.save_order()
                
    #-----operation------
    def close_order(self):
        processes = list()
        for zone in self.order.keys():
            process = threading.Thread(target=self.process_closeOrder, args=[zone])
            process.start()
            processes.append(process)
        for process in processes:
            process.join()
            
    ######################## program control ####################
    def controlPanel(self,timeout):
        self.timeout  = timeout*60 #min to sec
        lastsec=0
        while(self.system and (timeout != 0)):
            if(lastsec != self.tm.tm_sec):
                lastsec = self.tm.tm_sec
                self.timeout -= 1
            if(self.timeout<0):
                self.system = False
                
    ########################### start ###########################   
    def start(self):
        try:
            #get_ticker
            self.api_connect = all([self.sys[i].get_ticker() for i in range(len(self.sys))])

            #cal_ticker
            self.ticker['ask']  = round(self.sys[0].ticker['ask'] - self.sys[1].ticker['bid'], 5)
            self.ticker['bid']  = round(self.sys[0].ticker['bid'] - self.sys[1].ticker['ask'], 5)

            #----thread set 
            thr_getHisPrice = threading.Thread(target=self.getHisPrice)
            #----thread start 
            thr_getHisPrice.start()
        except:
            self.api_connect=False

        if(self.api_connect):
            #cal zone
            self.zone = round((self.ticker['ask'] // self.margin) * self.margin,5)
            
            #----thread set 
            #------open long condition ------
            thr_open_long = threading.Thread(target=self.long_open_conditon)
            #------check short_conditon
            thr_open_short = threading.Thread(target=self.short_open_conditon)
               
            #----thread start 
            thr_open_long.start()
            thr_open_short.start()
            #----thread join 
            thr_open_long.join()
            thr_open_short.join()
            
            #------check close_conditon
            self.close_order()
            
            ask  = self.ticker['ask']
            print(f'{self.sys[0].symbol}/{self.sys[1].symbol}:{self.sys_name} zone:{self.zone} ask:{ask} ma:{self.ma} {self.time_string}  timeout:{self.timeout}  ',end='\r')
        else:           
            print(f'{self.sys_name} connection failed {self.time_string}                                                                             ',end='\r')

program = main()
program.load_order()
while(program.system):
    program.start()
    time.sleep(0)