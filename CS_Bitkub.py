import time
import requests 
import hmac
import json
import hashlib
import numpy as np
from datetime import datetime
from pymongo import MongoClient,results 

# API info
API_HOST = 'https://api.bitkub.com'
API_KEY = '343f340ba1aafd4a4d056801c791f14d'
API_SECRET = b'4fd33427a5d4dfddb93ce38251c4d8e5'


header = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-BTK-APIKEY': API_KEY,
}


#///////////////////////////////////////////////////////////////////

def initialization():  
    print("----------- initialize -----------")
    global market,acc,trade
    market = marketAPI()
    acc = accountManagement()
    trade = tradeAPI()
    #--------------------------variable-----------------------------
    #ProductSetting
    global symbol, symbolSplit
    symbol = 'THB_XRP'  # THB_XRP
    symbolSplit =  symbol.split("_")
    #Grid
    global transactionCost,maxPrice,minPrice,priceTick,delta
    transactionCost= 0.005#0.5%
    maxPrice = 0
    minPrice = 0
    priceTick = 0.1
    delta  = 0.1
    #SystemSetitng
    global system,realTrade
    system = True #While loop
    realTrade = False
    loadArray = False
    clearArray = True
    clearLog = True
    setPort = False
    
    #--------------------------SymbolsInfo-----------------------------
    SymbolsInfo = market.getSymbolsInfo()
    for x in range(len(SymbolsInfo)):
        if(SymbolsInfo[x]['symbol'] == symbol):
            print("Id : %s,  Symbol : %s [%s]" %(SymbolsInfo[x]['id'] ,SymbolsInfo[x]['symbol'] ,SymbolsInfo[x]['info'])) 
            break
    if(minPrice>maxPrice):print('minPrice must lest than maxPrice')
    if(minPrice>maxPrice):system = False       
 
    print("range [{:0.2f} - {:0.2f}]".format(minPrice,maxPrice))   
    print("priceTick {:0.2f}".format(priceTick))   
    print(f"RealTrade {realTrade}")
            
    #--------------------------Array  initialization-----------------------------  
    global posList
    posList=[]
    if(loadArray):
        posList = acc.load_order()

    #---------Clear-------
    if(clearArray):
        acc.clear_db('bitkub_trade')
        print("-clearOrder")
    if(clearLog):
        acc.clear_db('bitkub_history')
        print("-clearHistory")
    #---------Setport-------  
    port = { 'initialize': 0.0, 
                  'equity': 0.0, 
                  'in': 0.0, 
                  'out': 0.0, 
                  'p/l': 0.0
                  }
    if(setPort):
        acc.save_port(port)
        print("-setPort")
    print("----------- start -----------")
    
#----------------------------------------------------------------------------
#ปรับ vol. ในการส่งคำสั่ง
def lotSize():
    lot = 10
    return lot 

#กำหนดฟังก์ชั่นในการส่วคำสั่ง ถ้าไม่ใส่จะเป็น CS ธรรมดา
def tradeFunction():

    return True

#///////////////////////////////////////////////////////////////////
#Msg Line
def lineSendMas(msg_line):
    url_line = 'https://notify-api.line.me/api/notify'
    token_line = 'QHQPbxDrgD35meR5LDh0PniRVDGYUBNrH8ls42ThiKM'
    headers_line = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer '+token_line}
    requests.post(url_line, headers=headers_line , data = {'message':msg_line})

#///////////////////////////////////////////////////////////////////
#สร้าง class Account : class นี้จะจัดการงานเกี่ยวกับบัญชีเก็บ log จัดการงานทัวไป
class  accountManagement: 
   #สร้างตัวแปรที่จำเป็นต้องใช้
    def __init__(self):
        self._client=MongoClient("mongodb+srv://wasan:1234@cluster0.ujivx.gcp.mongodb.net/trading_db?retryWrites=true&w=majority")
        self._db=self._client.get_database('trading_db')   
        self.port = { 'initialize': 0.0, 
                  'equity': 0.0, 
                  'in': 0.0, 
                  'out': 0.0, 
                  'p/l': 0.0
                  }
  
    #------Real-----
    #ดึงข้อมูล สถานะ เงินทุน กำไร etc   
    def load_port(self,port):
        print("#") 

    #บันทึกข้อมูล สถานะ เงินทุน กำไร etc   
    def save_port(self,port):
        print("#") 

    #ส่วนการเทรด
    #โหลดข้อมูลส่วน array ซึ่งจะเก็บสถานะไม้ CS ที่เปิดค้างไว้อยู่
    def load_order(self):
        if (self._db.bitkub_trade.count_documents({}))==0:
            self.arr=[]
        else:
            self.arr=[]
            for data in self._db.bitkub_trade.find({}):
                self.arr.append(data)
        return self.arr

    #บันทึกข้อมูลส่วน array ซึ่งจะเก็บสถานะไม้ CS ที่เปิดค้างไว้อยู่
    def save_order(self,arr):
        self.clear_db('bitkub_trade')
        res = self._db.bitkub_trade.insert_many(arr)
        return res

    #บันทึกlog ในการยิงคำสั่งแต่ละครัง
    def save_log(self,arr):
        res = self._db.bitkub_history.insert_one(arr)
        return res

    #----clear worksheet
    def clear_db(self,collection):
        self._db[collection].delete_many({})

        
    def findID(self,collection,ID):
        return print(self._db[collection].find_one({"_id": ID}))

