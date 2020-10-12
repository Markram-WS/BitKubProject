from datetime import datetime
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
    acc.account['account']='bitkub_xrp'
    acc._collection='bitkub_xrp'
    #ProductSetting
    global symbol, symbolSplit
    symbol = 'THB_XRP'  # THB_XRP
    symbolSplit =  symbol.split("_")

    #Grid
    global maxPrice,minPrice,priceTick,delta,printDecimal,makeFees,takeFees
    makeFees= 0.0025 #0.25%
    takeFees= 0.0025 #0.25%
    maxPrice = 0
    minPrice = 0
    priceTick = 0.01
    delta  = 0.05
    printDecimal = 3
    #SystemSetitng
    global sys_tradingsystem,sys_realTrade,sys_openOder
    sys_tradingsystem = True #While loop
    sys_realTrade = True
    sys_openOder = True
    clearOrder = False
    clearHistory = False
    setAccount = True
    
    #--------------------------SymbolsInfo-----------------------------
    SymbolsInfo = market.getSymbolsInfo()
    for x in range(len(SymbolsInfo)):
        if(SymbolsInfo[x]['symbol'] == symbol):
            print("Id : %s,  Symbol : %s [%s]" %(SymbolsInfo[x]['id'] ,SymbolsInfo[x]['symbol'] ,SymbolsInfo[x]['info'])) 
            break
    if(minPrice>maxPrice):print('minPrice must lest than maxPrice')
    if(minPrice>maxPrice):sys_tradingsystem = False       
    
    print(f"delta {delta}")   
    print(f"range [{minPrice} - {maxPrice}]")   
    print(f"priceTick {priceTick}")   
    print(f"RealTrade {sys_realTrade}")
            
    #--------------------------Array  initialization-----------------------------  
    global posList,priceList
    priceList=list(range(1,101))
    priceList=[round((i * 0.05)*4.6619, 2) for i in priceList]
    posList=[]
    #---------ClearOrder-------
    if(clearOrder):
        acc.clear_db({'position':'open'})
        print("-clearOrder")
    if(clearHistory):
        acc.clear_db({'position':'close'})
        print("-clearHistory")
    #---------loadOrder-------
    if(True):
        posList = acc.load_order()
        print("-loadOrder")
    #---------SetAccount-------  
    if(setAccount):
        print("-setPort")
        acc.account['initialize']=500
        acc.account['equity']=500
        acc.account['out']=0
        acc.account['p/l']=0
        acc.account['tmZone']=0
        acc.account['comment']=0
        acc.set_account()
    #---------loadAccount-------
    if(True):
        acc.load_account()
        
    print("----------- start -----------")

#///////////////////////////////////////////////////////////////////

#ปรับ vol. ในการส่งคำสั่ง
def amtSize(side,price):
    if side == "sell":#sell THB
        lot = 10
    elif side == "buy":#buy THB
        lot = round((10/price)+0.00001,5)
    return  lot

#กำหนดฟังก์ชั่นในการส่วคำสั่ง
def closeOrder(pos):
    # ask//priceTick ทำให้ทศนิยม priceTick ตำแหน่งกลายเป็นจำนวณเต็ม
    # %2 focus จำนวณที่ 2 หารลงตัว
    #-----initialize-----
    #condition_price     =   False
    condition1 = False
    condition2 = False
    totalCondition  =   False
    #-----condition-----
    #price check
    #if(((ask/priceTick)/1)%1.0 == 0.0):     condition_price = True
    

    #range
    if(priceZone > float(pos['comment']) + (0.05 * 4.6619)): condition1 = True
    

    #-----SumCondition-----
    if(condition1):totalCondition = True
    return totalCondition

def openOrder():
    # ask//priceTick ทำให้ทศนิยม priceTick ตำแหน่งกลายเป็นจำนวณเต็ม
    # %2 focus จำนวณที่ 2 หารลงตัว
    #-----initialize-----
    #condition_price     =   False
    condition_rang      =   False
    condition1 = False
    orderDuplicate = False
    totalCondition  =   False

    #-----condition-----
    #price check
    #if(((ask/priceTick)/1)%1.0 == 0.0): condition_price = True

    #rang check
    if( (ask <= maxPrice and ask >= minPrice ) or ( maxPrice == 0 and minPrice == 0 ) ): condition_rang = True

    #check price list
    if(ask in priceList): condition1 = True

    #check orde not Duplicate
    for i in range(len(posList)):  
        if( float(posList[i]['comment']) == priceZone): orderDuplicate = True

    #-----SumCondition-----
    if(sys_openOder == True
    and condition1 == True
    and orderDuplicate == False
    and condition_rang == True
    ):totalCondition = True
    return totalCondition

