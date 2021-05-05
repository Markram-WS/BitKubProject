import requests 
import hmac
import json
import hashlib

class Bitkub:
    def __init__(self,API_HOST,API_KEY,API_SECRET):
        ## instantiating the 'Inner' class
        self.API_HOST = API_HOST
        self.API_KEY = API_KEY
        self.API_SECRET = API_SECRET
        self.HEADER = {  'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'X-BTK-APIKEY': self.API_KEY,}

    #////////////////////////////////---API function---///////////////////////////////////
    def _json_encode(self,data):
        return json.dumps(data, separators=(',', ':'), sort_keys=True)

    def _sign(self,data):
            j = self._json_encode(data)
            h = hmac.new(self.API_SECRET, msg=j.encode(), digestmod=hashlib.sha256)
            return h.hexdigest()
    
    def _get(self,url): 
        try:
            res = requests.get(self.API_HOST + url)
            res = json.loads(res.text)
            if(res['error'] == 0 ):
                return res['result']
            else:
                err = res['error'] 
                return f'error:{err}'
        except:
            return f'error:404, Connection Lost'


    def _post(self,url,data): 
        try:
            data['sig'] = self._sign(data)
            res = requests.post(self.API_HOST + url, headers=self.HEADER, data=self._json_encode(data))
            res = json.loads(res.text)
            if(res['error']  == 0 ):
                return res['result']
            else:
                err = res['error'] 
                return f'error:{err}'
        except:
            return f'error:404, Connection Lost'
    
    
    #////////////////////////////////---getServerTime---///////////////////////////////////
    def _getServerTime(self):
        try:
            res = requests.get(self.API_HOST + '/api/servertime')
            return int(res.text)
        except:
            return json.loads(res.text)['error']

    #////////////////////////////////---ACC---///////////////////////////////////
    def getSymbolsInfo(self):
        return self._get('/api/market/symbols/')

    def bids(self,Symbol):
        return self._get('/api/market/bids?sym='+Symbol+'&lmt=1')

    def asks(self,Symbol):
        return self._get('/api/market/asks?sym='+Symbol+'&lmt=1')

    def balance(self):
        data = {
            'ts': self._getServerTime(),
        }
        return self._post('/api/market/balances',data)

    def wallet(self):
        data = {
            'ts': self._getServerTime(),
        }
        return self._post('/api/market/wallet',data)

    #////////////////////////////////---placeOrder---///////////////////////////////////
    def placeOrder(self, sym: str, orderType: str, amt: float, price: float, typ: str):
        tm=self._getServerTime()
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
            #*-----------Test-------------
            return res
        else:
            print(f"error:cannot place orders  {res['error']}                        ")

    
    def testPlaceOrder(self, sym: str, orderType: str, amt: float, price: float, typ: str):
        tm=self._getServerTime()    
        if(tm != False):
            data = {
            'sym': sym, #Symbol
            'amt': amt, # amount you want to spend
            'rat': price, #Price
            'typ': typ,#Order type: limit or market
            'ts': tm,
                }
            if(orderType=='buy'):
                res = self._post('/api/market/place-ask/test',data)
            if(orderType=='sell'):
                res = self._post('/api/market/place-bid/test',data)
            return res
        else:
            print(f"error:cannot place orders  {res['error']}                        ")