#///////////////////////////////////////////////////////////////////
class marketAPI:
    #API sub function
    def _json_encode(self,data):
        return json.dumps(data, separators=(',', ':'), sort_keys=True)

    def _sign(self,data):
            j = self._json_encode(data)
            h = hmac.new(API_SECRET, msg=j.encode(), digestmod=hashlib.sha256)
            return h.hexdigest()
    
    def _get(self,url): 
        try:
            res = requests.get(API_HOST + url)
            return json.loads(res.text)["result"]
        except:
            print(res)
            return json.loads(res.text)["error"]
    
    def _post(self,url,data): 
        try:
            signature = self._sign(data)
            data['sig'] = signature
            res = requests.post(API_HOST + url, headers=header, data=self._json_encode(data))
            return json.loads(res.text)["result"]
        except:
            print(res)
            return json.loads(res.text)["error"]
        
    #API function
    def getServerTime(self):
        try:
            res = requests.get(API_HOST + '/api/servertime')
            return int(res.text)
        except:
             return json.loads(res.text)['error']

    def getSymbolsInfo(self):
        return self._get('/api/market/symbols/')

    def getBids(self,Symbol):
        return self._get('/api/market/bids?sym='+Symbol+'&lmt=1')

    def getAsks(self,Symbol):
        return self._get('/api/market/asks?sym='+Symbol+'&lmt=1')

    def balance(self):
        data = {
            'ts': self.getServerTime(),
        }
        return self._post('/api/market/balances',data)
#///////////////////////////////////////////////////////////////////
#สร้าง class Trad : class นี้จะจัดการงานเกี่ยวกับการเทรดทั้งหมด
class  tradeAPI:
      #API sub function
    def _json_encode(self,data):
        return json.dumps(data, separators=(',', ':'), sort_keys=True)

    def _sign(self,data):
            j = self._json_encode(data)
            h = hmac.new(API_SECRET, msg=j.encode(), digestmod=hashlib.sha256)
            return h.hexdigest()
    
    def _get(self,url): 
        try:
            res = requests.get(API_HOST + url)
            return json.loads(res.text)["result"]
        except:
            print(res)
            return json.loads(res.text)["error"]
    
    def _post(self,url,data): 
        try:
            signature = self._sign(data)
            data['sig'] = signature
            res = requests.post(API_HOST + url, headers=header, data=self._json_encode(data))
            return json.loads(res.text)["result"]
        except:
            print(res)
            return json.loads(res.text)["error"]
     #-----------------
    def getServerTime(self):
        try:
            res = requests.get(API_HOST + '/api/servertime')
            return int(res.text)
        except:
             return json.loads(res.text)['error']
    
    def placeOrder(self, sym: str, orderType: str, lot: float, price: float, typ: str):
        data = {
            'sym': sym, #Symbol
            'amt': lot, # XRP amount you want to spend
            'rat': price, #Price
            'typ': typ,#Order type: limit or market
            'ts': self.getServerTime(),
                }
        if(orderType=='buy'):
            res = self._post('/api/market/place-ask',data)
        if(orderType=='sell'):
            res = self._post('/api/market/place-bid',data)
        return res
    
    def testPlaceOrder(self, sym: str, orderType: str, lot: float, price: float, typ: str):
        data = {
            'sym': sym, #Symbol
            'amt': lot, # XRP amount you want to spend
            'rat': price, #Price
            'typ': typ,#Order type: limit or market
            'ts': self.getServerTime(),
                }
        if(orderType=='buy'):
            res = self._post('/api/market/place-ask/test',data)
        if(orderType=='sell'):
            res = self._post('/api/market/place-bid/test',data)
        return res
#///////////////////////////////////////////////////////////////////
#---------------------------sent order FUNCTION ---------------------------
#function ยิง order 
def OrderSend(market,orderType,lot,price,mktType):
    if(realTrade == True):
        #ยิง order และรับค่าที่ return มา ถ้ายิงจริงจะมาปรับปรุงส่วนนี้เพิ่มเติม
        res = trade.placeOrder(market,orderType,lot,price,'market')

    else:
        res = trade.testPlaceOrder(market,orderType,lot,price,'market')
        #res = { 'hash':'Test', 'amt': lotSize(), 'rat':price, 'ts':date_time, 'rec':price*lot,}        
    return res

                            