#///////////////////////////////////////////////////////////////////

#Msg Line
def lineSendMas(msg_line):
    url_line = 'https://notify-api.line.me/api/notify'
    token_line = 'QHQPbxDrgD35meR5LDh0PniRVDGYUBNrH8ls42ThiKM'
    headers_line = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer '+token_line}
    requests.post(url_line, headers=headers_line , data = {'message':msg_line})

#////////////////////////////////////////////////////////////////////

#สร้าง class Account : class นี้จะจัดการงานเกี่ยวกับบัญชีเก็บ log จัดการงานทัวไป
class  accountManagement: 
   #สร้างตัวแปรที่จำเป็นต้องใช้
    def __init__(self):
        self._client=MongoClient("mongodb+srv://wasan:1234@cluster0.ujivx.gcp.mongodb.net/trading_db?retryWrites=true&w=majority")
        self._db=self._client.get_database('trading_db')   
        self._collection = ''
        self.account = { 
                    'account':'',
                    'initialize':0.0, 
                    'equity': 0.0, 
                    'out': 0.0, 
                    'p/l': 0.0,
                    'tmZone':0,
                    'comment':0,
                  }
    ####################### ส่วนAccount #############################
    #updateข้อมูล สถานะ เงินทุน กำไร etc   
    def set_account(self):
        if (self._db.summary.count_documents({'account':self.account['account']})!= 0):
            self._db.summary.delete_many({'account':self.account['account']})
        res = self._db.summary.insert_one(self.account)
        if(res != False):
            print('set account success.')
        else:
            print('set account failure.')
  
            

    #ดึงข้อมูล สถานะ เงินทุน กำไร etc   
    def load_account(self):        
        if (self._db.summary.count_documents({'account':self.account['account']})==0):
            print('Empty account.')
            arr=[]
        else:
            arr = self._db.summary.find_one({'account':self.account['account']})
            if(arr != False):
                self.account = arr
                print('load account success.')
            else:
                print('load account failure.')

    #updateข้อมูล สถานะ เงินทุน กำไร etc   
    def _update_account(self):
        res = self._db.summary.update_one({'account':'bitkub-dataMinding'}, { "$set":  self.account  })
        if(res == True):
            print('Update account failure.')
    
    def order_in(self,value,profit):
        self.account['equity'] = self.account['equity'] + value + profit
        self.account['out'] = self.account['out'] -  value
        self.account['p/l'] = self.account['p/l'] +  profit
        self._update_account()
        
    def order_out(self,value):
        self.account['equity'] - value
        self.account['out'] + value
        self._update_account()
    
    ####################### ส่วนการเทรด #############################
    
    #โหลดข้อมูลส่วน array ซึ่งจะเก็บสถานะไม้ CS ที่เปิดค้างไว้อยู่
    def load_order(self):
        if (self._db[self._collection].count_documents({'position':'open'}))==0:
            arr=[]
        else:
            arr=[]
            for data in self._db[self._collection].find({'position':'open'}):
                arr.append(data)
        return arr

    #บันทึกlog ในการยิงคำสั่งแต่ละครัง
    def save_db(self,arr):
        res = self._db[self._collection].insert_one(arr)
        return res

    def update_db(self,query,values):
        res = self._db[self._collection].update_one(query, { "$set": values })
        return res


    #----clear worksheet
    def clear_db(self,target):
        self._db[self._collection].delete_many(target)

        
    def findID(self,ID):
        return print(self._db[self._collection].find_one({"_id": ID}))


#//////////////////////////////////////////////////////////////////////////
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
            res = json.loads(res.text)
            if('result' in res):
                return res['result']
            else: 
                print(f'Error:{res}',end="\r")
                return False
        except:
            print(f'Error:{res.text}',end="\r")
            return False
    
    def _post(self,url,data): 
        try:
            signature = self._sign(data)
            data['sig'] = signature
            res = requests.post(API_HOST + url, headers=header, data=self._json_encode(data))
            res = json.loads(res.text)
            if('result' in res):
                return res['result']
            else: 
                print(f'Error:{res}',end="\r")
                return False
        except:
            print(f'Error:{res.text}',end="\r")
            return False
        
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