def OrderClose(order):
    if(order['type']=='buy'):
        orderType = 'sell'
        lot = lotSize()
        price = bid
    else:
        orderType = 'buy'
        lot = lotSize()
        price = ask
        
    if(realTrade == True):
        res = trade.placeOrder(order['symbol'],orderType,lot,price,'market')
    else:
        res = trade.testPlaceOrder(order['symbol'],orderType,lot,price,'market')
        #res = {'hash':'Test', 'rat':price, 'ts':date_time, 'rec':price*lot,}        
    return res
#///////////////////////////////////////////////////////////////////
def main():
    zone=0 #set zone zero
    date_time = time.strftime('%Y-%m-%d %H:%M:%S')
    #[0]orderId [1]timestamp [2]volume [3]rate [4]amount
    global bid,ask
    bid = market.getBids(symbol)[0][3]
    ask = market.getAsks(symbol)[0][3]
    
    #----condition----
    #set ตัวแปรเริ่มต้น
    openOrder = True
    closeOrder = False
    
    if((ask//priceTick)%10 == 0
    and tradeFunction() == True):
        zone = (ask//priceTick)*priceTick
        for i in range(len(posList)):
            #เมื่อโซนปัจจุบันไม่มีบันทึกใน array จะยิง buy order
            if(zone == float(posList[i]['comment'])):
                openOrder = False
            #เมื่อโซนก่อนหน้านี้มีระยะ = delta ใน array จะยิง sell order
            if(zone < float(posList[i]['comment']) + delta):
                closeOrder = True
         
        #------ balance check ------
        if(market.balance()[symbolSplit[0]]['available'] < ((lotSize()*ask) or (lotSize()*ask))  ): openOrder == False
        #-----openOrder
        if(openOrder == True
          and ((ask<maxPrice and ask>minPrice) or  (minPrice and minPrice) ==0)
          ):
        #รับค่าที่ได้จาก condition ชุดคำสั่ง Buy 
            res = OrderSend(symbol,'buy',lotSize(),ask,'market')
            #ถ้าการยิง oreder สำเร็จ จากนั้นเตรียมข้อมูลเขียน log
            if(res != True):
                Order  = {
                        'symbol':symbol,
                        'type':'buy',
                        'size':res["amt"],
                        'openHash':res["hash"],
                        'openPrice':res["rat"],
                        'openTime':res["ts"],
                        'recive':res["rec"],
                        'closeHash':'',
                        'closePrice':0,
                        'closeTime':0,
                        'profit':0,
                        'comment':f'{zone}'
                    }
                p_comment=Order['comment']
                p_size=Order['size']
                p_openPrice=Order['openPrice']
                p_recive=Order["recive"]
                p_tm=Order["openTime"]
                #add createOrder ใน list 
                posList.append(Order)
                #save trade
                acc.save_order(posList)
                #sent log
                lineSendMas(f'open {symbol} {p_comment} \r\n{p_size} {bid}') 
                print(f'open {symbol} {p_comment} {p_openPrice} {p_size} {p_recive} {p_tm}',end="\r")
                print('')
            else:
                res       
                               
            #-----closeOrder
            if(closeOrder == True):
                #รับค่าที่ได้จาก fn
                res = OrderClose(posList[i])
                #ถ้าการยิง oreder สำเร็จ จากนั้นเตรียมข้อมูลเขียน log
                if(res != True):
                    #add createOrder ใน list 
                    posList[i]['closeHash'] = res["hash"]
                    posList[i]['closePrice'] = res["rat"]
                    posList[i]['closeTime'] = res["ts"]
                    posList[i]['profit'] = res["rec"] -  posList[i]['openPrice']
                    
                    p_comment=posList[i]['comment']
                    p_size=res['size']
                    p_closePrice=posList[i]['closePrice']
                    p_recive=posList[i]["profit"]
                    p_tm= posList[i]['closeTime']
                    
                    
                    #update history
                    acc.save_log(posList[i])
                    
                    #sent log
                    lineSendMas(f'open {symbol} {p_comment} {p_recive}\r\n{p_size} {bid}') 
                    print(f'open {symbol} {p_comment} {p_closePrice} {p_size} {p_recive} {p_tm}',end="\r")
                    print('')
                    
                    #update arr
                    del posList[i]
                    #save trade
                    acc.save_order(posList)
                else:
                    res

    #ใช้กับ google Code
    #print('\r BID:{:.2f} ASK:{:.2f} {}'.format(bid,ask,date_time),end="")
    
    #ใช้กับ CMD
    print('BID:{:.2f} ASK:{:.2f} {}'.format(bid,ask,date_time),end="\r")


#///////////////////////////////////////////////////////////////////

if __name__ == "__main__":
    initialization()
    while(system):
        main()
        time.sleep(1)  