#//////////////////////////////////////////////////////////////////////////

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
            res = json.loads(res.text)
            if('result' in res):
                return res['result']
            else: 
                print(f'Error:{res}',end="\r")
                return False
        except:
            print(f'Error:{res.text}',end="\r")
            return False
    
    def _post(self,url,data): 
        try:
            signature = self._sign(data)
            data['sig'] = signature
            res = requests.post(API_HOST + url, headers=header, data=self._json_encode(data))
            res = json.loads(res.text)
            if('result' in res):
                return res['result']
            else: 
                print(f'Error:{res}',end="\r")
                return False
        except:
            print(f'Error:{res.text}',end="\r")
            return False
     #-----------------
    def getServerTime(self):
        try:
            res = requests.get(API_HOST + '/api/servertime')
            return int(res.text)
        except:
            print(f'Error:{res}',end="\r")
            return False
    
    def placeOrder(self, sym: str, orderType: str, amt: float, price: float, typ: str):
        tm=self.getServerTime()
        if(tm != False):
            data = {
            'sym': sym, #Symbol
            'amt': amt, # XRP amount you want to spend
            'rat': price, #Price
            'typ': typ,#Order type: limit or market
            'ts': tm,
                }
            if(orderType=='buy'):
                res = self._post('/api/market/place-ask',data)
            if(orderType=='sell'):
                res = self._post('/api/market/place-bid',data)
            return res
        else:
            print('cannot place orders                          ')
            return False
    
    def testPlaceOrder(self, sym: str, orderType: str, amt: float, price: float, typ: str):
        tm=self.getServerTime()    
        if(tm != False):
            data = {
            'sym': sym, #Symbol
            'amt': amt, # amount you want to spend
            'rat': price, #Price
            'typ': typ,#Order type: limit or market
            'ts': self.getServerTime(),
                }
            if(orderType=='buy'):
                res = self._post('/api/market/place-ask/test',data)
            if(orderType=='sell'):
                res = self._post('/api/market/place-bid/test',data)
            return res
        else:
            print('cannot place orders                          ')
            return False


#/////////////////////////////////////////////////////////////////////////

#---------------------------sent order FUNCTION ---------------------------
#function ยิง order 
def OrderOpen(market,orderType,mktType):
    if(orderType=='buy'):
        price = ask
        fee = takeFees
    else:
        price = bid
        fee = makeFees

    amt = amtSize(orderType,price)

    if(sys_realTrade == True):
        #ยิง order และรับค่าที่ return มา ถ้ายิงจริงจะมาปรับปรุงส่วนนี้เพิ่มเติม
        res = trade.placeOrder(market,orderType,amt,price,mktType)

    else:
        #res = trade.testPlaceOrder(market,orderType,lot,price,'market')
        res = { "id":"Test", 
                'hash':'Test', 
                'amt': amt, 
                'rat':price, 
                "fee": makeFees, 
                "cre": 0,
                'rec':(amt/price)*(1-makeFees),
                "ts": date_time }        
    return res

                            
def OrderClose(order):
    if(order['type']=='buy'):
        orderType = 'sell'
        price = bid
        fee = takeFees
    else:
        orderType = 'buy'
        price = ask
        fee = makeFees

    amt = amtSize(orderType,price)

    if(sys_realTrade == True):
        res = trade.placeOrder(order['symbol'],orderType,amt,price,'market')
    else:
        #res = trade.testPlaceOrder(order['symbol'],orderType,lot,price,'market')
        res = { "id":"Test", 
                'hash':'Test', 
                'amt': order['recive'], 
                'rat':price, 
                "fee": makeFees, 
                "cre": 0,
                'rec':(order['recive']*price)*(1-fee),
                "ts": date_time }           
    return res

#//////////////////////////////////////////////////////////////////////////////////////

def main():
    global bid,ask,date_time,priceZone
    priceZone=0 #set zone zero
    tm = datetime.now()
    date_time = tm.strftime('%Y-%m-%d %H:%M:%S')
    #[0]orderId [1]timestamp [2]volume [3]rate [4]amount
    
    bid = market.getBids(symbol)[0][3]
    ask = market.getAsks(symbol)[0][3]
    priceZone =  round(((ask/priceTick)//1)*priceTick ,printDecimal)

    
    #Time action
    if(ask != False):
        
        for i in range(len(posList)):
            if(closeOrder(posList[i]) == True):
                res = OrderClose(posList[i])
                print(res)
                if(res != False):
                    #add Close Order ใน list 
                    posList[i]['position'] = 'close'
                    posList[i]['closeHash'] = res["hash"]
                    posList[i]['closePrice'] = res["rat"]
                    posList[i]['closeTime'] = res["ts"]
                    posList[i]['profit'] =  res["rec"] - posList[i]['size']

                    msgComment    =   posList[i]['comment']
                    msgSize       =   round(posList[i]["recive"],printDecimal)
                    msgPrice      =   round(posList[i]['closePrice'],printDecimal)
                    msgRecive     =   round(posList[i]["profit"],printDecimal)
                    msgTm         =   posList[i]['closeTime']
                    msgType       =   posList[i]['type']
                    msgComment    =   posList[i]['comment']
                    
                    if(msgType == 'buy'):
                        msgType = 'sell'
                    else:
                        msgType = 'buy'

                    #update history
                    acc.update_db({ "comment": msgComment,"position":'open' },posList[i])
                    acc.order_in(msgSize,msgRecive)
                    #sent log
                    lineSendMas(f'{msgType} {symbol} {msgComment} \r\n{msgSize} {symbolSplit[1]} @ {msgPrice} \r\nprofit {msgRecive} {symbolSplit[0]} ') 
                    print(f'{msgType}:{symbol} zone:{msgComment} {msgSize} {symbolSplit[1]} @ {msgPrice} profit {msgRecive} {symbolSplit[0]} {msgTm}',end="\r")
                    print('')
                
                    #update arr
                    del posList[i]
                    break# end loop
                else:
                    print('error: close order')
        #-----openOrder
        if(openOrder() == True):
            #------ balance check ------
             #balance check

            condition_balance = False 
            if(sys_realTrade == True):
                if( ( market.balance()[symbolSplit[0]]['available'] > (amtSize('sell',ask)*ask) ) ):
                    condition_balance = True
                else:
                    print('Not enough money.')
                    sys_tradingsystem == False
            
       
            if(condition_balance == True or sys_realTrade == False):
        
                orderType = 'sell'
                res = OrderOpen(symbol,orderType,'market')# sell THB buy XRP
                #ถ้าการยิง oreder สำเร็จ จากนั้นเตรียมข้อมูลเขียน log
                if(res != False):
                    Order  = {
                        'position':'open',
                        'symbol':symbol,
                        'type':orderType,
                        'size':res["amt"],
                        'openHash':res["hash"],
                        'openPrice':res["rat"],
                        'openTime':res["ts"],
                        'recive':res["rec"],
                        'closeHash':'',
                        'closePrice':0,
                        'closeTime':'',
                        'profit':0,
                        'comment':f'{priceZone}'
                    }
                    msgType = Order['type']
                    msgComment = Order['comment']
                    msgSize    = round(Order['size'],printDecimal)
                    msgPrice  = round(Order['openPrice'],printDecimal)
                    msgRecive  = round(Order["recive"],printDecimal)
                    msgTm      = Order["openTime"]
                    #add createOrder ใน list 
                    posList.append(Order)
                    #save trade
                    acc.save_db(posList[-1])
                    acc.order_out(msgSize)
                    #sent log
                    lineSendMas(f'{msgType} {symbol} {msgComment} \r\n{msgSize} {symbolSplit[0]} @ {msgPrice} \r\nrecive {msgRecive} {symbolSplit[1]} ') 
                    print(f'{msgType}:{symbol} zone:{msgComment} {msgSize} {symbolSplit[0]} @ {msgPrice} recive {msgRecive} {symbolSplit[1]} {msgTm}',end="\r")
                    print('')

                else:
                    print('error: openOrder order')        

        #ใช้กับ google Code
        #print('\r BID:{:.2f} ASK:{:.2f} {}'.format(bid,ask,date_time),end="")
        #ใช้กับ CMD
    if(ask != False):   
        print(f'Zone:{priceZone} BID:{round(bid,printDecimal)} ASK:{round(ask,printDecimal)} {date_time}     ',end="\r")
    else:
        print(f'Error,plese check connection.                                               ',end="\r")

#//////////////////////////////////////////////////////////////////////

initialization()
while(sys_tradingsystem):
    main()
    time.sleep(1)